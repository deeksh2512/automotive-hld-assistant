"""Central configuration loaded from environment / .env."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_provider: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b-instruct"
    llm_temperature: float = 0.1
    llm_timeout_seconds: int = 180

    embedding_model: str = "BAAI/bge-small-en-v1.5"

    data_dir: Path = PROJECT_ROOT / "data"
    vectorstore_dir: Path = PROJECT_ROOT / "data" / "vectorstore"
    upload_dir: Path = PROJECT_ROOT / "data" / "uploads"
    database_url: str = f"sqlite:///{(PROJECT_ROOT / 'data' / 'platform.db').as_posix()}"

    retrieval_top_k: int = 6
    chunk_target_chars: int = 1200
    chunk_overlap_chars: int = 150

    api_host: str = "127.0.0.1"
    api_port: int = 8000
    api_base_url: str = "http://127.0.0.1:8000"

    enable_ocr: bool = True
    tesseract_cmd: str = ""

    default_user: str = "engineer@local"
    default_role: str = "engineer"

    def ensure_directories(self) -> None:
        for path in (self.data_dir, self.vectorstore_dir, self.upload_dir):
            Path(path).mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings


settings = get_settings()
