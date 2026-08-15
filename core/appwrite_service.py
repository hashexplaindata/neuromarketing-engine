"""
Appwrite BaaS Integration Service
Handles Authentication, Document Databases, and Storage Buckets
"""

import io
import json
import logging
from typing import Dict, Any, Optional
from core.config import settings

logger = logging.getLogger("icm.appwrite")

try:
    from appwrite.client import Client
    from appwrite.services.account import Account
    from appwrite.services.databases import Databases
    from appwrite.services.storage import Storage
    from appwrite.input_file import InputFile
except ImportError:
    Client = None

class AppwriteService:
    def __init__(self):
        self.endpoint = settings.APPWRITE_ENDPOINT
        self.project_id = settings.APPWRITE_PROJECT_ID
        self.api_key = settings.APPWRITE_API_KEY
        self.database_id = settings.APPWRITE_DATABASE_ID
        self.jobs_collection_id = settings.APPWRITE_JOBS_COLLECTION_ID
        self.bucket_id = settings.APPWRITE_STORAGE_BUCKET_ID
        
        # Local mock storage for development/offline testing
        self._mock_db: Dict[str, Dict[str, Any]] = {}
        self._mock_files: Dict[str, bytes] = {}

        if Client and self.api_key and not self.api_key.startswith("appwrite_mock"):
            try:
                self.client = Client()
                self.client.set_endpoint(self.endpoint)
                self.client.set_project(self.project_id)
                self.client.set_key(self.api_key)
                self.databases = Databases(self.client)
                self.storage = Storage(self.client)
                self.account = Account(self.client)
                logger.info(f"Appwrite client connected to {self.endpoint}")
            except Exception as e:
                logger.warning(f"Appwrite client init notice: {e}")
                self.client = None
        else:
            self.client = None

    def verify_appwrite_jwt(self, jwt_token: str) -> Dict[str, Any]:
        """
        Verifies Appwrite User JWT token.
        Extracts user_id, tenant_id/org, and user profile.
        """
        if not jwt_token:
            raise ValueError("Missing Appwrite JWT token")
            
        if jwt_token.startswith("Bearer ") or jwt_token.startswith("bearer "):
            jwt_token = jwt_token[7:].strip()

        # Dev/Test Mock token support: "test_tenant_{tenant_id}"
        if jwt_token.startswith("test_tenant_"):
            tenant_id = jwt_token.replace("test_tenant_", "").strip()
            return {
                "user_id": "usr_appwrite_dev",
                "tenant_id": tenant_id,
                "email": f"designer@{tenant_id}.com",
                "name": "Figma Art Director"
            }

        # Real Appwrite JWT verification when live client exists
        if self.client:
            try:
                user_client = Client()
                user_client.set_endpoint(self.endpoint)
                user_client.set_project(self.project_id)
                user_client.set_jwt(jwt_token)
                user_account = Account(user_client)
                user_data = user_account.get()
                
                user_id = user_data.get("$id", "usr_unknown")
                prefs = user_data.get("prefs", {})
                tenant_id = prefs.get("tenant_id") or f"org_{user_id[:8]}"
                email = user_data.get("email", "designer@agency.com")
                
                return {
                    "user_id": user_id,
                    "tenant_id": tenant_id,
                    "email": email,
                    "name": user_data.get("name", "Appwrite User")
                }
            except Exception as e:
                logger.error(f"Appwrite JWT verification failed: {e}")
                raise ValueError(f"Invalid or expired Appwrite JWT: {str(e)}")

        raise ValueError("Appwrite client not connected for token validation")

    def create_job_document(self, job_id: str, session_id: str, tenant_id: str, user_id: str, asset_filename: str) -> Dict[str, Any]:
        """Creates an initial job document in Appwrite Database."""
        doc_data = {
            "job_id": job_id,
            "session_id": session_id,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "asset_filename": asset_filename,
            "status": "ENQUEUED",
            "stage": 0,
            "progress_percent": 0,
            "created_at": None,
            "results_json": "{}"
        }
        
        if self.client and hasattr(self, 'databases'):
            try:
                doc = self.databases.create_document(
                    database_id=self.database_id,
                    collection_id=self.jobs_collection_id,
                    document_id=job_id,
                    data=doc_data
                )
                return doc
            except Exception as e:
                logger.warning(f"Appwrite create_document fallback: {e}")
                
        self._mock_db[job_id] = doc_data
        return doc_data

    def update_job_status(self, job_id: str, status: str, stage: int = 0, progress: int = 0, results: Optional[Dict[str, Any]] = None):
        """Updates job status and progress in Appwrite Database."""
        update_data = {
            "status": status,
            "stage": stage,
            "progress_percent": progress
        }
        if results:
            update_data["results_json"] = json.dumps(results)

        if self.client and hasattr(self, 'databases'):
            try:
                self.databases.update_document(
                    database_id=self.database_id,
                    collection_id=self.jobs_collection_id,
                    document_id=job_id,
                    data=update_data
                )
                return
            except Exception as e:
                logger.warning(f"Appwrite update_document fallback: {e}")

        # In-memory mock update / auto-create if needed
        if job_id not in self._mock_db:
            self._mock_db[job_id] = {"job_id": job_id}
        self._mock_db[job_id].update(update_data)

    def get_job_document(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Fetches job record from Appwrite Database."""
        if self.client and hasattr(self, 'databases'):
            try:
                return self.databases.get_document(
                    database_id=self.database_id,
                    collection_id=self.jobs_collection_id,
                    document_id=job_id
                )
            except Exception:
                pass
        return self._mock_db.get(job_id)

    def upload_asset_file(self, file_id: str, file_bytes: bytes, filename: str) -> str:
        """Uploads creative asset to Appwrite Storage Bucket."""
        if self.client and hasattr(self, 'storage'):
            try:
                input_file = InputFile.from_bytes(file_bytes, filename=filename)
                file_obj = self.storage.create_file(
                    bucket_id=self.bucket_id,
                    file_id=file_id,
                    file=input_file
                )
                return file_obj.get("$id", file_id)
            except Exception as e:
                logger.warning(f"Appwrite storage upload fallback: {e}")
                
        self._mock_files[file_id] = file_bytes
        return file_id

appwrite_service = AppwriteService()
