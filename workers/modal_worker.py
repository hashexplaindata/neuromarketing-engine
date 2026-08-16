"""Provider-neutral Neuromarketing Studio GPU worker.

Modal invokes ``process_modal_job`` once per asynchronous task. The worker
resolves the asset from Appwrite, executes the real pipeline, persists the
canonical result envelope and artifacts, and returns the envelope to Modal.
"""

from __future__ import annotations

import base64
import logging
import os
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from core.appwrite_service import appwrite_service
from core.contracts import JobStatus
from core.vram_manager import VRAMManager
from scripts.run_full_pipeline import run_full_pipeline

logger = logging.getLogger("modal_worker")


def _decode_data_url(value: str) -> bytes:
    raw = value.split(",", 1)[1] if "," in value else value
    return base64.b64decode(raw, validate=True)


def _safe_suffix(filename: str) -> str:
    suffix = Path(filename or "asset.bin").suffix.lower()
    return suffix if suffix and len(suffix) <= 10 else ".bin"


def _persist_artifacts(service, report: Dict[str, Any], tenant_id: str) -> tuple[Dict[str, str], list[Dict[str, str]]]:
    """Move worker-local visual artifacts into durable tenant-scoped storage."""
    artifact_ids: Dict[str, str] = {}
    errors: list[Dict[str, str]] = []
    for artifact_name, raw_path in (report.get("visual_artifacts", {}) or {}).items():
        if not raw_path or not isinstance(raw_path, str):
            continue
        path = Path(raw_path)
        if not path.is_file():
            errors.append({"artifact": artifact_name, "error": "worker artifact file does not exist"})
            continue
        try:
            artifact_id = f"artifact_{uuid.uuid4().hex[:20]}"
            service.upload_asset_file(artifact_id, path.read_bytes(), path.name, tenant_id=tenant_id)
            artifact_ids[artifact_name] = artifact_id
        except Exception as exc:  # artifact failure should not erase valid numerical results
            logger.warning("Artifact upload failed for %s: %s", artifact_name, exc)
            errors.append({"artifact": artifact_name, "error": str(exc)[:300]})
    return artifact_ids, errors


def _result_envelope(task: Dict[str, Any], report: Dict[str, Any], artifact_file_ids: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Adapt legacy pipeline output into the stable client delivery envelope."""
    return {
        "type": "FIGMA_NEUROMARKETING_DELIVERABLE_V1",
        "schema_version": "1.0.0",
        "job_id": task.get("job_id"),
        "session_id": task.get("session_id"),
        "tenant_id": task.get("tenant_id"),
        "project_id": task.get("project_id", "default"),
        "asset_id": task.get("appwrite_file_id") or task.get("file_id") or task.get("asset_id") or task.get("job_id"),
        "artifact_file_ids": artifact_file_ids or {},
        "user_id": task.get("user_id"),
        "analysis_id": task.get("analysis_id") or task.get("experiment_id") or task.get("job_id"),
        "mode": task.get("mode", "PREDICTIVE"),
        "status": "COMPLETE",
        "canvas_overlay": report.get("visual_artifacts", {}),
        "neuromarketing_metrics": {
            "domain_kpis": report.get("metrics", {}),
            "biometrics": report.get("biometrics", {}),
            "linguistics": report.get("linguistics", {}),
            "neuromarketing_indices": report.get("neuromarketing_indices", {}),
            "ctr_forecast": report.get("ctr_forecast", {}),
            "n_factorial": report.get("n_factorial"),
        },
        "report": report,
    }


def process_modal_job(task: Dict[str, Any], service=None) -> Dict[str, Any]:
    """Execute one real task and persist its status/result to Appwrite."""
    service = service or appwrite_service
    job_id = task.get("job_id", f"job_{int(time.time())}")
    tenant_id = task.get("tenant_id", "tenant_unknown")
    filename = task.get("filename", "asset.bin")
    analysis_id = task.get("analysis_id") or task.get("experiment_id") or job_id
    temp_path: Optional[str] = None

    try:
        service.update_job_status(job_id, JobStatus.RUNNING.value, stage=1, progress=5, tenant_id=tenant_id, message="Modal worker accepted analysis job")

        with tempfile.NamedTemporaryFile(prefix=f"{job_id}_", suffix=_safe_suffix(filename), delete=False) as handle:
            temp_path = handle.name
            if task.get("image_base64"):
                handle.write(_decode_data_url(task["image_base64"]))
            elif task.get("appwrite_file_id") or task.get("file_id"):
                file_id = task.get("appwrite_file_id") or task.get("file_id")
                if not service.download_file_to_path(file_id, temp_path, tenant_id=tenant_id):
                    raise FileNotFoundError(f"Unable to download asset '{file_id}'")
            else:
                raise ValueError("Task has neither image_base64 nor an Appwrite file ID")

        with VRAMManager.vram_stage("modal_full_execution"):
            report = run_full_pipeline(temp_path)

        artifact_file_ids, artifact_errors = _persist_artifacts(service, report, tenant_id)
        envelope = _result_envelope({**task, "analysis_id": analysis_id}, report, artifact_file_ids)
        if artifact_errors:
            envelope["artifact_errors"] = artifact_errors
        service.save_result_document(envelope, tenant_id=tenant_id)
        service.update_job_status(
            job_id,
            JobStatus.COMPLETE.value,
            stage=6,
            progress=100,
            tenant_id=tenant_id,
            results_json=envelope,
            message="Analysis completed",
        )
        return envelope
    except Exception as exc:
        error = {
            "code": "ANALYSIS_EXECUTION_FAILED",
            "message": str(exc),
            "retryable": False,
        }
        service.update_job_status(
            job_id,
            JobStatus.FAILED.value,
            stage=0,
            progress=0,
            tenant_id=tenant_id,
            error_json=error,
            message="Analysis failed",
        )
        logger.exception("Modal job %s failed", job_id)
        raise
    finally:
        if temp_path:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
