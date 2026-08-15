#!/usr/bin/env python3
"""
Camber Cloud GPU Worker Daemon
Listens to Upstash Redis `queue:analysis_jobs` via REST / Polling.
Streams raw image/video assets directly from Appwrite Storage (bypassing API gateways).
Executes Multi-Tier Saliency, Biometrics, and CTR forecasting with VRAMManager memory flushing.
"""

import os
import sys
import time
import json
import logging

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

import requests
from core.vram_manager import VRAMManager
from core.appwrite_service import AppwriteService
from scripts.run_full_pipeline import run_full_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [camber_worker] %(message)s"
)
logger = logging.getLogger("camber_worker")


class CamberWorkerDaemon:
    def __init__(self):
        self.redis_url = os.getenv("UPSTASH_REDIS_REST_URL", "").strip().strip('"')
        self.redis_token = os.getenv("UPSTASH_REDIS_REST_TOKEN", "").strip().strip('"')
        self.appwrite = AppwriteService()
        self.running = True

        if not self.redis_url or not self.redis_token:
            logger.warning("Upstash Redis credentials not configured. Worker running in idle standby mode.")

    def pop_job(self):
        """Pops a job payload from Upstash Redis `queue:analysis_jobs`."""
        if not self.redis_url or not self.redis_token:
            return None
        try:
            headers = {"Authorization": f"Bearer {self.redis_token}"}
            resp = requests.post(f"{self.redis_url}/rpop/queue:analysis_jobs", headers=headers, timeout=5)
            if resp.status_code == 200:
                result = resp.json().get("result")
                if result:
                    return json.loads(result)
            return None
        except Exception as e:
            logger.warning(f"Redis poll note: {e}")
            return None

    def process_job(self, job_data: dict):
        """Processes a single analysis job."""
        job_id = job_data.get("job_id", "unknown")
        experiment_id = job_data.get("experiment_id", f"exp_{int(time.time())}")
        file_id = job_data.get("file_id")
        
        logger.info(f"Processing Job '{job_id}' (Experiment '{experiment_id}') ...")

        temp_dir = os.path.join(PROJECT_ROOT, "input_assets")
        os.makedirs(temp_dir, exist_ok=True)
        local_asset_path = os.path.join(temp_dir, f"{file_id or job_id}.jpg")

        # Direct Appwrite Download
        if file_id:
            download_ok = self.appwrite.download_file_to_path(file_id, local_asset_path)
            if not download_ok:
                logger.error(f"Failed downloading asset '{file_id}' from Appwrite Storage.")
                return

        with VRAMManager.vram_stage("camber_full_execution"):
            report = run_full_pipeline(local_asset_path)
            logger.info(f"Job '{job_id}' completed with Predicted CTR: {report.get('ctr_forecast', {}).get('predicted_ctr_pct')}%")

    def run(self, max_iterations: int = 1):
        """Main polling loop."""
        logger.info("Camber Worker Daemon started. Polling Redis queue ...")
        count = 0
        while self.running and count < max_iterations:
            job = self.pop_job()
            if job:
                self.process_job(job)
            else:
                time.sleep(2)
            count += 1


if __name__ == "__main__":
    daemon = CamberWorkerDaemon()
    daemon.run(max_iterations=1)