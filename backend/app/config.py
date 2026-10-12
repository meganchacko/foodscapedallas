from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


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
    # "require" in production: the cloud database only accepts encrypted (TLS) connections.
    # "prefer" locally: use encryption if the server offers it (the Docker database doesn't).
    postgres_sslmode: str = "prefer"

    redis_host: str = "localhost"
    redis_port: int = 6379

    # Websites allowed to call this API from the browser (CORS), comma-separated, e.g. the
    # deployed frontend's address. Empty locally, where the Vite proxy makes calls same-origin.
    allowed_origins: str = ""

    # Turned off for load tests (one machine sends every request) and in the test suite
    rate_limit_enabled: bool = True

    # The trained health check model. Locally that's ml/model/ in the repo; the Docker image
    # sets MODEL_DIR=/app/model.
    model_dir: Path = Path(__file__).resolve().parents[2] / "ml" / "model"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

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
def get_settings() -> Settings:
    # lru_cache means the env is read once and the same Settings object is reused
    return Settings()
