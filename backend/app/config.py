from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App settings, read from environment variables (or a .env file in the working directory).

    Field names match env var names case-insensitively, e.g. `postgres_host` reads POSTGRES_HOST.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    redis_host: str = "localhost"
    redis_port: int = 6379

    @property
    def database_url(self) -> str:
        # "postgresql+psycopg" tells SQLAlchemy to use the psycopg (v3) driver
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    # lru_cache means the env is read once and the same Settings object is reused
    return Settings()
