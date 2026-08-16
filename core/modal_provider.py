"""Modal execution adapter for Neuromarketing Studio.

The Heroku API uses this adapter only to submit and inspect a remote call. The
Modal function itself executes ``workers.modal_worker.process_modal_job`` and
persists the canonical result envelope to Appwrite. Appwrite remains the
business system of record; Modal call IDs are execution references only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
from uuid import uuid4

from core.config import settings


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

    def submit(self, task_payload: Dict[str, Any]) -> str:
        try:
            call = self._function().spawn(task_payload)
            return str(call.object_id)
        except RuntimeError:
            if settings.DEBUG or settings.ENVIRONMENT == "test":
                return f"local-modal-{uuid4().hex}"
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
