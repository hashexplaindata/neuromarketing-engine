"""Canonical authenticated REST routes for analysis jobs."""

from __future__ import annotations

import base64
import json
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel, Field

from core.appwrite_service import appwrite_service
from core.auth import AuthenticatedUser, verify_jwt_token
from core.modal_provider import modal_provider

logger = logging.getLogger("icm.api")
router = APIRouter()


class AnalysisRequest(BaseModel):
    image_base64: Optional[str] = Field(default=None, min_length=16, description="Base64 encoded image for compatibility clients")
    file_id: Optional[str] = Field(default=None, min_length=1, max_length=160, description="Previously uploaded Appwrite asset file ID")
    filename: str = Field(default="figma_export.png", min_length=1, max_length=240)
    project_id: str = Field(default="default", min_length=1, max_length=160)
    experiment_id: Optional[str] = Field(default=None, max_length=160)
    domain_module: str = Field(default="UI_UX_AND_DIGITAL_ADS", max_length=160)
    requested_permutations: int = Field(default=18, ge=2, le=256)
    media_type: str = Field(default="IMAGE", max_length=40)
    objective: str = Field(default="OVERALL_HIERARCHY", max_length=80)


class JobInitiatedResponse(BaseModel):
    job_id: str
    session_id: str
    tenant_id: str
    project_id: str
    status: str
    ws_stream_url: str
    estimated_duration_seconds: int


async def get_current_user(authorization: Optional[str] = Header(None)) -> AuthenticatedUser:
    """Validate an Appwrite or local signed bearer token."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization Header. Please provide a valid Bearer JWT.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return verify_jwt_token(authorization)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


@router.post("/assets/upload", status_code=status.HTTP_201_CREATED)
async def upload_analysis_asset(
    file: UploadFile = File(...),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Store one static creative before the analysis job is deliberately started."""
    filename = file.filename or "creative_upload"
    content_type = (file.content_type or "").lower()
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if content_type not in {"image/jpeg", "image/png", "image/webp"} and suffix not in {"jpg", "jpeg", "png", "webp"}:
        raise HTTPException(status_code=400, detail="The MVP supports static image creatives only: JPG, PNG, or WebP.")
    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="The uploaded creative is empty.")
    if len(content) > 8 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="For this MVP, choose an image smaller than 8 MB.")
    asset_id = f"asset_{uuid.uuid4().hex[:16]}"
    appwrite_service.upload_asset_file(asset_id, content, filename, tenant_id=current_user.tenant_id)
    return {
        "file_id": asset_id,
        "filename": filename,
        "media_type": "IMAGE",
        "size_bytes": len(content),
    }


