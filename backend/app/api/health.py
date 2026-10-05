import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.cache import get_redis
from app.db.database import get_engine
from app.schemas.health import HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter()


def check_db(engine: Engine) -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError:
        logger.exception("Database health check failed")
        return False


def check_cache(cache: Redis) -> bool:
    try:
        return bool(cache.ping())
    except RedisError:
        logger.exception("Redis health check failed")
        return False


@router.get("/health", response_model=HealthResponse)
def health(
    response: Response,
    engine: Annotated[Engine, Depends(get_engine)],
    cache: Annotated[Redis, Depends(get_redis)],
) -> HealthResponse:
    db_ok = check_db(engine)
    cache_ok = check_cache(cache)

    # 503 lets load balancers and monitors tell "up but broken" apart from "healthy"
    if not (db_ok and cache_ok):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthResponse(
        api="ok",
        db="ok" if db_ok else "error",
        cache="ok" if cache_ok else "error",
    )
