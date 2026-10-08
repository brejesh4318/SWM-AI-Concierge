from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.async_url,
    pool_pre_ping=True,
    connect_args={"ssl": "require"} if settings.DB_SSL else {},
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
