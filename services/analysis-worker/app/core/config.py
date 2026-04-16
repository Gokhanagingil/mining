from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    app_name: str = "Analysis Worker"
    debug: bool = False

    # Storage
    storage_path: str = "/data/storage"
    parquet_path: str = "/data/parquet"
    artifacts_path: str = "/data/artifacts"

    # Database
    database_url: str = "postgresql://mining:mining@postgres:5432/mining"

    # LLM
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    use_mock_llm: bool = False

    # Worker
    max_file_size_mb: int = 500
    chunk_size_rows: int = 50000
    sample_size_rows: int = 10000

    class Config:
        env_file = ".env"
        env_prefix = "WORKER_"


settings = Settings()

# Ensure directories exist
for path in [settings.storage_path, settings.parquet_path, settings.artifacts_path]:
    Path(path).mkdir(parents=True, exist_ok=True)
