"""FastAPI gateway for BIA Signal Studio.

The public API exposes the canonical authenticated analysis and job-status
routes. Heavy inference is delegated to the worker path; the gateway does not
write user uploads to its local filesystem or expose a shared report file.
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router as canonical_router

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

app = FastAPI(
    title="BIA Signal Studio API",
    description="Tenant-scoped creative diagnostics gateway for predictive visual-attention analysis.",
    version="5.0.0",
)

cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Idempotency-Key"],
)

app.include_router(canonical_router, prefix="/api/v1")


@app.get("/health")
def health_check():
    return {
        "status": "HEALTHY",
        "architecture": "Tenant-authenticated API + Appwrite Storage + Upstash Redis + worker inference",
        "version": "5.0.0",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
