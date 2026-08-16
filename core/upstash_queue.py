"""Queue, progress, and short-lived job-state adapter.

Redis is used for dispatch/progress when configured. Durable job and result
records remain the responsibility of Appwrite or the production database. The
in-memory path exists only for local development and tests.
"""

from __future__ import annotations

import json
import logging
import threading
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.config import settings

logger = logging.getLogger("icm.upstash")

try:
    import redis
except ImportError:  # pragma: no cover - optional local dependency
    redis = None


class UpstashQueueService:
    def __init__(self):
        self.queue_name = settings.GPU_QUEUE_NAME
        self.redis_url = settings.UPSTASH_REDIS_URL
        self.rest_url = settings.UPSTASH_REDIS_REST_URL
        self.rest_token = settings.UPSTASH_REDIS_REST_TOKEN

        self._lock = threading.RLock()
        self._in_memory_queue: List[Dict[str, Any]] = []
        self._in_memory_state: Dict[str, Dict[str, Any]] = {}
        self._in_memory_idempotency: Dict[str, str] = {}

        self.r = None
        if redis and self.redis_url and not self.redis_url.startswith("redis://localhost"):
            try:
                ssl_params = {"ssl_cert_reqs": None} if self.redis_url.startswith("rediss://") else {}
                self.r = redis.from_url(self.redis_url, decode_responses=True, **ssl_params)
                self.r.ping()
                logger.info("Connected to Redis broker")
            except Exception as exc:  # pragma: no cover
                logger.warning("Redis connection failed; local queue fallback active: %s", exc)
                self.r = None

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _state_key(job_id: str) -> str:
        return f"job_state:{job_id}"

    @staticmethod
    def _idempotency_key(tenant_id: Optional[str], key: Optional[str]) -> Optional[str]:
        if not key:
            return None
        return f"{tenant_id or 'tenant_unknown'}:{key}"

    def _initial_state(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "job_id": job_data.get("job_id"),
            "tenant_id": job_data.get("tenant_id"),
            "status": "ENQUEUED",
            "stage": 0,
            "progress_percent": 0,
            "message": "Task enqueued for GPU processing",
            "timestamp": self._now(),
        }

    def push_gpu_job(self, job_data: Dict[str, Any]) -> str:
        """Enqueue one job and publish an initial state event.

        The caller owns durable job creation. This method is deliberately safe to
        call again with the same tenant-scoped idempotency key.
        """
        job_id = job_data.get("job_id")
        if not job_id:
            raise ValueError("job_data.job_id is required")

        idem_key = self._idempotency_key(job_data.get("tenant_id"), job_data.get("idempotency_key"))
        if idem_key:
            with self._lock:
                existing = self._in_memory_idempotency.get(idem_key)
            if existing:
                return existing
            if self.r:
                try:
                    existing = self.r.get(f"job_idempotency:{idem_key}")
                    if existing:
                        return existing
                except Exception:
                    pass

        serialized = json.dumps(job_data, default=str)
        state = self._initial_state(job_data)
        if self.r:
            try:
                self.r.rpush(self.queue_name, serialized)
                self.r.setex(self._state_key(job_id), 3600, json.dumps(state))
                if idem_key:
                    self.r.setex(f"job_idempotency:{idem_key}", 3600, job_id)
                return job_id
            except Exception as exc:  # pragma: no cover
                logger.error("Redis enqueue failed; local fallback active: %s", exc)

        with self._lock:
            self._in_memory_queue.append(deepcopy(job_data))
            self._in_memory_state[job_id] = deepcopy(state)
            if idem_key:
                self._in_memory_idempotency[idem_key] = job_id
        return job_id

    # Backward-compatible name for callers that use generic queue terminology.
    enqueue = push_gpu_job

    def pop_gpu_job(self, timeout: int = 2) -> Optional[Dict[str, Any]]:
        """Pop the next pending task for a worker."""
        if self.r:
            try:
                result = self.r.blpop(self.queue_name, timeout=timeout)
                if result:
                    _, job_str = result
                    return json.loads(job_str)
            except Exception as exc:  # pragma: no cover
                logger.error("Redis pop failed: %s", exc)
        with self._lock:
            return deepcopy(self._in_memory_queue.pop(0)) if self._in_memory_queue else None

    dequeue = pop_gpu_job

    def publish_progress(
        self,
        job_id: str,
        stage: int,
        progress: int,
        message: str,
        payload: Optional[Dict[str, Any]] = None,
        status: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        event_data = {
            "job_id": job_id,
            "tenant_id": tenant_id,
            "stage": stage,
            "progress_percent": max(0, min(100, progress)),
            "status": status or ("COMPLETE" if progress >= 100 else "RUNNING"),
            "message": message,
            "payload": payload,
            "timestamp": self._now(),
        }
        serialized = json.dumps(event_data, default=str)
        if self.r:
            try:
                self.r.publish(f"job_progress:{job_id}", serialized)
                self.r.setex(self._state_key(job_id), 3600, serialized)
                return event_data
            except Exception as exc:  # pragma: no cover
                logger.warning("Redis progress publish failed; local state fallback: %s", exc)
        with self._lock:
            self._in_memory_state[job_id] = deepcopy(event_data)
        return event_data

    def mark_failed(self, job_id: str, message: str, error: Optional[Dict[str, Any]] = None, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        return self.publish_progress(job_id, -1, 0, message, payload={"error": error or {}}, status="FAILED", tenant_id=tenant_id)

    def mark_complete(self, job_id: str, message: str = "Analysis completed", payload: Optional[Dict[str, Any]] = None, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        return self.publish_progress(job_id, 6, 100, message, payload=payload, status="COMPLETE", tenant_id=tenant_id)

    def get_job_state(self, job_id: str, tenant_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        if self.r:
            try:
                data = self.r.get(self._state_key(job_id))
                if data:
                    state = json.loads(data)
                    if tenant_id is None or state.get("tenant_id") == tenant_id:
                        return state
                    return None
            except Exception:  # pragma: no cover
                pass
        with self._lock:
            state = deepcopy(self._in_memory_state.get(job_id))
        if state and tenant_id is not None and state.get("tenant_id") != tenant_id:
            return None
        return state


upstash_queue = UpstashQueueService()
