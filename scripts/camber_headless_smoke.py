"""Run one bounded, secret-free Neuromarketing Studio worker smoke test.

This script is intended for a private Camber Job. It uses the real worker
pipeline with the local Appwrite fallback, so it verifies GPU/runtime/model
execution and the canonical result envelope without requiring client data,
Upstash credentials, Appwrite credentials, or Gemini credits.
"""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path

from core.appwrite_service import AppwriteService
from workers.camber_worker import process_camber_gpu_job


ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = ROOT / "input_assets" / "user_test_thumbnail.jpg"
OUTPUT_PATH = Path(os.environ.get("CAMBER_SMOKE_OUTPUT", "/tmp/camber_smoke_result.json"))


def main() -> int:
    if not INPUT_PATH.is_file():
        raise FileNotFoundError(f"Smoke asset not found: {INPUT_PATH}")

    encoded = base64.b64encode(INPUT_PATH.read_bytes()).decode("ascii")
    task = {
        "job_id": "camber_smoke_local_job",
        "analysis_id": "camber_smoke_analysis",
        "session_id": "camber_smoke_session",
        "tenant_id": "camber_smoke_tenant",
        "user_id": "camber_smoke_user",
        "project_id": "camber_smoke_project",
        "filename": INPUT_PATH.name,
        "mode": "PREDICTIVE",
        "image_base64": f"data:image/jpeg;base64,{encoded}",
    }

    result = process_camber_gpu_job(task, service=AppwriteService())
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")

    print("NEUROMARKETING_STUDIO_CAMBER_SMOKE_OK")
    print(json.dumps({
        "job_id": result.get("job_id"),
        "analysis_id": result.get("analysis_id"),
        "status": result.get("status"),
        "schema_version": result.get("schema_version"),
        "output": str(OUTPUT_PATH),
        "artifact_count": len(result.get("artifact_file_ids", {})),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
