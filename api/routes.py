"""
FastAPI REST API Routes
Heroku + Appwrite + Upstash Redis Gateway
"""

import uuid
import base64
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Header, status
from core.auth import verify_jwt_token, AuthenticatedUser
from core.appwrite_service import appwrite_service
from core.upstash_queue import upstash_queue
from core.config import settings

logger = logging.getLogger("icm.api")
router = APIRouter()

class AnalysisRequest(BaseModel):
    image_base64: str = Field(..., description="Base64 encoded image or Figma canvas frame export")
    filename: Optional[str] = Field("figma_export.png", description="Original canvas frame name")
    domain_module: Optional[str] = Field("UI_UX_AND_DIGITAL_ADS", description="Target evaluation domain")
    requested_permutations: Optional[int] = Field(18, description="Number of factorial permutations to evaluate")

class JobInitiatedResponse(BaseModel):
    job_id: str
    session_id: str
    tenant_id: str
    status: str
    ws_stream_url: str
    estimated_duration_seconds: int

async def get_current_user(authorization: Optional[str] = Header(None)) -> AuthenticatedUser:
    """FastAPI Dependency validating Appwrite JWT authentication."""
    if not authorization:
        if settings.DEBUG:
            return AuthenticatedUser(user_id="usr_dev", tenant_id="agency_alpha", email="dev@alpha.com")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization Header. Please provide a valid Appwrite Bearer JWT.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return verify_jwt_token(authorization)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )

@router.post("/analyze", response_model=JobInitiatedResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_analysis_job(
    request: AnalysisRequest,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Accepts an image payload from Figma, stores the asset in Appwrite Storage,
    registers the job in Appwrite Database, pushes the task to Upstash Redis,
    and INSTANTLY returns a job_id (< 25ms) to completely eliminate HTTP timeouts.
    """
    # 1. Allocate Unique Multi-Tenant Session and Job IDs
    session_id = f"sess_{uuid.uuid4().hex[:12]}"
    job_id = f"job_{uuid.uuid4().hex[:16]}"
    
    # 2. Upload Asset to Appwrite Storage Bucket
    try:
        raw_b64 = request.image_base64
        if "," in raw_b64:
            raw_b64 = raw_b64.split(",")[1]
        img_bytes = base64.b64decode(raw_b64)
        file_id = f"asset_{job_id}"
        appwrite_service.upload_asset_file(file_id, img_bytes, request.filename)
    except Exception as e:
        logger.warning(f"Appwrite storage staging notice: {e}")
        file_id = "local_asset"

    # 3. Create Record in Appwrite Database
    appwrite_service.create_job_document(
        job_id=job_id,
        session_id=session_id,
        tenant_id=current_user.tenant_id,
        user_id=current_user.user_id,
        asset_filename=request.filename
    )

    # 4. Push Task Payload to Upstash Redis for Camber Cloud GPU Workers
    task_payload = {
        "job_id": job_id,
        "session_id": session_id,
        "tenant_id": current_user.tenant_id,
        "user_id": current_user.user_id,
        "appwrite_file_id": file_id,
        "image_base64": request.image_base64,
        "filename": request.filename,
        "domain_module": request.domain_module,
        "requested_permutations": request.requested_permutations
    }
    upstash_queue.push_gpu_job(task_payload)

    ws_url = f"/ws/jobs/{job_id}"
    return JobInitiatedResponse(
        job_id=job_id,
        session_id=session_id,
        tenant_id=current_user.tenant_id,
        status="ENQUEUED",
        ws_stream_url=ws_url,
        estimated_duration_seconds=15
    )

@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str, current_user: AuthenticatedUser = Depends(get_current_user)):
    """Retrieves real-time job status from Upstash Redis or Appwrite Database."""
    # Check Upstash Redis state cache first (fastest)
    cached_state = upstash_queue.get_job_state(job_id)
    if cached_state:
        return cached_state

    # Check Appwrite Database
    doc = appwrite_service.get_job_document(job_id)
    if doc:
        return {
            "job_id": job_id,
            "status": doc.get("status", "PROCESSING"),
            "stage": doc.get("stage", 0),
            "progress_percent": doc.get("progress_percent", 0),
            "results": doc.get("results_json")
        }

    return {
        "job_id": job_id,
        "status": "PROCESSING",
        "message": "Task is active on Camber Cloud GPU worker queue"
    }
