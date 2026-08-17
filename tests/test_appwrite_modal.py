"""Appwrite, Modal provider, and worker contract tests."""

import base64
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from api.main import app
from core.appwrite_service import appwrite_service
from core.auth import create_access_token
from core.modal_provider import modal_provider
from workers.modal_worker import _result_envelope, _sanitize_report_artifacts, process_modal_job

client = TestClient(app)


def test_appwrite_auth_and_database():
    tenant = "agency_ogilvy"
    user_id = "usr_ogilvy_99"
    job_id = f"job_test_appwrite_{uuid.uuid4().hex[:10]}"
    session_id = f"sess_test_appwrite_{uuid.uuid4().hex[:10]}"

    user_data = appwrite_service.verify_appwrite_jwt(f"test_tenant_{tenant}")
    assert user_data["tenant_id"] == tenant
    assert user_data["user_id"] == "usr_appwrite_dev"

    doc = appwrite_service.create_job_document(job_id, session_id, tenant, user_id, "hero_banner.png", provider="modal")
    assert doc["job_id"] == job_id
    assert doc["status"] == "ENQUEUED"
    assert doc.get("provider") in (None, "modal")

    appwrite_service.update_job_status(job_id, "PROCESSING", stage=2, progress=35, provider_job_id="fc-test-123")
    updated = appwrite_service.get_job_document(job_id)
    assert updated["status"] == "PROCESSING"
    assert updated["stage"] == 2
    assert updated["progress_percent"] == 35
    assert updated.get("provider_job_id") in (None, "fc-test-123")


def test_fastapi_analyze_endpoint_submits_modal_job(monkeypatch):
    submitted = {}

    def fake_submit(payload):
        submitted.update(payload)
        return "fc-local-test-123"

    monkeypatch.setattr(modal_provider, "submit", fake_submit)
    token = create_access_token(tenant_id="agency_mccann", user_id="usr_mccann_01", email="art_director@mccann.com")
    headers = {"Authorization": f"Bearer {token}"}
    sample_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGWaW9rAAAABJRU5ErkJggg=="

    response = client.post("/api/v1/analyze", headers=headers, json={
        "image_base64": sample_b64,
        "filename": "landing_page_v1.png",
        "requested_permutations": 18,
    })

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "ENQUEUED"
    assert data["tenant_id"] == "agency_mccann"
    assert submitted["job_id"] == data["job_id"]


def test_artifact_paths_are_sanitized_before_persistence():
    report = {
        "visual_artifacts": {
            "thermal_heatmap": "/tmp/tenant-a/job-1/heatmap.png",
            "report_pdf": "/tmp/tenant-a/job-1/report.pdf",
        },
        "report_exports": {"pdf": "/tmp/tenant-a/job-1/report.pdf"},
        "metrics": {"s_auc": 0.8},
    }
    artifact_ids = {
        "thermal_heatmap": "artifact_heatmap",
        "report_pdf": "artifact_pdf",
    }
    sanitized = _sanitize_report_artifacts(report, artifact_ids)
    envelope = _result_envelope({"job_id": "job-1", "tenant_id": "tenant-a"}, sanitized, artifact_ids)
    serialized = str(envelope)
    assert "/tmp/" not in serialized
    assert "artifact_heatmap" in serialized
    assert "artifact_pdf" in serialized
    assert envelope["canvas_overlay"] == {"thermal_heatmap": "artifact_heatmap", "report_pdf": "artifact_pdf"}
    assert envelope["report"]["report_exports"] == {"pdf": "artifact_pdf"}


def test_modal_worker_pipeline_execution():
    job_id = f"job_modal_e2e_{uuid.uuid4().hex[:10]}"
    session_id = f"sess_modal_e2e_{uuid.uuid4().hex[:10]}"
    appwrite_service.create_job_document(job_id, session_id, "agency_publicis", "usr_pub_01", "packaging_box.png", provider="modal")

    asset_path = Path(__file__).resolve().parents[1] / "input_assets" / "user_test_thumbnail.jpg"
    encoded_asset = base64.b64encode(asset_path.read_bytes()).decode("ascii")
    task = {
        "job_id": job_id,
        "session_id": session_id,
        "tenant_id": "agency_publicis",
        "user_id": "usr_pub_01",
        "image_base64": encoded_asset,
        "filename": asset_path.name,
    }

    payload = process_modal_job(task)

    assert payload["type"] == "FIGMA_NEUROMARKETING_DELIVERABLE_V1"
    assert "canvas_overlay" in payload
    assert "neuromarketing_metrics" in payload
    assert "domain_kpis" in payload["neuromarketing_metrics"]
    assert payload.get("artifact_file_ids")

    doc = appwrite_service.get_job_document(job_id)
    assert doc is not None
    assert doc["status"] == "COMPLETE"
    assert doc["stage"] == 6
    assert doc["progress_percent"] == 100
