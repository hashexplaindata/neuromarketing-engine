"""
Global Configuration & Environment Settings
Heroku + Appwrite + Upstash Redis + Camber Cloud Stack
"""

import os
from typing import List, Optional
try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseModel as BaseSettings

class Settings(BaseSettings):
    # App Identity & Heroku Runtime
    APP_NAME: str = "Neuromarketing Studio"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # Appwrite BaaS (Auth, Database, Storage)
    APPWRITE_ENDPOINT: str = os.getenv("APPWRITE_ENDPOINT", "https://cloud.appwrite.io/v1")
    APPWRITE_PROJECT_ID: str = os.getenv("APPWRITE_PROJECT_ID", "neuromarketing-engine")
    APPWRITE_API_KEY: str = os.getenv("APPWRITE_API_KEY", "appwrite_mock_secret_api_key_2026")
    APPWRITE_DATABASE_ID: str = os.getenv("APPWRITE_DATABASE_ID", "neuromarketing_db")
    APPWRITE_JOBS_COLLECTION_ID: str = os.getenv("APPWRITE_JOBS_COLLECTION_ID", "jobs")
    APPWRITE_STORAGE_BUCKET_ID: str = os.getenv("APPWRITE_STORAGE_BUCKET_ID", "assets")
    S3_BUCKET: str = os.getenv("S3_BUCKET", "appwrite-storage")
    USE_S3_STORAGE: bool = False
    
    # Upstash Redis (Task Queue & Real-time Pub/Sub)
    UPSTASH_REDIS_URL: str = os.getenv("UPSTASH_REDIS_URL", os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    UPSTASH_REDIS_REST_URL: Optional[str] = os.getenv("UPSTASH_REDIS_REST_URL", None)
    UPSTASH_REDIS_REST_TOKEN: Optional[str] = os.getenv("UPSTASH_REDIS_REST_TOKEN", None)
    GPU_QUEUE_NAME: str = "queue:camber_gpu_jobs"
    
    # Camber Cloud (GPU Workers)
    CAMBER_WORKER_POOL: str = os.getenv("CAMBER_WORKER_POOL", "camber-gpu-t4-cluster")
    CAMBER_API_KEY: Optional[str] = os.getenv("CAMBER_API_KEY", None)
    
    # Ephemeral Filesystem Isolation
    EPHEMERAL_ROOT: str = os.getenv(
        "EPHEMERAL_ROOT", 
        "/tmp/neuromarketing" if os.name != "nt" else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ephemeral_workspaces")
    )
    
    # Fallback JWT Secret for development/testing
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "icm-appwrite-upstash-camber-secret-key-2026")
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]

settings = Settings()
