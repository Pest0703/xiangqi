from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_prefix="XIANGQI_",
        extra="ignore",
    )

    database_path: Path = PROJECT_ROOT / "data" / "xiangqi_tutor.sqlite3"
    log_dir: Path = PROJECT_ROOT / "logs"
    pikafish_path: Path | None = None
    pikafish_nnue_path: Path | None = None
    engine_threads: int = Field(default=4, ge=1)
    engine_hash_mb: int = Field(default=256, ge=16)
    engine_multipv: int = Field(default=3, ge=1, le=10)
    engine_depth: int = Field(default=16, ge=1)
    engine_movetime_ms: int = Field(default=1500, ge=100)
    engine_timeout_seconds: float = Field(default=20, gt=0)
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = ""
    llm_temperature: float = Field(default=0.2, ge=0, le=2)
    llm_max_tokens: int = Field(default=1200, ge=1)
    llm_timeout_seconds: float = Field(default=30, gt=0)
