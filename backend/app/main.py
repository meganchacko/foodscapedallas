from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware

from app.api import geocode, health, health_check, places, tracts
from app.config import get_settings
from app.logging_config import configure_logging
from app.middleware import add_security_headers, configure_cors, observe_request
from app.services.health_check import get_health_model

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Runs once when the server starts: load the health check model now, so the first user
    # doesn't wait for it, and a missing or broken model file stops startup with a clear error
    get_health_model()
    yield


def docs_options(enabled: bool) -> dict[str, str | None]:
    """FastAPI serves its docs pages by default; setting their URLs to None turns them off."""
    return {} if enabled else {"docs_url": None, "redoc_url": None, "openapi_url": None}


app = FastAPI(
    title="FoodScape Dallas API",
    lifespan=lifespan,
    **docs_options(get_settings().api_docs_enabled),
)

# Compress responses over 1 KB when the browser accepts gzip. Map data is mostly repeated
# coordinate text, which compresses to a fraction of its size.
app.add_middleware(GZipMiddleware, minimum_size=1000)

configure_cors(app, get_settings().cors_origins)
app.middleware("http")(add_security_headers)
app.middleware("http")(observe_request)

app.include_router(health.router)
app.include_router(tracts.router)
app.include_router(places.router)
app.include_router(geocode.router)
app.include_router(health_check.router)
