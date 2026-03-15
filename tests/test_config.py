from __future__ import annotations

from wb_helper.config import Settings


def test_settings_use_database_url_as_postgres_dsn(monkeypatch) -> None:
    monkeypatch.setenv("BOT_TOKEN", "token")
    monkeypatch.delenv("POSTGRES_DSN", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/dbname")

    settings = Settings.from_env()

    assert settings.postgres_dsn == "postgresql+psycopg://user:pass@localhost:5432/dbname"


def test_settings_prefer_explicit_postgres_dsn(monkeypatch) -> None:
    monkeypatch.setenv("BOT_TOKEN", "token")
    monkeypatch.setenv("POSTGRES_DSN", "postgresql+psycopg://user:pass@localhost:5432/dbname")
    monkeypatch.setenv("DATABASE_URL", "postgresql://other:other@localhost:5432/other")

    settings = Settings.from_env()

    assert settings.postgres_dsn == "postgresql+psycopg://user:pass@localhost:5432/dbname"
