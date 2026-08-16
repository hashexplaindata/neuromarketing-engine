"""Neuromarketing Studio cloud configuration diagnostic.

This script is intentionally non-destructive. It checks configuration presence
and Appwrite connectivity; it does not submit a GPU job or mutate provider data.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("neuromarketing.diagnostics")


def check_appwrite() -> tuple[bool, str]:
    endpoint = os.getenv("APPWRITE_ENDPOINT", "")
    project_id = os.getenv("APPWRITE_PROJECT_ID", "")
    api_key = os.getenv("APPWRITE_API_KEY", "")
    if not endpoint or not project_id or not api_key:
        return False, "APPWRITE_ENDPOINT, APPWRITE_PROJECT_ID, or APPWRITE_API_KEY missing"
    try:
        from appwrite.client import Client
        from appwrite.services.storage import Storage

        client = Client().set_endpoint(endpoint).set_project(project_id).set_key(api_key)
        Storage(client).get_bucket(os.getenv("APPWRITE_STORAGE_BUCKET_ID", "assets"))
        return True, "Appwrite Storage reachable"
    except Exception as exc:
        return False, str(exc)[:300]


def check_modal_config() -> tuple[bool, str]:
    token_id = os.getenv("MODAL_TOKEN_ID", "")
    token_secret = os.getenv("MODAL_TOKEN_SECRET", "")
    app_name = os.getenv("MODAL_APP_NAME", "neuromarketing-studio")
    function_name = os.getenv("MODAL_FUNCTION_NAME", "process_job")
    if not token_id or not token_secret:
        return False, "MODAL_TOKEN_ID or MODAL_TOKEN_SECRET missing"
    return True, f"Modal credentials configured for {app_name}.{function_name}"


def check_gemini_config() -> tuple[bool, str]:
    key = os.getenv("GEMINI_API_KEY", "")
    return (bool(key), "Gemini key configured" if key else "GEMINI_API_KEY missing")


def run_all_tests() -> None:
    results = {
        "Appwrite": check_appwrite(),
        "Modal": check_modal_config(),
        "Gemini": check_gemini_config(),
    }
    for name, (ok, message) in results.items():
        logger.info("%s | %s | %s", "PASS" if ok else "ATTENTION", name, message)


if __name__ == "__main__":
    run_all_tests()
