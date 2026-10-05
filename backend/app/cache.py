from functools import lru_cache

from redis import Redis

from app.config import get_settings


@lru_cache
def get_redis() -> Redis:
    # One client for the whole app; like the DB engine, it pools connections internally
    settings = get_settings()
    return Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        socket_connect_timeout=2,
        socket_timeout=2,
    )
