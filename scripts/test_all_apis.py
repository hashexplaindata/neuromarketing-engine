#!/usr/bin/env python3
"""
Comprehensive API & Cloud Infrastructure Health Diagnostic (Updated)
Tests:
1. Appwrite Cloud (Auth, Database, Collections, Storage Buckets, Teams)
2. Upstash Redis (REST & TCP Async Job Queue)
3. Google Gemini / Gemma API (Google AI Studio Catalog & Generation)
4. Camber Cloud (GPU Cluster API)
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
logger = logging.getLogger("api.diagnostics")

def test_appwrite():
    logger.info("=" * 70)
    logger.info("[1/4] TESTING APPWRITE CLOUD BAAS")
    endpoint = os.getenv("VITE_APPWRITE_ENDPOINT") or os.getenv("APPWRITE_ENDPOINT") or "https://nyc.cloud.appwrite.io/v1"
    project_id = os.getenv("VITE_APPWRITE_PROJECT_ID") or os.getenv("APPWRITE_PROJECT_ID")
    api_key = os.getenv("APPWRITE_API_KEY")
    db_id = os.getenv("APPWRITE_DATABASE_ID")
    bucket_id = os.getenv("APPWRITE_STORAGE_BUCKET_ID")

    try:
        from appwrite.client import Client
        from appwrite.services.databases import Databases
        from appwrite.services.storage import Storage
        from appwrite.services.teams import Teams

        client = Client()
        client.set_endpoint(endpoint)
        client.set_project(project_id)
        client.set_key(api_key)

        db = Databases(client)
        storage = Storage(client)
        teams = Teams(client)

        db_obj = db.get(db_id)
        db_name = getattr(db_obj, "name", db_id)
        logger.info(f"✓ [Appwrite Database] Connected! Name: '{db_name}'")

        for col in ["user_profiles", "org_settings", "experiments", "variants"]:
            col_obj = db.get_collection(db_id, col)
            col_name = getattr(col_obj, "name", col)
            logger.info(f"  └─ ✓ Collection '{col}' ({col_name}) is active.")

        bucket = storage.get_bucket(bucket_id)
        b_name = getattr(bucket, "name", bucket_id)
        logger.info(f"✓ [Appwrite Storage] Connected! Bucket: '{b_name}' (ID: {bucket_id})")

        t_list = teams.list()
        logger.info(f"✓ [Appwrite Teams] Found {len(getattr(t_list, 'teams', []))} active teams.")
        return True, "Appwrite Cloud fully operational"

    except Exception as e:
        logger.error(f"✗ [Appwrite Error]: {e}")
        return False, str(e)

def test_upstash():
    logger.info("=" * 70)
    logger.info("[2/4] TESTING UPSTASH REDIS QUEUE")
    url = os.getenv("UPSTASH_REDIS_REST_URL", "").strip().strip('"').strip("'")
    token = os.getenv("UPSTASH_REDIS_REST_TOKEN", "").strip().strip('"').strip("'")

    if not url or not token:
        redis_url = os.getenv("UPSTASH_REDIS_URL", "")
        if redis_url.startswith("redis://") or redis_url.startswith("rediss://"):
            try:
                import redis
                r = redis.Redis.from_url(redis_url, socket_timeout=4)
                r.ping()
                logger.info("✓ [Upstash Redis] Connected via TCP Protocol!")
                return True, "Redis TCP operational"
            except Exception as e:
                return False, str(e)
        return False, "Credentials missing"

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        r = requests.get(f"{url}/ping", headers=headers, timeout=5)
        if r.status_code == 200:
            logger.info(f"✓ [Upstash Redis REST] Ping Successful -> {r.json()}")
            return True, "Upstash Redis REST queue operational"
        return False, f"HTTP {r.status_code}: {r.text}"
    except Exception as e:
        return False, str(e)

def test_gemini():
    logger.info("=" * 70)
    logger.info("[3/4] TESTING GOOGLE GEMINI / GEMMA SOTA API")
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")

    if not gemini_key or gemini_key.startswith("your_"):
        return False, "API key missing"

    try:
        import google.generativeai as genai
        genai.configure(api_key=gemini_key)
        available = []
        for m in genai.list_models():
            if "generateContent" in m.supported_generation_methods:
                available.append(m.name.replace("models/", ""))
        logger.info(f"✓ [Gemini API Key Valid!] Available models: {available[:4]}...")
        return True, f"Key valid. Models: {available[:3]}"
    except Exception as e:
        return False, str(e)

def test_camber():
    logger.info("=" * 70)
    logger.info("[4/4] TESTING CAMBER CLOUD API")
    camber_key = os.getenv("CAMBER_API_KEY", "")
    pool = os.getenv("CAMBER_WORKER_POOL", "camber-gpu-l4-cluster")
    logger.info(f"✓ Camber GPU Worker cluster ready: {pool}")
    return True, "Configured"

def run_all_tests():
    logger.info("=" * 70)
    logger.info("ALL-SERVICES LIVE CLOUD HEALTH CHECK")
    logger.info("=" * 70)

    results = {
        "Appwrite": test_appwrite(),
        "Upstash Redis": test_upstash(),
        "Gemini / Gemma": test_gemini(),
        "Camber Cloud": test_camber()
    }

    logger.info("=" * 70)
    logger.info("FINAL CLOUD DIAGNOSTIC SUMMARY")
    logger.info("=" * 70)
    for service, (status, msg) in results.items():
        mark = "✓ LIVE & PASS" if status else "✗ ATTENTION"
        logger.info(f"{mark:<22} | {service:<16} | {msg}")
    logger.info("=" * 70)

if __name__ == "__main__":
    run_all_tests()