@router.post("/analyze", response_model=JobInitiatedResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_analysis_job(
    request: AnalysisRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    idempotency_header: Optional[str] = Header(default=None, alias="X-Idempotency-Key"),
):
    """Stage an asset, persist a tenant-scoped job, and enqueue real work.

    The endpoint accepts a lightweight base64 path for compatibility with the
    existing Figma adapter. Large production uploads should use direct object
    storage upload and submit a file reference through the same job contract.
    """
    if request.media_type.upper() != "IMAGE":
        raise HTTPException(status_code=400, detail="The MVP supports static image creatives only: JPG, PNG, or WebP.")
    if not request.image_base64 and not request.file_id:
        raise HTTPException(status_code=400, detail="Provide an uploaded file_id before starting analysis.")

    session_id = f"sess_{uuid.uuid4().hex[:12]}"
    job_id = f"job_{uuid.uuid4().hex[:16]}"
    asset_id = f"asset_{uuid.uuid4().hex[:16]}"
    experiment_id = request.experiment_id or f"exp_{uuid.uuid4().hex[:12]}"

    if request.file_id:
        asset_id = request.file_id
    else:
        try:
            raw_b64 = request.image_base64.split(",", 1)[1] if "," in request.image_base64 else request.image_base64
            image_bytes = base64.b64decode(raw_b64, validate=True)
        except Exception as exc:
            raise HTTPException(status_code=400, detail="image_base64 is not valid base64") from exc
        appwrite_service.upload_asset_file(asset_id, image_bytes, request.filename, tenant_id=current_user.tenant_id)
    appwrite_service.create_job_document(
        job_id=job_id,
        session_id=session_id,
        tenant_id=current_user.tenant_id,
        user_id=current_user.user_id,
        asset_filename=request.filename,
        project_id=request.project_id,
        asset_id=asset_id,
        experiment_id=experiment_id,
        provider=modal_provider.provider_name,
    )

    task_payload = {
        "job_id": job_id,
        "analysis_id": experiment_id,
        "session_id": session_id,
        "tenant_id": current_user.tenant_id,
        "user_id": current_user.user_id,
        "project_id": request.project_id,
        "appwrite_file_id": asset_id,
        "filename": request.filename,
        "media_type": request.media_type,
        "domain_module": request.domain_module,
        "objective": request.objective,
        "requested_permutations": request.requested_permutations,
        "idempotency_key": idempotency_header,
    }
    try:
        provider_job_id = modal_provider.submit(task_payload)
        appwrite_service.update_job_status(
            job_id,
            "ENQUEUED",
            tenant_id=current_user.tenant_id,
            message="Modal GPU task submitted",
            provider=modal_provider.provider_name,
            provider_job_id=provider_job_id,
        )
    except Exception as exc:
        appwrite_service.update_job_status(
            job_id,
            "FAILED",
            stage=0,
            progress=0,
            tenant_id=current_user.tenant_id,
            error_json={"code": "GPU_SUBMISSION_FAILED", "message": str(exc)[:500], "retryable": True},
            message="Modal GPU task submission failed",
            provider=modal_provider.provider_name,
        )
        raise HTTPException(status_code=503, detail="GPU execution provider unavailable") from exc

    return JobInitiatedResponse(
        job_id=job_id,
        session_id=session_id,
        tenant_id=current_user.tenant_id,
        project_id=request.project_id,
        status="ENQUEUED",
        ws_stream_url=f"/ws/jobs/{job_id}",
        estimated_duration_seconds=15,
    )


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str, current_user: AuthenticatedUser = Depends(get_current_user)):
    """Return only the requesting tenant’s job state."""
    document = appwrite_service.get_job_document(job_id, tenant_id=current_user.tenant_id)
    if document is None:
        # Backward-compatible, non-leaking response for clients that poll before
        # the durable document is visible. No result or cross-tenant data is sent.
        return {
            "job_id": job_id,
            "tenant_id": current_user.tenant_id,
            "status": "PROCESSING",
            "stage": 0,
            "progress_percent": 0,
            "known": False,
            "message": "Task status is not yet available",
        }

    return {
        "job_id": job_id,
        "tenant_id": current_user.tenant_id,
        "status": document.get("status", "ENQUEUED"),
        "stage": document.get("stage", 0),
        "progress_percent": document.get("progress_percent", 0),
        "known": True,
        "results": document.get("results_json"),
        "error": document.get("error_json"),
        "message": document.get("message"),
        "provider": document.get("provider"),
        "provider_job_id": document.get("provider_job_id"),
    }


@router.get("/jobs/{job_id}/artifacts/{artifact_name}")
async def get_job_artifact(job_id: str, artifact_name: str, current_user: AuthenticatedUser = Depends(get_current_user)):
    """Stream one allow-listed persisted artifact for the requesting tenant."""
    allowed = {
        "original_image": ("original_image", "image/jpeg"),
        "thermal_heatmap": ("thermal_heatmap", "image/png"),
        "focus_map": ("focus_map", "image/png"),
        "scanpath_map": ("scanpath_map", "image/png"),
        "report_json": ("report_json", "application/json"),
        "report_csv": ("report_csv", "text/csv"),
        "report_xlsx": ("report_xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        "report_html": ("report_html", "text/html"),
        "report_pdf": ("report_pdf", "application/pdf"),
    }
    selected = allowed.get(artifact_name)
    if selected is None:
        raise HTTPException(status_code=404, detail="Artifact not found")

    document = appwrite_service.get_job_document(job_id, tenant_id=current_user.tenant_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Job not found")

    results = document.get("results_json")
    if isinstance(results, str):
        try:
            results = json.loads(results)
        except ValueError:
            results = None
    artifact_ids = results.get("artifact_file_ids", {}) if isinstance(results, dict) else {}
    file_id = artifact_ids.get(selected[0])
    if not file_id:
        raise HTTPException(status_code=404, detail="Artifact not available")

    content = appwrite_service.download_file_bytes(file_id, tenant_id=current_user.tenant_id)
    if content is None:
        raise HTTPException(status_code=404, detail="Artifact not available")
    return Response(content=content, media_type=selected[1], headers={"Cache-Control": "private, max-age=3600"})
