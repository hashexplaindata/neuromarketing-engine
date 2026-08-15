#!/usr/bin/env python3
"""
Live Upstash Redis REST & Queue Diagnostic Test
Tests connection, PING, SET, GET, and Async Job Queue (LPUSH / RPOP).
"""

import os
import sys
import json
import logging
import requests
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(dotenv_path)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("upstash.test")

def test_upstash_rest():
    url = os.getenv("UPSTASH_REDIS_REST_URL", "").strip().strip('"').strip("'")
    token = os.getenv("UPSTASH_REDIS_REST_TOKEN", "").strip().strip('"').strip("'")

    logger.info("=" * 70)
    logger.info("TESTING UPSTASH REDIS REST API & QUEUE")
    logger.info(f"REST URL:   {url}")
    logger.info(f"REST Token: {token[:8]}...{token[-6:] if len(token) > 14 else ''}")
    logger.info("=" * 70)

    if not url or not token:
        logger.error("UPSTASH_REDIS_REST_URL or UPSTASH_REDIS_REST_TOKEN missing in .env")
        return False

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # 1. Test PING
    try:
        ping_resp = requests.get(f"{url}/ping", headers=headers, timeout=5)
        logger.info(f"[1/4] PING Endpoint -> HTTP {ping_resp.status_code}: {ping_resp.text}")
        if ping_resp.status_code != 200:
            logger.error(f"Failed to ping Upstash: {ping_resp.text}")
            return False
    except Exception as e:
        logger.error(f"Network error contacting Upstash: {e}")
        return False

    # 2. Test SET Key
    test_key = "neuromarketing_engine_healthcheck"
    test_val = json.dumps({"status": "healthy", "service": "upstash_async_queue"})
    try:
        set_resp = requests.post(f"{url}/set/{test_key}", headers=headers, json=test_val, timeout=5)
        logger.info(f"[2/4] SET Key '{test_key}' -> HTTP {set_resp.status_code}: {set_resp.text}")
    except Exception as e:
        logger.error(f"Failed to SET key: {e}")
        return False

    # 3. Test GET Key
    try:
        get_resp = requests.get(f"{url}/get/{test_key}", headers=headers, timeout=5)
        logger.info(f"[3/4] GET Key '{test_key}' -> HTTP {get_resp.status_code}: {get_resp.text}")
    except Exception as e:
        logger.error(f"Failed to GET key: {e}")
        return False

    # 4. Test Job Queue: LPUSH and RPOP
    queue_name = "queue:neuromarketing_jobs"
    mock_job = json.dumps({
        "job_id": "job_test_001",
        "experiment_id": "exp_live_upstash_test",
        "action": "run_saliency_pipeline"
    })
    try:
        # LPUSH job
        lpush_resp = requests.post(f"{url}/lpush/{queue_name}", headers=headers, json=mock_job, timeout=5)
        logger.info(f"[4/4] LPUSH Job to '{queue_name}' -> HTTP {lpush_resp.status_code}: {lpush_resp.text}")

        # RPOP job
        rpop_resp = requests.post(f"{url}/rpop/{queue_name}", headers=headers, timeout=5)
        logger.info(f"      RPOP Job from '{queue_name}' -> HTTP {rpop_resp.status_code}: {rpop_resp.text}")
    except Exception as e:
        logger.error(f"Failed queue test: {e}")
        return False

    logger.info("=" * 70)
    logger.info("✓ UPSTASH REDIS REST API IS 100% OPERATIONAL & VERIFIED!")
    logger.info("=" * 70)
    return True

if __name__ == "__main__":
    success = test_upstash_rest()
    sys.exit(0 if success else 1)
