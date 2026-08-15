"""
Upstash Redis Async Queue & Pub/Sub Gateway
Dispatches tasks to Camber Cloud GPU workers and streams real-time progress events.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from core.config import settings

logger = logging.getLogger("icm.upstash")

try:
    import redis
except ImportError:
    redis = None

class UpstashQueueService:
    def __init__(self):
        self.queue_name = settings.GPU_QUEUE_NAME
        self.redis_url = settings.UPSTASH_REDIS_URL
        self.rest_url = settings.UPSTASH_REDIS_REST_URL
        self.rest_token = settings.UPSTASH_REDIS_REST_TOKEN
        
        self._in_memory_queue: List[Dict[str, Any]] = []
        self._in_memory_state: Dict[str, Dict[str, Any]] = []
        
        self.r = None
        if redis and self.redis_url:
            try:
                # Connect with SSL / TLS support for Upstash
                ssl_params = {}
                if self.redis_url.startswith("rediss://"):
                    ssl_params = {"ssl_cert_reqs": None}
                self.r = redis.from_url(self.redis_url, decode_responses=True, **ssl_params)
                self.r.ping()
                logger.info(f"Connected to Upstash Redis broker at {self.redis_url.split('@')[-1] if '@' in self.redis_url else 'localhost'}")
            except Exception as e:
                logger.warning(f"Upstash Redis connection note: {e}. Active with in-memory task bus.")
                self.r = None

    def push_gpu_job(self, job_data: Dict[str, Any]) -> str:
        """
        Pushes task payload to Upstash Redis queue for Camber Cloud workers.
        Returns immediately (< 5ms) to prevent HTTP gateway timeouts.
        """
        job_id = job_data.get("job_id")
        serialized = json.dumps(job_data)
        
        if self.r:
            try:
                # RPUSH to Camber GPU queue
                self.r.rpush(self.queue_name, serialized)
                # Store initial state
                initial_event = {
                    "job_id": job_id,
                    "stage": 0,
                    "progress_percent": 0,
                    "status": "ENQUEUED",
                    "message": "Task enqueued to Upstash Redis for Camber Cloud GPU workers"
                }
                self.r.setex(f"job_state:{job_id}", 3600, json.dumps(initial_event))
                logger.info(f"Enqueued job {job_id} to Upstash Redis queue '{self.queue_name}'")
                return job_id
            except Exception as e:
                logger.error(f"Upstash Redis rpush error: {e}")
                
        self._in_memory_queue.append(job_data)
        logger.info(f"Enqueued job {job_id} to local memory queue")
        return job_id

    def pop_gpu_job(self, timeout: int = 2) -> Optional[Dict[str, Any]]:
        """Used by Camber Cloud GPU worker to pull the next pending task."""
        if self.r:
            try:
                # BLPOP blocking pop from queue
                result = self.r.blpop(self.queue_name, timeout=timeout)
                if result:
                    _, job_str = result
                    return json.loads(job_str)
            except Exception as e:
                logger.error(f"Upstash Redis pop error: {e}")
                
        if self._in_memory_queue:
            return self._in_memory_queue.pop(0)
        return None

    def publish_progress(self, job_id: str, stage: int, progress: int, message: str, payload: Optional[Dict[str, Any]] = None):
        """
        Broadcasts real-time step progress to Upstash Redis channel 'job_progress:{job_id}'.
        Delivered live to the Figma plugin via WebSocket.
        """
        event_data = {
            "job_id": job_id,
            "stage": stage,
            "progress_percent": progress,
            "message": message,
            "payload": payload
        }
        serialized = json.dumps(event_data)
        
        if self.r:
            try:
                self.r.publish(f"job_progress:{job_id}", serialized)
                self.r.setex(f"job_state:{job_id}", 3600, serialized)
                logger.info(f"Upstash Pub/Sub [Job {job_id}]: Stage {stage} ({progress}%) - {message}")
                return
            except Exception as e:
                logger.warning(f"Upstash progress publish error: {e}")
                
        logger.info(f"Local Progress [Job {job_id}]: Stage {stage} ({progress}%) - {message}")

    def get_job_state(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves latest cached job state."""
        if self.r:
            try:
                data = self.r.get(f"job_state:{job_id}")
                if data:
                    return json.loads(data)
            except Exception:
                pass
        return None

upstash_queue = UpstashQueueService()
