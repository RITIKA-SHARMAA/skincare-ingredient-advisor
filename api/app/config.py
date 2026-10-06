from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://skincare:skincare@localhost:5432/skincare"
    api_base_url: str = "http://localhost:8000"
    llm_provider: str = "fake"
    google_cloud_project: str | None = None
    google_cloud_location: str = "global"
    vertex_model: str = "gemini-2.5-flash"
    storage_bucket: str = "local-labels"
    storage_root: str = "./storage"
    max_ingredients_per_request: int = 100
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
