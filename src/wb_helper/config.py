from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import sys

from dotenv import load_dotenv


def _load_env_file() -> None:
    candidates = [
        Path.cwd() / ".env",
        Path(__file__).resolve().parents[2] / ".env",
    ]
    for candidate in candidates:
        if candidate.exists():
            load_dotenv(candidate, override=False)
            return


_load_env_file()


def _read_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Environment variable {name} is required")
    return value


def _read_postgres_dsn() -> str:
    value = os.getenv("POSTGRES_DSN") or os.getenv("DATABASE_URL")
    if not value:
        raise RuntimeError("Environment variable POSTGRES_DSN or DATABASE_URL is required")
    if value.startswith("postgresql://"):
        return value.replace("postgresql://", "postgresql+psycopg://", 1)
    return value


def _read_optional_env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


@dataclass(frozen=True, slots=True)
class Settings:
    bot_token: str
    webhook_base_url: str | None
    webhook_secret: str | None
    postgres_dsn: str
    redis_url: str
    ytdlp_bin: str
    request_timeout_seconds: int
    cache_ttl_days: int
    log_level: str
    auto_create_schema: bool
    webhook_path: str
    extractor_timeout_seconds: int
    job_timeout_seconds: int
    bind_host: str
    bind_port: int
    telegram_user_agent: str
    redis_queue_name: str
    wb_button_custom_emoji_id: str | None
    ozon_button_custom_emoji_id: str | None

    @property
    def webhook_url(self) -> str | None:
        if not self.webhook_base_url:
            return None
        return f"{self.webhook_base_url.rstrip('/')}{self.webhook_path}"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            bot_token=_require_env("BOT_TOKEN"),
            webhook_base_url=os.getenv("WEBHOOK_BASE_URL"),
            webhook_secret=os.getenv("WEBHOOK_SECRET"),
            postgres_dsn=_read_postgres_dsn(),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            ytdlp_bin=os.getenv("YTDLP_BIN", sys.executable),
            request_timeout_seconds=int(os.getenv("REQUEST_TIMEOUT_SECONDS", "8")),
            cache_ttl_days=int(os.getenv("CACHE_TTL_DAYS", "30")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            auto_create_schema=_read_bool("AUTO_CREATE_SCHEMA", True),
            webhook_path=os.getenv("WEBHOOK_PATH", "/telegram/webhook"),
            extractor_timeout_seconds=int(os.getenv("EXTRACTOR_TIMEOUT_SECONDS", "20")),
            job_timeout_seconds=int(os.getenv("JOB_TIMEOUT_SECONDS", "35")),
            bind_host=os.getenv("BIND_HOST", "0.0.0.0"),
            bind_port=int(os.getenv("BIND_PORT") or os.getenv("PORT", "8080")),
            telegram_user_agent=os.getenv(
                "TELEGRAM_USER_AGENT",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
            ),
            redis_queue_name=os.getenv("REDIS_QUEUE_NAME", "reels"),
            wb_button_custom_emoji_id=_read_optional_env("WB_BUTTON_CUSTOM_EMOJI_ID"),
            ozon_button_custom_emoji_id=_read_optional_env("OZON_BUTTON_CUSTOM_EMOJI_ID"),
        )
