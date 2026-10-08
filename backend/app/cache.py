import logging
from functools import lru_cache

from redis import Redis
from redis.backoff import NoBackoff
from redis.exceptions import RedisError
from redis.retry import Retry

from app.config import get_settings

logger = logging.getLogger(__name__)


def create_redis(host: str, port: int, db: int = 0) -> Redis:
    return Redis(
        host=host,
        port=port,
        db=db,
        socket_connect_timeout=2,
        socket_timeout=2,
        # The client normally retries a failed connection 3 times with growing waits (~3.5s per
        # call). For a cache, a fast miss beats a slow hit: fail at once and use the database.
        retry=Retry(NoBackoff(), retries=0),
    )


@lru_cache
def get_redis() -> Redis:
    # One client for the whole app; like the DB engine, it pools connections internally
    settings = get_settings()
    return create_redis(settings.redis_host, settings.redis_port)


# The cache is an optimization, never a requirement: if Redis is down, these log a warning
# and the endpoint falls back to the database instead of failing.


def get_cached(cache: Redis, key: str) -> bytes | None:
    try:
        return cache.get(key)
    except RedisError:
        logger.warning("Cache read failed for %s; using the database", key, exc_info=True)
        return None


def set_cached(cache: Redis, key: str, value: str, ttl_seconds: int) -> None:
    try:
        cache.set(key, value, ex=ttl_seconds)
    except RedisError:
        logger.warning("Cache write failed for %s", key, exc_info=True)
