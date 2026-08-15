"""
Celery Application Instance & Redis Progress Event Streamer
ICM Neuromarketing Async Task Queue
"""

import json
import logging
from typing import Dict, Any, Optional
from celery import Celery
from core.config import settings

logger = logging.getLogger("icm.celery")

celery_app = Celery(
    "neuromarketing_engine",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["tasks.pipeline_tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300, # 5 min max GPU run
    task_soft_time_limit=240,
    worker_prefetch_multiplier=1, # Strict 1-task per GPU worker concurrency
    worker_max_tasks_per_child=50 # Prevent CUDA memory fragmentation
)

def publish_job_progress(job_id: str, stage: int, progress: int, message: str, payload: Optional[Dict[str, Any]] = None):
    """
    Publishes real-time pipeline progression to Redis Pub/Sub channel 'job_progress:{job_id}'.
    Consumed by the FastAPI WebSocket gateway to stream updates to Figma plugin.
    """
    try:
        import redis
        r = redis.from_url(settings.REDIS_URL)
        event_data = {
            "job_id": job_id,
            "stage": stage,
            "progress_percent": progress,
            "message": message,
            "payload": payload
        }
        r.publish(f"job_progress:{job_id}", json.dumps(event_data))
        # Also store latest state in Redis cache with 1h TTL
        r.setex(f"job_state:{job_id}", 3600, json.dumps(event_data))
        logger.info(f"Broadcast progress for job {job_id}: Stage {stage} ({progress}%) - {message}")
    except Exception as e:
        logger.warning(f"Failed to publish progress to Redis for job {job_id}: {e}")
