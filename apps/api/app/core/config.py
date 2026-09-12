from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CareerOS Intelligence API"
    app_version: str = "0.1.0"
    app_env: Literal["development", "production", "test"] = "development"
    demo_mode: bool = True

    # Supabase (Single Canonical Storage)
    supabase_url: str = Field(
        default="https://mock-project.supabase.co", alias="NEXT_PUBLIC_SUPABASE_URL"
    )
    supabase_anon_key: str = Field(default="mock-anon-key", alias="NEXT_PUBLIC_SUPABASE_ANON_KEY")
    supabase_service_role_key: str = Field(default="", alias="SUPABASE_SERVICE_ROLE_KEY")

    # AI & Embedding
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    fal_key: str = Field(default="", alias="FAL_KEY")
    fal_image_model: str = Field(default="fal-ai/flux/dev", alias="FAL_IMAGE_MODEL")
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_embedding_model: str = Field(default="nomic-embed-text", alias="OLLAMA_EMBEDDING_MODEL")
    embedding_dimensions: int = Field(default=768, alias="EMBEDDING_DIMENSIONS")
    embedding_timeout_seconds: float = Field(default=30.0, alias="EMBEDDING_TIMEOUT_SECONDS")
    embedding_batch_size: int = Field(default=16, alias="EMBEDDING_BATCH_SIZE")
    embedding_chunk_size: int = Field(default=512, alias="EMBEDDING_CHUNK_SIZE")
    embedding_chunk_overlap: int = Field(default=64, alias="EMBEDDING_CHUNK_OVERLAP")

    # Security
    max_resume_file_size: int = 5 * 1024 * 1024  # 5 MB
    cron_secret: str = Field(default="", alias="CRON_SECRET")

    # Job Ingestion (Phase 6)
    job_provider_timeout_seconds: float = Field(default=20.0, alias="JOB_PROVIDER_TIMEOUT_SECONDS")
    job_provider_max_pages: int = Field(default=5, alias="JOB_PROVIDER_MAX_PAGES")
    job_provider_max_jobs_per_run: int = Field(default=100, alias="JOB_PROVIDER_MAX_JOBS_PER_RUN")
    job_provider_batch_size: int = Field(default=20, alias="JOB_PROVIDER_BATCH_SIZE")
    job_url_fetch_timeout_seconds: float = Field(default=15.0, alias="JOB_URL_FETCH_TIMEOUT_SECONDS")
    job_url_max_response_bytes: int = Field(default=2_000_000, alias="JOB_URL_MAX_RESPONSE_BYTES")

    # Trust & Safety (Phase 7)
    open_corporates_api_key: str = Field(default="", alias="OPEN_CORPORATES_API_KEY")
    urlscan_api_key: str = Field(default="", alias="URLSCAN_API_KEY")
    trust_assessment_ttl_hours: int = Field(default=72, alias="TRUST_ASSESSMENT_TTL_HOURS")
    trust_timeout_seconds: float = Field(default=15.0, alias="TRUST_TIMEOUT_SECONDS")

    model_config = SettingsConfigDict(
        env_file=(".env.local", ".env", "../../.env.local", "../../.env"), env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
