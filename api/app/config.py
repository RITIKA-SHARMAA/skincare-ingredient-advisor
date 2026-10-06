from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://skincare:skincare@localhost:5432/skincare"
    cors_origins: str = "http://localhost:3000"

    # "rules" uses the deterministic catalogue explainer; "vertex" calls Gemini on Vertex AI.
    llm_provider: Literal["rules", "vertex"] = "rules"
    google_cloud_project: str | None = None
    google_cloud_location: str = "global"
    vertex_model: str = "gemini-2.5-flash"
    llm_timeout_seconds: float = 20.0

    # "local" keeps label images on disk; "gcs" issues signed Cloud Storage upload URLs.
    storage_backend: Literal["local", "gcs"] = "local"
    storage_bucket: str = "local-labels"
    storage_root: str = "./storage"
    public_api_base_url: str = "http://localhost:8000"
    signed_url_minutes: int = 10

    max_ingredients_per_request: int = 100
    max_label_bytes: int = 5 * 1024 * 1024

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
