from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware

from app.api import health, places, tracts

app = FastAPI(title="FoodScape Dallas API")

# Compress responses over 1 KB when the browser accepts gzip. Map data is mostly repeated
# coordinate text, which compresses to a fraction of its size.
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.include_router(health.router)
app.include_router(tracts.router)
app.include_router(places.router)
