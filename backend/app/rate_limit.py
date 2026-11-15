"""Rate limiting: cap how many requests a client can make in a time window (429 when over).

Counts live in Redis so every server process shares them (with in-memory counts, running 4
processes would quietly allow 4x the limit). It's a "fixed window" counter: one key per client,
per action, per window, e.g. ratelimit:geocode:<client>:<window number>, which Redis deletes
when the window is over.

Request limits fail open: if Redis is down, requests are allowed rather than blocked. Callers
can choose to fail closed instead (see allow()), for optional actions like saving a result.
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


def client_ip(request: Request) -> str:
    """The IP of the person making the request.

    Without a proxy, that's the connecting IP (request.client). Behind one (the Vite dev server,
    Azure's ingress), the connecting IP is the proxy's, and the real one is in X-Forwarded-For.
    Each proxy APPENDS the address it received the request from, e.g.

        X-Forwarded-For: <anything the client sent>, <IP our proxy saw>

    The client controls the start of that list, so only the entries our own proxies added (the
    last TRUSTED_PROXY_HOPS of them) can be believed. With one proxy, that's the last entry.
    """
    hops = get_settings().trusted_proxy_hops
    if hops > 0:
        # A client may send several X-Forwarded-For headers; together they form one list
        forwarded = ",".join(request.headers.getlist("X-Forwarded-For"))
        addresses = [address.strip() for address in forwarded.split(",") if address.strip()]
        if len(addresses) >= hops:
            return addresses[-hops]
    return request.client.host if request.client else "unknown"


def client_key(request: Request) -> str:
    """Identify the client without storing their IP: a short hash of it."""
    return hashlib.sha256(client_ip(request).encode()).hexdigest()[:16]


def allow(cache: Redis, key: str, limit: int, window_seconds: int, fail_open: bool = True) -> bool:
    """Count one use of `key` in the current window, and say whether it's within `limit`.

    If Redis is unavailable, returns `fail_open`: True lets the action happen anyway (better for
    requests people are waiting on), False blocks it (better for optional extras).
    """
    if not get_settings().rate_limit_enabled:
        return True
    window = int(time.time() // window_seconds)
    window_key = f"ratelimit:{key}:{window}"
    try:
        # INCR and EXPIRE together in one transaction: count this use, and make sure the key is
        # deleted once its window is over
        count, _ = cache.pipeline().incr(window_key).expire(window_key, window_seconds).execute()
    except RedisError:
        logger.warning("Rate limiter unavailable; %s", "allowing" if fail_open else "blocking")
        return fail_open
    return count <= limit


class RateLimit:
    """A FastAPI dependency: Depends(RateLimit("geocode", limit=10, window_seconds=60))."""

    def __init__(self, name: str, limit: int, window_seconds: int = 60):
        self.name = name
        self.limit = limit
        self.window_seconds = window_seconds

    def __call__(self, request: Request, cache: Annotated[Redis, Depends(get_redis)]) -> None:
        key = f"{self.name}:{client_key(request)}"
        if not allow(cache, key, self.limit, self.window_seconds):
            seconds_left = self.window_seconds - int(time.time() % self.window_seconds)
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "Too many requests. Please wait a minute and try again.",
                headers={"Retry-After": str(seconds_left)},
            )
