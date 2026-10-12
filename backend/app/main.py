from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware

from app.api import geocode, health, health_check, places, tracts
from app.middleware import add_server_timing
from app.services.health_check import get_health_model


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Runs once when the server starts: load the health check model now, so the first user
    # doesn't wait for it, and a missing or broken model file stops startup with a clear error
    get_health_model()
    yield


app = FastAPI(title="FoodScape Dallas API", lifespan=lifespan)

# Compress responses over 1 KB when the browser accepts gzip. Map data is mostly repeated
# coordinate text, which compresses to a fraction of its size.
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.middleware("http")(add_server_timing)

app.include_router(health.router)
app.include_router(tracts.router)
app.include_router(places.router)
app.include_router(geocode.router)
app.include_router(health_check.router)
