"""Modal deployment for Neuromarketing Studio GPU inference.

Deploy from the repository root with:

    modal deploy modal_app.py

The web API submits ``process_job`` asynchronously through
``core.modal_provider.ModalProvider``. The function persists the canonical
result envelope to Appwrite and returns it to Modal for reconciliation.
"""

from __future__ import annotations

from pathlib import Path

import modal


ROOT = Path(__file__).resolve().parent
APP_NAME = "neuromarketing-studio"
RUNTIME_SECRET = "custom-secrets-neuromarketing"

image = modal.Image.from_dockerfile(str(ROOT / "Dockerfile.worker"))
app = modal.App(APP_NAME)


@app.function(
    image=image,
    gpu="L4",
    timeout=30 * 60,
    retries=2,
    secrets=[modal.Secret.from_name(RUNTIME_SECRET)],
)
def process_job(task_payload: dict) -> dict:
    """Process one tenant-scoped analysis task on an L4 GPU."""
    from workers.modal_worker import process_modal_job

    return process_modal_job(task_payload)


@app.local_entrypoint()
def main():
    print(f"Modal app definition ready: {APP_NAME}.process_job")
