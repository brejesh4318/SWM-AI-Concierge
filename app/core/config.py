from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str
    DB_SSL: bool = False

    @property
    def async_url(self) -> str:
        """Build the database URL used by the async SQLAlchemy engine.

        Returns:
            The configured DATABASE_URL with its ``postgresql://`` scheme
            swapped for ``postgresql+asyncpg://``.
        """
        return self.DATABASE_URL.replace(
            "postgresql://", "postgresql+asyncpg://", 1
        )

    @property
    def sync_url(self) -> str:
        """Build the database URL used by synchronous tools such as Alembic.

        Returns:
            The configured DATABASE_URL with its ``postgresql://`` scheme
            swapped for ``postgresql+psycopg2://``, plus
            ``?sslmode=require`` when DB_SSL is enabled.
        """
        url = self.DATABASE_URL.replace(
            "postgresql://", "postgresql+psycopg2://", 1
        )
        return url + ("?sslmode=require" if self.DB_SSL else "")


@lru_cache
def get_settings() -> Settings:
    """Return the application settings, loading them only once.

    Returns:
        The cached Settings instance, populated from environment
        variables and the .env file.

    Raises:
        pydantic.ValidationError: If a required setting such as
            DATABASE_URL is missing (raised on the first call only).
    """
    return Settings()
