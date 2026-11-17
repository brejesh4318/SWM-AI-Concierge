import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_async_url_swaps_scheme():
    s = Settings(DATABASE_URL="postgresql://u:p@h/db")
    assert s.async_url == "postgresql+asyncpg://u:p@h/db"


def test_sync_url_plain_and_ssl():
    assert (
        Settings(DATABASE_URL="postgresql://u@h/db", DB_SSL=False).sync_url
        == "postgresql+psycopg2://u@h/db"
    )
    assert Settings(
        DATABASE_URL="postgresql://u@h/db", DB_SSL=True
    ).sync_url.endswith("?sslmode=require")


def test_missing_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)
