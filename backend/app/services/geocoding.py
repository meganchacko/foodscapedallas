"""Turns an address or place name into coordinates, using OpenStreetMap's Nominatim service.

Kept in its own module so the rest of the app only knows "geocode this text" and doesn't
depend on Nominatim: tests swap in a fake fetch function, and changing providers means
changing only this file.

Nominatim is free and shared, and its usage policy asks for at most 1 request per second, an
identifying User-Agent, and caching of results. We do all three.
"""

import json
import logging
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass

import requests
from redis import Redis
from redis.exceptions import RedisError

from app.cache import get_cached, set_cached

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "FoodScapeDallas/0.1 (https://github.com/meganchacko/foodscapedallas)"

# Only search around Dallas County (left, top, right, bottom), so "Main St" finds Dallas's
DALLAS_VIEWBOX = "-97.05,33.00,-96.50,32.53"

CACHE_TTL_SECONDS = 30 * 24 * 60 * 60  # addresses don't move
RATE_LIMIT_KEY = "nominatim:rate_limit"
RATE_LIMIT_WAIT_SECONDS = 5


@dataclass(frozen=True)
class GeocodeResult:
    lat: float
    lng: float
    display_name: str


class GeocoderUnavailable(Exception):
    """Nominatim couldn't be reached, or we'd have to wait too long to stay under its limit."""


def fetch_nominatim(query: str) -> list[dict]:
    """Ask Nominatim for the best match near Dallas. Returns its raw JSON results."""
    params = {
        "q": query,
        "format": "jsonv2",
        "limit": 1,
        "countrycodes": "us",
        "viewbox": DALLAS_VIEWBOX,
        "bounded": 1,  # only return results inside the viewbox
    }
    response = requests.get(
        NOMINATIM_URL, params=params, headers={"User-Agent": USER_AGENT}, timeout=10
    )
    response.raise_for_status()
    return response.json()


def parse_nominatim(results: list[dict]) -> GeocodeResult | None:
    if not results:
        return None
    best = results[0]
    # Nominatim returns coordinates as strings
    return GeocodeResult(
        lat=float(best["lat"]), lng=float(best["lon"]), display_name=best["display_name"]
    )


def normalize(query: str) -> str:
    """'  1500 Marilla St ' and '1500 marilla st' are the same search: one cache entry."""
    return " ".join(query.lower().split())


class NominatimGeocoder:
    def __init__(self, cache: Redis, fetch: Callable[[str], list[dict]] = fetch_nominatim):
        self.cache = cache
        self.fetch = fetch

    def geocode(self, query: str) -> GeocodeResult | None:
        key = f"geocode:v1:{normalize(query)}"
        cached = get_cached(self.cache, key)
        if cached is not None:
            data = json.loads(cached)
            # "no match" is cached too, so a repeated typo doesn't hit Nominatim again
            return GeocodeResult(**data) if data else None

        self._wait_for_rate_limit()
        try:
            result = parse_nominatim(self.fetch(normalize(query)))
        except requests.RequestException as error:
            raise GeocoderUnavailable("Nominatim request failed") from error

        set_cached(
            self.cache, key, json.dumps(asdict(result) if result else None), CACHE_TTL_SECONDS
        )
        return result

    def _wait_for_rate_limit(self) -> None:
        """Allow one Nominatim request per second across every API process.

        SET with nx=True only succeeds if the key doesn't exist, and px=1000 deletes it after
        1 second. So whoever sets it may make a request; everyone else waits for it to expire.
        """
        deadline = time.monotonic() + RATE_LIMIT_WAIT_SECONDS
        while True:
            try:
                if self.cache.set(RATE_LIMIT_KEY, 1, nx=True, px=1000):
                    return
            except RedisError:
                logger.warning("Rate limiter unavailable; calling Nominatim anyway")
                return
            if time.monotonic() > deadline:
                raise GeocoderUnavailable("Too many geocoding requests right now")
            time.sleep(0.1)
