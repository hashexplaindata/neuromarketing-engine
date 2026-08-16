"""Canonical authenticated REST routes for analysis jobs."""

from __future__ import annotations

import base64
import json
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel, Field

from core.appwrite_service import appwrite_service
from core.auth import AuthenticatedUser, verify_jwt_token
from core.upstash_queue import upstash_queue

logger = logging.getLogger("icm.api")
router = APIRouter()


class AnalysisRequest(BaseModel):
    image_base64: str = Field(..., min_length=16, description="Base64 encoded image or Figma canvas frame export")
    filename: str = Field(default="figma_export.png", min_length=1, max_length=240)
    project_id: str = Field(default="default", min_length=1, max_length=160)
    experiment_id: Optional[str] = Field(default=None, max_length=160)
    domain_module: str = Field(default="UI_UX_AND_DIGITAL_ADS", max_length=160)
    requested_permutations: int = Field(default=18, ge=2, le=256)
    media_type: str = Field(default="IMAGE", max_length=40)


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
    session_id = f"sess_{uuid.uuid4().hex[:12]}"
    job_id = f"job_{uuid.uuid4().hex[:16]}"
    asset_id = f"asset_{uuid.uuid4().hex[:16]}"
    experiment_id = request.experiment_id or f"exp_{uuid.uuid4().hex[:12]}"

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
        "requested_permutations": request.requested_permutations,
        "idempotency_key": idempotency_header,
    }
    upstash_queue.push_gpu_job(task_payload)

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
    cached_state = upstash_queue.get_job_state(job_id, tenant_id=current_user.tenant_id)
    if cached_state:
        return cached_state

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
    }


@router.get("/jobs/{job_id}/artifacts/{artifact_name}")
async def get_job_artifact(job_id: str, artifact_name: str, current_user: AuthenticatedUser = Depends(get_current_user)):
    """Stream one allow-listed persisted artifact for the requesting tenant."""
    allowed = {
        "original_image": ("original_image", "image/jpeg"),
        "thermal_heatmap": ("thermal_heatmap", "image/png"),
        "focus_map": ("focus_map", "image/png"),
        "scanpath_map": ("scanpath_map", "image/png"),
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
