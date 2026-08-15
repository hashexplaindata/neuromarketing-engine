"""
FastAPI Gateway & Route Integration Tests (Heroku + Appwrite + Upstash Stack)
Verifies HTTP endpoints, Appwrite JWT security, and zero-timeout async dispatch.
"""

import pytest
from fastapi.testclient import TestClient
from api.main import app
from core.auth import create_access_token

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"

def test_analyze_unauthorized_rejection():
    # Calling analyze without Auth header should return 401
    response = client.post("/api/v1/analyze", json={
        "image_base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    })
    assert response.status_code == 401

def test_analyze_authorized_job_initiation():
    # Generate test JWT for an agency
    token = create_access_token(
        tenant_id="agency_dentsu",
        user_id="usr_dentsu_01",
        email="art_director@dentsu.com"
    )
    
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post("/api/v1/analyze", headers=headers, json={
        "image_base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        "filename": "hero_banner.png",
        "requested_permutations": 8
    })
    
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert "session_id" in data
    assert data["tenant_id"] == "agency_dentsu"
    assert data["status"] == "ENQUEUED"
    assert data["ws_stream_url"].startswith("/ws/jobs/job_")

def test_job_status_endpoint():
    token = create_access_token("agency_dentsu", "usr_dentsu_01", "dev@dentsu.com")
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/jobs/job_12345", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == "job_12345"
    assert "status" in data
