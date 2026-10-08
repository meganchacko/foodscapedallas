import logging

from redis import Redis
from redis.backoff import NoBackoff
from redis.exceptions import RedisError
from redis.retry import Retry

from pipeline.config import get_settings

logger = logging.getLogger(__name__)

# Cached API responses built from the data the pipeline loads. Must match the key prefix used
# in backend/app/api/tracts.py.
MAP_CACHE_PATTERN = "tracts:*"


def create_redis(host: str | None = None, port: int | None = None) -> Redis:
    settings = get_settings()
    return Redis(
        host=host or settings.redis_host,
        port=port or settings.redis_port,
        socket_connect_timeout=2,
        retry=Retry(NoBackoff(), retries=0),  # if Redis is down, say so at once
    )


def clear_map_cache(cache: Redis) -> int:
    """Delete cached map responses so the API rebuilds them from the new data.

    A failure here doesn't fail the pipeline: the data is already loaded, and the API's cache
    expires on its own within a day.
    """
    try:
        keys = list(cache.scan_iter(match=MAP_CACHE_PATTERN))
        return cache.delete(*keys) if keys else 0
    except RedisError:
        logger.warning("Couldn't clear the map cache; it will expire on its own", exc_info=True)
        return 0
