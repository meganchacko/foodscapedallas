from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from redis import Redis

from app.cache import get_redis
from app.schemas.geocode import GeocodeResponse
from app.services.geocoding import GeocoderUnavailable, NominatimGeocoder

router = APIRouter()


def get_geocoder(cache: Annotated[Redis, Depends(get_redis)]) -> NominatimGeocoder:
    return NominatimGeocoder(cache)


@router.get("/geocode", response_model=GeocodeResponse)
def geocode(
    q: Annotated[str, Query(min_length=3, max_length=200, description="Address or place name")],
    geocoder: Annotated[NominatimGeocoder, Depends(get_geocoder)],
) -> GeocodeResponse:
    """Coordinates for an address or place in the Dallas area.

    404 if nothing matches; 503 if the geocoding service is unavailable.
    """
    try:
        result = geocoder.geocode(q)
    except GeocoderUnavailable:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Address search is busy right now. Please try again in a moment.",
        ) from None
    if result is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "We couldn't find that address in the Dallas area. "
            "Try adding a street number or ZIP code.",
        )
    return GeocodeResponse(lat=result.lat, lng=result.lng, display_name=result.display_name)
