"""Global configuration for the Neuromarketing Studio API and Modal worker."""

import os
from typing import List

try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseModel as BaseSettings


class Settings(BaseSettings):
    # App identity and Heroku runtime
    APP_NAME: str = "Neuromarketing Studio"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    PORT: int = int(os.getenv("PORT", "8000"))

    # Appwrite remains the durable tenant-scoped database and object store.
    APPWRITE_ENDPOINT: str = os.getenv("APPWRITE_ENDPOINT", "https://cloud.appwrite.io/v1")
    APPWRITE_PROJECT_ID: str = os.getenv("APPWRITE_PROJECT_ID", "neuromarketing-engine")
    APPWRITE_API_KEY: str = os.getenv("APPWRITE_API_KEY", "")
    APPWRITE_DATABASE_ID: str = os.getenv("APPWRITE_DATABASE_ID", "neuromarketing_db")
    APPWRITE_JOBS_COLLECTION_ID: str = os.getenv("APPWRITE_JOBS_COLLECTION_ID", "jobs")
    APPWRITE_STORAGE_BUCKET_ID: str = os.getenv("APPWRITE_STORAGE_BUCKET_ID", "assets")
    APPWRITE_PROVIDER_FIELDS_ENABLED: bool = os.getenv("APPWRITE_PROVIDER_FIELDS_ENABLED", "false").lower() == "true"
    S3_BUCKET: str = os.getenv("S3_BUCKET", "appwrite-storage")
    USE_S3_STORAGE: bool = False

    # Modal execution provider. MODAL_TOKEN_ID and MODAL_TOKEN_SECRET are read
    # directly by the Modal SDK and must be injected only into Heroku/CI secrets.
    GPU_PROVIDER: str = os.getenv("GPU_PROVIDER", "modal")
    MODAL_APP_NAME: str = os.getenv("MODAL_APP_NAME", "neuromarketing-studio")
    MODAL_FUNCTION_NAME: str = os.getenv("MODAL_FUNCTION_NAME", "process_job")
    MODAL_ENVIRONMENT: str = os.getenv("MODAL_ENVIRONMENT", "main")

    # Ephemeral filesystem isolation
    EPHEMERAL_ROOT: str = os.getenv(
        "EPHEMERAL_ROOT",
        "/tmp/neuromarketing" if os.name != "nt" else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ephemeral_workspaces"),
    )

    # Fallback JWT secret for development/testing; production must override it.
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "neuromarketing-studio-development-secret")

    # CORS is parsed by api.main from the deployment environment.
    CORS_ORIGINS: List[str] = ["*"]


settings = Settings()
