from typing import Annotated

from fastapi import APIRouter, Depends, Response
from redis import Redis
from sqlalchemy import Engine

from app.cache import get_cached, get_redis, set_cached
from app.db.database import get_engine
from app.schemas.tracts import TractCollection
from app.services.tracts import get_tract_collection

router = APIRouter()

# The pipeline deletes every "tracts:*" key after loading new data. Bump the version when the
# response shape changes, so an old-shaped cached copy is never served.
TRACTS_CACHE_KEY = "tracts:v1"
# Safety net: even if the pipeline can't clear the cache, it refreshes within a day
CACHE_TTL_SECONDS = 24 * 60 * 60


@router.get("/tracts", response_model=TractCollection)
def list_tracts(
    engine: Annotated[Engine, Depends(get_engine)],
    cache: Annotated[Redis, Depends(get_redis)],
) -> Response:
    """Every Dallas County tract as GeoJSON, with its food access and health stats.

    Cache-aside: return the copy in Redis if there is one; otherwise build it from the
    database, store it in Redis, and return it.
    """
    cached = get_cached(cache, TRACTS_CACHE_KEY)
    if cached is not None:
        return Response(content=cached, media_type="application/json")

    body = get_tract_collection(engine).model_dump_json()
    set_cached(cache, TRACTS_CACHE_KEY, body, CACHE_TTL_SECONDS)
    return Response(content=body, media_type="application/json")
