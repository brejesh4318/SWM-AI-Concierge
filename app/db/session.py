from collections.abc import AsyncGenerator
from uuid import uuid4

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

settings = get_settings()

connect_args: dict = {"ssl": "require"} if settings.DB_SSL else {}

# Supabase's transaction pooler (port 6543, pgbouncer) does not support
# prepared statements, so turn off asyncpg's caches and use unique names.
if ":6543" in settings.DATABASE_URL:
    connect_args.update(
        statement_cache_size=0,
        prepared_statement_cache_size=0,
        prepared_statement_name_func=lambda: f"__asyncpg_{uuid4()}__",
    )

engine = create_async_engine(
    settings.async_url,
    pool_pre_ping=False,
    pool_size=5,
    max_overflow=10,
    pool_recycle=1800,
    connect_args=connect_args,
)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a database session for the duration of one request.

    Intended for use as a FastAPI dependency. The session is closed
    automatically when the request finishes.

    Yields:
        An AsyncSession bound to the application's engine.
    """
    async with SessionLocal() as session:
        yield session
