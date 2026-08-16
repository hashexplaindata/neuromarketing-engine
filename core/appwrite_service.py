"""Appwrite storage/database adapter with an explicit local fallback.

The remote Appwrite path is used when credentials are configured. The in-memory
path is intentionally limited to local development and tests; it is not a
production persistence substitute. Both paths expose the same tenant-aware job,
asset, result, and authentication contract.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import threading
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from dotenv import load_dotenv

from core.config import settings

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

logger = logging.getLogger("core.appwrite")


class AppwriteService:
    def __init__(self) -> None:
        self.endpoint = os.getenv("APPWRITE_ENDPOINT", os.getenv("VITE_APPWRITE_ENDPOINT", "https://cloud.appwrite.io/v1"))
        self.project_id = os.getenv("APPWRITE_PROJECT_ID", os.getenv("VITE_APPWRITE_PROJECT_ID", "neuromarketing-engine"))
        self.api_key = os.getenv("APPWRITE_API_KEY", "")
        self.database_id = os.getenv("APPWRITE_DATABASE_ID", "neuromarketing_db")
        self.jobs_collection_id = os.getenv("APPWRITE_JOBS_COLLECTION_ID", "jobs")
        self.results_collection_id = os.getenv("APPWRITE_RESULTS_COLLECTION_ID", "analysis_results")
        self.experiments_collection_id = os.getenv("APPWRITE_EXPERIMENTS_COLLECTION_ID", "experiments")
        self.bucket_id = os.getenv("APPWRITE_STORAGE_BUCKET_ID", "neuromarketing-assets")

        self.client = None
        self.storage = None
        self.databases = None
        self._lock = threading.RLock()
        self._memory_assets: Dict[str, Dict[str, Any]] = {}
        self._memory_jobs: Dict[str, Dict[str, Any]] = {}
        self._memory_results: Dict[str, Dict[str, Any]] = {}

        if self.api_key and self.project_id:
            try:
                from appwrite.client import Client
                from appwrite.services.databases import Databases
                from appwrite.services.storage import Storage

                self.client = Client()
                self.client.set_endpoint(self.endpoint)
                self.client.set_project(self.project_id)
                self.client.set_key(self.api_key)
                self.storage = Storage(self.client)
                self.databases = Databases(self.client)
                logger.info("AppwriteService initialized with remote storage/database.")
            except Exception as exc:  # pragma: no cover - depends on remote SDK/runtime
                logger.warning("Appwrite initialization failed; local fallback active: %s", exc)
                self.client = self.storage = self.databases = None
        else:
            logger.info("Appwrite credentials not configured; local fallback active for development/tests.")

    @property
    def remote_enabled(self) -> bool:
        return bool(self.storage and self.databases)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _stringify(value: Any) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, str):
            return value
        return json.dumps(value, default=str, separators=(",", ":"))

    @staticmethod
    def _as_dict(value: Any) -> Optional[Dict[str, Any]]:
        if value is None:
            return None
        if isinstance(value, dict):
            return deepcopy(value)
        if hasattr(value, "model_dump"):
            raw = value.model_dump()
        elif hasattr(value, "dict"):
            raw = value.dict()
        else:
            raw = getattr(value, "__dict__", None)
        if not isinstance(raw, dict):
            return None
        # Appwrite SDK document models expose user fields under `data`.
        # Flatten them while retaining system identifiers for diagnostics.
        data = raw.get("data")
        if isinstance(data, dict):
            flattened = {key: val for key, val in raw.items() if key != "data"}
            flattened.update(data)
            return deepcopy(flattened)
        return deepcopy(raw)

    @classmethod
    def _assert_tenant(cls, doc: Optional[Any], tenant_id: Optional[str]) -> Optional[Dict[str, Any]]:
        normalized = cls._as_dict(doc)
        if normalized is None:
            return None
        if tenant_id is not None and normalized.get("tenant_id") != tenant_id:
            return None
        return normalized

    def verify_appwrite_jwt(self, token: str) -> Dict[str, str]:
        """Resolve a user identity for tests or a future Appwrite JWT verifier.

        Appwrite JWT verification is intentionally not guessed from a service key.
        The deterministic test token remains available for local tests. A live
        verifier will be added once the chosen Appwrite authentication flow is
        configured and tested with real credentials.
        """
        if token.startswith("Bearer ") or token.startswith("bearer "):
            token = token[7:].strip()
        if token.startswith("test_tenant_"):
            tenant_id = token.removeprefix("test_tenant_").strip()
            if not tenant_id:
                raise ValueError("Invalid or expired Appwrite JWT")
            return {
                "tenant_id": tenant_id,
                "user_id": "usr_appwrite_dev",
                "email": f"dev@{tenant_id}.com",
                "name": "Local Test User",
            }
        raise ValueError("Invalid or expired Appwrite JWT")

    def upload_asset_file(self, file_id: str, content: bytes, filename: str, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """Persist an asset remotely when configured, otherwise in local fallback."""
        if self.storage:
            try:
                from appwrite.input_file import InputFile

                self.storage.create_file(
                    bucket_id=self.bucket_id,
                    file_id=file_id,
                    file=InputFile.from_bytes(content, filename),
                )
                return {"file_id": file_id, "filename": filename, "storage": "appwrite"}
            except Exception as exc:  # pragma: no cover - remote SDK/API dependent
                logger.error("Appwrite asset upload failed: %s", exc)
                raise

        with self._lock:
            self._memory_assets[file_id] = {
                "file_id": file_id,
                "filename": filename,
                "tenant_id": tenant_id,
                "content_b64": base64.b64encode(content).decode("ascii"),
                "created_at": self._now(),
            }
        return {"file_id": file_id, "filename": filename, "storage": "memory"}

    def download_file_to_path(self, file_id: str, target_path: str, tenant_id: Optional[str] = None) -> bool:
        """Download an asset to a worker-local path with optional tenant check."""
        if self.storage:
            try:
                result = self.storage.get_file_download(bucket_id=self.bucket_id, file_id=file_id)
                with open(target_path, "wb") as handle:
                    handle.write(result)
                return True
            except Exception as exc:  # pragma: no cover
                logger.error("Failed downloading Appwrite file '%s': %s", file_id, exc)
                return False

        with self._lock:
            asset = self._assert_tenant(self._memory_assets.get(file_id), tenant_id)
        if asset is None:
            return False
        try:
            with open(target_path, "wb") as handle:
                handle.write(base64.b64decode(asset["content_b64"]))
            return True
        except OSError as exc:
            logger.error("Failed writing local asset '%s': %s", file_id, exc)
            return False

    def download_file_bytes(self, file_id: str, tenant_id: Optional[str] = None) -> Optional[bytes]:
        """Return stored bytes for an already-authorized asset or artifact."""
        if self.storage:
            try:
                return self.storage.get_file_download(bucket_id=self.bucket_id, file_id=file_id)
            except Exception as exc:  # pragma: no cover - remote API dependent
                logger.error("Failed downloading Appwrite file '%s': %s", file_id, exc)
                return None

        with self._lock:
            asset = self._assert_tenant(self._memory_assets.get(file_id), tenant_id)
        if asset is None:
            return None
        try:
            return base64.b64decode(asset["content_b64"])
        except (KeyError, ValueError, base64.binascii.Error):
            return None

    def create_job_document(
        self,
        job_id: str,
        session_id: str,
        tenant_id: str,
        user_id: str,
        asset_filename: str,
        project_id: str = "default",
        asset_id: Optional[str] = None,
        experiment_id: Optional[str] = None,
        provider: Optional[str] = None,
        provider_job_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        document = {
            "job_id": job_id,
            "session_id": session_id,
            "tenant_id": tenant_id,
            "project_id": project_id,
            "user_id": user_id,
            "asset_id": asset_id or job_id,
            "experiment_id": experiment_id,
            "asset_filename": asset_filename,
            "status": "ENQUEUED",
            "stage": 0,
            "progress_percent": 0,
            "results_json": None,
            "error_json": None,
            "created_at": self._now(),
            "updated_at": self._now(),
        }
        if self.databases:
            if settings.APPWRITE_PROVIDER_FIELDS_ENABLED:
                document.update({"provider": provider, "provider_job_id": provider_job_id})
            try:  # pragma: no cover - remote API dependent
                return self._as_dict(self.databases.create_document(
                    database_id=self.database_id,
                    collection_id=self.jobs_collection_id,
                    document_id=job_id,
                    data=document,
                )) or document
            except Exception as exc:
                if getattr(exc, "code", None) == 409:
                    existing = self.get_job_document(job_id, tenant_id=tenant_id)
                    if existing is not None:
                        return existing
                logger.error("Appwrite job creation failed: %s", exc)
                raise
        with self._lock:
            self._memory_jobs[job_id] = deepcopy(document)
        return deepcopy(document)

    def update_job_status(
        self,
        job_id: str,
        status: str,
        stage: int = 0,
        progress: int = 0,
        tenant_id: Optional[str] = None,
        results_json: Optional[Dict[str, Any]] = None,
        error_json: Optional[Dict[str, Any]] = None,
        message: Optional[str] = None,
        provider: Optional[str] = None,
        provider_job_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        patch = {
            "status": status,
            "stage": stage,
            "progress_percent": max(0, min(100, progress)),
            "updated_at": self._now(),
        }
        if results_json is not None:
            patch["results_json"] = self._stringify(results_json)
        if error_json is not None:
            patch["error_json"] = self._stringify(error_json)
        if message is not None:
            patch["message"] = message
        if settings.APPWRITE_PROVIDER_FIELDS_ENABLED:
            if provider is not None:
                patch["provider"] = provider
            if provider_job_id is not None:
                patch["provider_job_id"] = provider_job_id

        current = self.get_job_document(job_id, tenant_id=tenant_id)
        if current is None:
            return None
        if self.databases:
            try:  # pragma: no cover
                return self._as_dict(self.databases.update_document(
                    database_id=self.database_id,
                    collection_id=self.jobs_collection_id,
                    document_id=job_id,
                    data=patch,
                ))
            except Exception as exc:
                logger.error("Appwrite job update failed: %s", exc)
                raise
        with self._lock:
            self._memory_jobs[job_id].update(patch)
            return deepcopy(self._memory_jobs[job_id])

    def get_job_document(self, job_id: str, tenant_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        if self.databases:
            try:  # pragma: no cover
                document = self.databases.get_document(
                    database_id=self.database_id,
                    collection_id=self.jobs_collection_id,
                    document_id=job_id,
                )
                return self._assert_tenant(document, tenant_id)
            except Exception:
                return None
        with self._lock:
            return self._assert_tenant(self._memory_jobs.get(job_id), tenant_id)

    def save_result_document(self, result: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
        analysis_id = result["analysis_id"]
        document = {
            "analysis_id": analysis_id,
            "schema_version": result.get("schema_version", "1.0.0"),
            "tenant_id": tenant_id,
            "project_id": result.get("project_id", "default"),
            "asset_id": result.get("asset_id", result.get("job_id", analysis_id)),
            "job_id": result.get("job_id", analysis_id),
            "mode": result.get("mode", "PREDICTIVE"),
            "status": result.get("status", "COMPLETE"),
            "result_json": self._stringify(result),
            "artifact_manifest_json": self._stringify(result.get("canvas_overlay", result.get("artifacts", {}))),
            "warnings_json": self._stringify(result.get("warnings", [])),
            "errors_json": self._stringify(result.get("errors", [])),
            "created_at": result.get("created_at", self._now()),
            "updated_at": self._now(),
        }
        if self.databases:
            try:  # pragma: no cover
                return self._as_dict(self.databases.create_document(
                    database_id=self.database_id,
                    collection_id=self.results_collection_id,
                    document_id=analysis_id,
                    data=document,
                )) or document
            except Exception as exc:
                logger.error("Appwrite result save failed: %s", exc)
                raise
        with self._lock:
            self._memory_results[analysis_id] = document
        return deepcopy(document)

    def get_result_document(self, analysis_id: str, tenant_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        if self.databases:
            try:  # pragma: no cover
                document = self.databases.get_document(
                    database_id=self.database_id,
                    collection_id=self.results_collection_id,
                    document_id=analysis_id,
                )
                return self._assert_tenant(document, tenant_id)
            except Exception:
                return None
        with self._lock:
            return self._assert_tenant(self._memory_results.get(analysis_id), tenant_id)

    def get_experiment_status(self, experiment_id: str, tenant_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        if not self.databases:
            with self._lock:
                matches = [doc for doc in self._memory_jobs.values() if doc.get("experiment_id") == experiment_id]
            return self._assert_tenant(matches[0] if matches else None, tenant_id)
        try:  # pragma: no cover
            from appwrite.query import Query

            queries = [Query.equal("experiment_id", experiment_id), Query.limit(1)]
            if tenant_id:
                queries.append(Query.equal("tenant_id", tenant_id))
            docs = self.databases.list_documents(
                database_id=self.database_id,
                collection_id=self.experiments_collection_id,
                queries=queries,
            )
            documents = docs.get("documents", []) if docs else []
            return documents[0] if documents else None
        except Exception as exc:
            logger.warning("Error querying experiment status: %s", exc)
            return None


appwrite_service = AppwriteService()
