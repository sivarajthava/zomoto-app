"""Application configuration and environment settings."""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API Keys & LLM Configuration
    groq_api_key: str = ""
    gemini_api_key: str = ""
    default_llm_model: str = "openai/gpt-oss-120b"
    request_timeout_seconds: float = 4.0

    # Environment & Server
    environment: str = "development"
    app_host: str = "127.0.0.1"
    app_port: int = 8000

    # Data Ingestion & Storage
    base_dir: Path = Path(__file__).resolve().parent.parent
    data_path: str = "data/processed/zomato_clean.parquet"
    raw_data_path: str = "data/raw/zomato_raw.parquet"

    # Stage 1 Retrieval Parameters
    max_candidates_stage_1: int = 15
    min_candidates_threshold: int = 5

    @property
    def absolute_data_path(self) -> Path:
        """Resolve data_path to an absolute filesystem Path."""
        p = Path(self.data_path)
        if not p.is_absolute():
            return self.base_dir / p
        return p


settings = Settings()
