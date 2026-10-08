from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # Redis, so the pipeline can clear the API's cached map data after loading
    redis_host: str = "localhost"
    redis_port: int = 6379

    # Free key from https://api.census.gov/data/key_signup.html (needed for block population)
    census_api_key: str | None = None

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> PipelineSettings:
    return PipelineSettings()
