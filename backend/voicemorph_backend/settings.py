"""Backend settings (environment-driven via pydantic-settings)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VOICEMORPH_", env_file=".env", extra="ignore")

    # --- API ---
    api_key: str = "change-me"          # simple shared-secret auth for personal servers
    cors_origins: list[str] = ["*"]

    # --- Engine ---
    # "passthrough" (default here) is CPU-safe for dev/CI; set to "rvc" in
    # production GPU workers.
    engine_backend: str = "passthrough"
    device: str = "auto"
    sample_rate: int = 40_000

    # --- Job execution ---
    # eager = run jobs in-process synchronously (dev/tests, no broker needed).
    # celery = dispatch to Celery workers via redis broker (production).
    job_mode: str = "eager"
    redis_url: str = "redis://localhost:6379/0"

    # --- Storage ---
    # "local" = filesystem under storage_root; "s3" = S3/MinIO via boto3.
    storage_backend: str = "local"
    storage_root: Path = Path("./.voicemorph-data")
    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "voicemorph"
    s3_region: str = "us-east-1"

    # --- Limits ---
    max_upload_mb: int = 512


@lru_cache
def get_settings() -> Settings:
    return Settings()
