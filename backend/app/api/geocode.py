from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from redis import Redis

from app.cache import get_redis
from app.rate_limit import RateLimit
from app.schemas.geocode import GeocodeResponse
from app.services.geocoding import GeocoderUnavailable, NominatimGeocoder

router = APIRouter()


def get_geocoder(cache: Annotated[Redis, Depends(get_redis)]) -> NominatimGeocoder:
    return NominatimGeocoder(cache)


@router.get(
    "/geocode",
    response_model=GeocodeResponse,
    # protects Nominatim, which allows us 1 request per second in total
    dependencies=[Depends(RateLimit("geocode", per_minute=30))],
)
def geocode(
    q: Annotated[str, Query(min_length=3, max_length=200, description="Address or place name")],
    geocoder: Annotated[NominatimGeocoder, Depends(get_geocoder)],
    response: Response,
) -> GeocodeResponse:
    """Coordinates for an address or place in the Dallas area.

    404 if nothing matches; 503 if the geocoding service is unavailable. The X-Cache header says
    whether the answer came from our cache (HIT) or from Nominatim (MISS).
    """
    try:
        lookup = geocoder.geocode(q)
    except GeocoderUnavailable:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Address search is busy right now. Please try again in a moment.",
        ) from None
    cache_header = {"X-Cache": "HIT" if lookup.from_cache else "MISS"}
    if lookup.result is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "We couldn't find that address in the Dallas area. "
            "Try adding a street number or ZIP code.",
            headers=cache_header,
        )
    response.headers.update(cache_header)
    result = lookup.result
    return GeocodeResponse(lat=result.lat, lng=result.lng, display_name=result.display_name)
