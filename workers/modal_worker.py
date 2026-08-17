"""Provider-neutral Neuromarketing Studio GPU worker.

Modal invokes ``process_modal_job`` once per asynchronous task. The worker
resolves the asset from Appwrite, executes the real pipeline, persists the
canonical result envelope and artifacts, and returns the envelope to Modal.
"""

from __future__ import annotations

import base64
import copy
import logging
import os
import shutil
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
from scripts.media_adapters import UnsupportedMediaError, detect_media_type, prepare_media_bundle
from scripts.report_exports import export_all, write_json_report
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


def _sanitize_report_artifacts(report: Dict[str, Any], artifact_file_ids: Dict[str, str]) -> Dict[str, Any]:
    """Return a portable report containing Appwrite IDs, never worker-local paths."""
    sanitized = copy.deepcopy(report)
    for field in ("visual_artifacts", "report_exports"):
        artifact_map = sanitized.get(field)
        if not isinstance(artifact_map, dict):
            continue
        sanitized[field] = {
            name: artifact_file_ids.get(name) or artifact_file_ids.get(f"report_{name}")
            for name in artifact_map
            if name in artifact_file_ids or f"report_{name}" in artifact_file_ids
        }
    return sanitized


def _result_envelope(task: Dict[str, Any], report: Dict[str, Any], artifact_file_ids: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Adapt legacy pipeline output into the stable client delivery envelope."""
    return {
        "type": "FIGMA_NEUROMARKETING_DELIVERABLE_V1",
        "schema_version": "1.0.0",
        "job_id": task.get("job_id"),
        "session_id": task.get("session_id"),
        "tenant_id": task.get("tenant_id"),
        "project_id": task.get("project_id", "default"),
        "objective": task.get("objective", "OVERALL_HIERARCHY"),
        "asset_id": task.get("appwrite_file_id") or task.get("file_id") or task.get("asset_id") or task.get("job_id"),
        "artifact_file_ids": artifact_file_ids or {},
        "user_id": task.get("user_id"),
        "analysis_id": task.get("analysis_id") or task.get("experiment_id") or task.get("job_id"),
        "mode": task.get("mode", "PREDICTIVE"),
        "status": "COMPLETE",
        "canvas_overlay": report.get("visual_artifacts", {}),
        "neuromarketing_metrics": {
            "domain_kpis": report.get("metrics", {}),
            "mvp_diagnostic": report.get("mvp_diagnostic", {}),
            "linguistics": report.get("linguistics", {}),
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
    workspace: Optional[str] = None

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

        workspace = tempfile.mkdtemp(prefix=f"neuromarketing-{job_id}-")
        media_type = detect_media_type(temp_path)
        with VRAMManager.vram_stage("modal_full_execution"):
            if media_type in {"image", "video"}:
                report = run_full_pipeline(temp_path, output_dir=workspace, objective=task.get("objective", "OVERALL_HIERARCHY"))
            else:
                bundle = prepare_media_bundle(temp_path, os.path.join(workspace, "normalized"), max_frames=20)
                frame_reports = []
                for index, frame in enumerate(bundle.get("frames", [])[:20]):
                    frame_path = frame.get("frame_path")
                    if not frame_path:
                        continue
                    frame_reports.append(run_full_pipeline(
                        frame_path,
                        output_dir=os.path.join(workspace, f"frame_{index:03d}"),
                        objective=task.get("objective", "OVERALL_HIERARCHY"),
                    ))
                primary_report = frame_reports[0] if frame_reports else {}
                report = {
                    "status": "SUCCESS" if frame_reports or bundle.get("structured_data") else "INGESTED",
                    "media_type": bundle.get("media_type", media_type).upper(),
                    "pipeline_version": "5.0.0-media-adapter",
                    "job_id": job_id,
                    "experiment_id": analysis_id,
                    "asset": {
                        "filename": filename,
                        "frames_analyzed": len(frame_reports),
                        "structured_data_present": bool(bundle.get("structured_data")),
                    },
                    "evidence_status": bundle.get("structured_data", {}).get("evidence_status", "MODEL_INPUT_ASSET") if isinstance(bundle.get("structured_data"), dict) else "MODEL_INPUT_ASSET",
                    "structured_data": bundle.get("structured_data"),
                    "page_reports": [
                        {
                            "media_type": child.get("media_type"),
                            "metrics": child.get("metrics", {}),
                            "ctr_forecast": child.get("ctr_forecast", {}),
                            "neuromarketing_indices": child.get("neuromarketing_indices", {}),
                        }
                        for child in frame_reports
                    ],
                    "visual_artifacts": dict(primary_report.get("visual_artifacts", {})),
                    "interpretation_boundary": "Structured and rendered asset outputs are either measured file observations or model-derived visual diagnostics. They do not establish neural, psychological, memory, emotion, or causal behavioural outcomes without an appropriate empirical study.",
                }
                report_exports = export_all(report, os.path.join(workspace, "reports"))
                report["report_exports"] = report_exports
                report["visual_artifacts"].update({f"report_{kind}": path for kind, path in report_exports.items()})
                write_json_report(report, report_exports["json"])

        artifact_file_ids, artifact_errors = _persist_artifacts(service, report, tenant_id)
        sanitized_report = _sanitize_report_artifacts(report, artifact_file_ids)
        envelope = _result_envelope({**task, "analysis_id": analysis_id}, sanitized_report, artifact_file_ids)
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
        if workspace:
            shutil.rmtree(workspace, ignore_errors=True)
