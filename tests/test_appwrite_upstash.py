"""
Appwrite, Upstash Redis & Camber Cloud Worker Tests
Verifies BaaS integration, instant queue dispatch, and end-to-end processing.
"""

import json
import base64
import pytest
from fastapi.testclient import TestClient
from api.main import app
from core.appwrite_service import appwrite_service
from core.upstash_queue import upstash_queue
from core.auth import create_access_token
from workers.camber_worker import process_camber_gpu_job

client = TestClient(app)

def test_appwrite_auth_and_database():
    tenant = "agency_ogilvy"
    user_id = "usr_ogilvy_99"
    job_id = "job_test_appwrite_01"
    session_id = "sess_test_appwrite_01"
    
    # 1. Test JWT Verification
    user_data = appwrite_service.verify_appwrite_jwt(f"test_tenant_{tenant}")
    assert user_data["tenant_id"] == tenant
    assert user_data["user_id"] == "usr_appwrite_dev"
    
    # 2. Test Document Creation in Appwrite Database
    doc = appwrite_service.create_job_document(job_id, session_id, tenant, user_id, "hero_banner.png")
    assert doc["job_id"] == job_id
    assert doc["status"] == "ENQUEUED"
    
    # 3. Test Document Update
    appwrite_service.update_job_status(job_id, "PROCESSING", stage=2, progress=35)
    updated = appwrite_service.get_job_document(job_id)
    assert updated["status"] == "PROCESSING"
    assert updated["stage"] == 2
    assert updated["progress_percent"] == 35

def test_upstash_redis_queue_dispatch():
    # Clear any residual items from earlier tests
    while upstash_queue.pop_gpu_job(timeout=0):
        pass

    job_data = {
        "job_id": "job_upstash_test_01",
        "session_id": "sess_upstash_01",
        "tenant_id": "agency_havas",
        "user_id": "usr_havas_01",
        "filename": "display_ad.png"
    }
    
    # 1. Push to Upstash Queue
    jid = upstash_queue.push_gpu_job(job_data)
    assert jid == "job_upstash_test_01"
    
    # 2. Pop from Upstash Queue for Camber Worker
    popped = upstash_queue.pop_gpu_job(timeout=1)
    assert popped is not None
    assert popped["job_id"] == "job_upstash_test_01"
    assert popped["tenant_id"] == "agency_havas"

def test_fastapi_analyze_endpoint_instant_return():
    token = create_access_token(
        tenant_id="agency_mccann",
        user_id="usr_mccann_01",
        email="art_director@mccann.com"
    )
    
    headers = {"Authorization": f"Bearer {token}"}
    sample_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    
    # Send request
    response = client.post("/api/v1/analyze", headers=headers, json={
        "image_base64": sample_b64,
        "filename": "landing_page_v1.png",
        "requested_permutations": 18
    })
    
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert "session_id" in data
    assert data["tenant_id"] == "agency_mccann"
    assert data["status"] == "ENQUEUED"
    assert data["ws_stream_url"].startswith("/ws/jobs/job_")

def test_camber_cloud_gpu_worker_pipeline_execution():
    job_id = "job_camber_e2e_01"
    session_id = "sess_camber_e2e_01"
    
    # Pre-register job document in Appwrite DB
    appwrite_service.create_job_document(job_id, session_id, "agency_publicis", "usr_pub_01", "packaging_box.png")

    task = {
        "job_id": job_id,
        "session_id": session_id,
        "tenant_id": "agency_publicis",
        "user_id": "usr_pub_01",
        "image_base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        "filename": "packaging_box.png"
    }
    
    # Execute Camber Cloud GPU pipeline worker
    payload = process_camber_gpu_job(task)
    
    assert payload is not None
    assert payload["type"] == "FIGMA_NEUROMARKETING_DELIVERABLE_V1"
    assert "canvas_overlay" in payload
    assert "neuromarketing_metrics" in payload
    assert "domain_kpis" in payload["neuromarketing_metrics"]
    
    # Verify Appwrite Database marked as COMPLETED
    doc = appwrite_service.get_job_document(job_id)
    assert doc is not None
    assert doc["status"] == "COMPLETED"
    assert doc["stage"] == 6
    assert doc["progress_percent"] == 100
