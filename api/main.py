"""
FastAPI Application Entrypoint
ICM Neuromarketing Production Gateway
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router as api_router
from api.websocket import ws_router
from core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("icm.gateway")

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Multi-Tenant Ephemeral ICM Attention Platform Backend with Celery GPU Execution"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Attach routes
app.include_router(api_router, prefix=settings.API_V1_STR, tags=["Neuromarketing Inference"])
app.include_router(ws_router, tags=["Real-time WebSockets"])

@app.get("/health", tags=["Monitoring"])
async def health_check():
    return {
        "status": "HEALTHY",
        "service": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
        "version": "1.0.0",
        "ephemeral_root": settings.EPHEMERAL_ROOT
    }

@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "Welcome to the Interpretable Context Methodology (ICM) Neuromarketing Engine",
        "docs": "/docs",
        "health": "/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
