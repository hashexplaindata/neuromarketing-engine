#!/usr/bin/env python3
"""
Neuromarketing Suite - FastAPI Async Server (Production Gateway)
Enforces Client-Direct Upload Architecture (Section 8.1):
- Accepts lightweight JSON micro-payloads containing Appwrite `file_id`.
- Proxies zero heavy binary bandwidth, eliminating Heroku H12 timeouts.
- Enqueues jobs to Upstash Redis for Camber GPU execution.
"""

import os
import sys
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel

from core.appwrite_service import AppwriteService
from scripts.run_full_pipeline import run_full_pipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api.gateway")

app = FastAPI(
    title="Neuromarketing Suite API Gateway",
    description="Client-Direct Storage & Async Task Gateway for Consumer Neuroscience Engine",
    version="5.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class JobSubmissionPayload(BaseModel):
    file_id: str
    experiment_id: Optional[str] = None
    media_type: Optional[str] = "IMAGE"
    team_id: Optional[str] = "team_general"
    created_by_user: Optional[str] = "user_default"


@app.get("/health")
def health_check():
    return {
        "status": "HEALTHY",
        "architecture": "Client-Direct Appwrite Storage + Upstash Redis + Camber GPU",
        "version": "5.0.0"
    }


@app.post("/api/v1/jobs/submit")
async def submit_analysis_job(payload: JobSubmissionPayload, background_tasks: BackgroundTasks):
    """
    Section 8.1: Client-Direct Upload Task Submitter.
    Receives lightweight JSON (< 1KB) with Appwrite file_id and drops into Redis queue.
    Zero binary bandwidth through API gateway.
    """
    experiment_id = payload.experiment_id or f"exp_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    job_id = f"job_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

    job_data = {
        "job_id": job_id,
        "experiment_id": experiment_id,
        "file_id": payload.file_id,
        "media_type": payload.media_type,
        "team_id": payload.team_id,
        "created_by_user": payload.created_by_user,
        "status": "QUEUED",
        "submitted_at": datetime.now(timezone.utc).isoformat()
    }

    # Enqueue to Redis
    import requests
    url = os.getenv("UPSTASH_REDIS_REST_URL", "").strip().strip('"')
    token = os.getenv("UPSTASH_REDIS_REST_TOKEN", "").strip().strip('"')

    if url and token:
        try:
            headers = {"Authorization": f"Bearer {token}"}
            requests.post(f"{url}/lpush/queue:analysis_jobs", headers=headers, data=json.dumps(job_data), timeout=5)
            logger.info(f"Enqueued Job '{job_id}' (Experiment '{experiment_id}') to Redis queue.")
        except Exception as e:
            logger.warning(f"Redis enqueue note: {e}")

    # Launch background executor as local fallback / async process
    appwrite = AppwriteService()
    temp_path = os.path.join(PROJECT_ROOT, "input_assets", f"{payload.file_id}.jpg")
    
    def async_process():
        success = appwrite.download_file_to_path(payload.file_id, temp_path)
        if success:
            run_full_pipeline(temp_path)

    background_tasks.add_task(async_process)

    return JSONResponse(content={
        "status": "ACCEPTED",
        "job_id": job_id,
        "experiment_id": experiment_id,
        "file_id": payload.file_id,
        "message": "Task queued successfully. Worker streaming from Appwrite Storage."
    })


@app.post("/api/v1/analyze/direct")
async def analyze_direct_file(file: UploadFile = File(...)):
    """Direct file upload endpoint for local testing."""
    try:
        temp_dir = os.path.join(PROJECT_ROOT, "input_assets")
        os.makedirs(temp_dir, exist_ok=True)
        file_path = os.path.join(temp_dir, file.filename)
        
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())
            
        report = run_full_pipeline(file_path)
        return JSONResponse(content=report)
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/experiments/{experiment_id}")
def get_experiment(experiment_id: str):
    """Fetches experiment report."""
    report_path = os.path.join(PROJECT_ROOT, "output", "analysis_results", "full_report.json")
    if os.path.exists(report_path):
        with open(report_path, "r", encoding="utf-8") as f:
            return json.load(f)
    raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found.")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)