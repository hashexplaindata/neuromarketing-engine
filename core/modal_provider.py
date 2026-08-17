"""Modal execution adapter for Neuromarketing Studio.

The Heroku API uses this adapter only to submit and inspect a remote call. The
Modal function itself executes ``workers.modal_worker.process_modal_job`` and
persists the canonical result envelope to Appwrite. Appwrite remains the
business system of record; Modal call IDs are execution references only.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Any, Dict, Optional
from uuid import uuid4

from core.appwrite_service import appwrite_service
from core.config import settings

logger = logging.getLogger("icm.modal_provider")


@dataclass(frozen=True)
class ModalCallState:
    provider: str
    provider_job_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ModalProvider:
    """Small lazy-import adapter so the web process stays testable offline."""

    provider_name = "modal"

    def _function(self):
        try:
            import modal
        except ImportError as exc:  # pragma: no cover - dependency is deployed remotely
            raise RuntimeError("Modal SDK is not installed") from exc
        return modal.Function.from_name(
            settings.MODAL_APP_NAME,
            settings.MODAL_FUNCTION_NAME,
        )

    def _run_local(self, task_payload: Dict[str, Any]) -> None:
        """Run the real worker in-process for an explicit local-demo environment."""
        try:
            from workers.modal_worker import process_modal_job
            process_modal_job(task_payload)
        except Exception as exc:  # pragma: no cover - exercised by local integration runs
            logger.exception("Local demo worker failed for %s", task_payload.get("job_id"))
            appwrite_service.update_job_status(
                task_payload.get("job_id", ""),
                "FAILED",
                stage=0,
                progress=0,
                tenant_id=task_payload.get("tenant_id"),
                error_json={"code": "LOCAL_WORKER_FAILED", "message": str(exc)[:500], "retryable": False},
                message="Local demo worker failed",
            )

    def submit(self, task_payload: Dict[str, Any]) -> str:
        try:
            call = self._function().spawn(task_payload)
            return str(call.object_id)
        except RuntimeError:
            if settings.DEBUG or settings.ENVIRONMENT == "test":
                provider_job_id = f"local-modal-{uuid4().hex}"
                # Delay slightly so the API can persist ENQUEUED before the worker
                # writes RUNNING/COMPLETE to the same in-memory or Appwrite record.
                threading.Timer(0.25, self._run_local, args=(task_payload,)).start()
                return provider_job_id
            raise

    def get_state(self, provider_job_id: str, timeout: float = 0) -> ModalCallState:
        try:
            import modal

            call = modal.FunctionCall.from_id(provider_job_id)
            result = call.get(timeout=timeout)
            return ModalCallState(
                provider=self.provider_name,
                provider_job_id=provider_job_id,
                status="COMPLETE",
                result=result if isinstance(result, dict) else {"value": result},
            )
        except TimeoutError:
            return ModalCallState(
                provider=self.provider_name,
                provider_job_id=provider_job_id,
                status="RUNNING",
            )
        except Exception as exc:
            try:
                import modal

                if isinstance(exc, modal.exception.OutputExpiredError):
                    status = "EXPIRED"
                else:
                    status = "FAILED"
            except Exception:  # pragma: no cover - defensive import path
                status = "FAILED"
            return ModalCallState(
                provider=self.provider_name,
                provider_job_id=provider_job_id,
                status=status,
                error=str(exc)[:500],
            )


modal_provider = ModalProvider()
