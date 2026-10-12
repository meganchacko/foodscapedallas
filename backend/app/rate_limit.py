"""Rate limiting: cap how many requests one client can make per minute (429 when over).

Counts live in Redis so every server process shares them (with in-memory counts, running 4
processes would quietly allow 4x the limit). It's a "fixed window" counter: one key per client,
per endpoint, per minute, e.g. ratelimit:geocode:<client>:<minute>, which Redis deletes when
the minute is over.

Like the cache, it fails open: if Redis is down, requests are allowed rather than blocked.
"""

import hashlib
import logging
import time
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from redis import Redis
from redis.exceptions import RedisError

from app.cache import get_redis
from app.config import get_settings

logger = logging.getLogger(__name__)

WINDOW_SECONDS = 60


def client_key(request: Request) -> str:
    """Identify the client without storing their IP: a short hash of it.

    request.client is the connecting IP. Behind a proxy (Vite in development, a load balancer in
    production) uvicorn replaces it with the original IP from X-Forwarded-For, but only for
    proxies listed in FORWARDED_ALLOW_IPS, so clients can't fake their IP with that header.
    """
    host = request.client.host if request.client else "unknown"
    return hashlib.sha256(host.encode()).hexdigest()[:16]


class RateLimit:
    """A FastAPI dependency: Depends(RateLimit("geocode", per_minute=30))."""

    def __init__(self, name: str, per_minute: int):
        self.name = name
        self.per_minute = per_minute

    def __call__(self, request: Request, cache: Annotated[Redis, Depends(get_redis)]) -> None:
        if not get_settings().rate_limit_enabled:
            return
        window = int(time.time() // WINDOW_SECONDS)
        key = f"ratelimit:{self.name}:{client_key(request)}:{window}"
        try:
            # INCR and EXPIRE together in one transaction: count this request, and make sure
            # the key is deleted once its minute is over
            count, _ = cache.pipeline().incr(key).expire(key, WINDOW_SECONDS).execute()
        except RedisError:
            logger.warning("Rate limiter unavailable; allowing the request")
            return
        if count > self.per_minute:
            seconds_left = WINDOW_SECONDS - int(time.time() % WINDOW_SECONDS)
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "Too many requests. Please wait a minute and try again.",
                headers={"Retry-After": str(seconds_left)},
            )
