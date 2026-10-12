from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class PipelineSettings(BaseSettings):
    """Database settings, read from the same env vars (or .env) as the backend.

    The pipeline is a separate program from the API, so it has its own small settings class
    instead of importing the backend's code.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    # "require" in production: the cloud database only accepts encrypted (TLS) connections.
    # "prefer" locally: use encryption if the server offers it (the Docker database doesn't).
    postgres_sslmode: str = "prefer"

    # Redis, so the pipeline can clear the API's cached map data after loading
    redis_host: str = "localhost"
    redis_port: int = 6379

    # Free key from https://api.census.gov/data/key_signup.html (needed for block population)
    census_api_key: str | None = None

    @property
    def database_url(self) -> str:
        # URL.create escapes special characters in the password (generated passwords often have
        # them, and an unescaped "@" or "/" would break the URL). "postgresql+psycopg" tells
        # SQLAlchemy to use the psycopg (v3) driver.
        return URL.create(
            "postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
            query={"sslmode": self.postgres_sslmode},
        ).render_as_string(hide_password=False)


@lru_cache
def get_settings() -> PipelineSettings:
    return PipelineSettings()
