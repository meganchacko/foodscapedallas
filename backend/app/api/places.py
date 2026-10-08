from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Engine

from app.db.database import get_engine
from app.schemas.nearby import NearbyResponse
from app.schemas.places import PlaceCollection, PlaceType
from app.services.nearby import find_nearby
from app.services.places import get_place_collection

router = APIRouter()


@router.get("/places", response_model=PlaceCollection)
def list_places(
    engine: Annotated[Engine, Depends(get_engine)],
    place_type: Annotated[PlaceType | None, Query(alias="type")] = None,
) -> PlaceCollection:
    """Grocery stores, food pantries, and farmers markets as GeoJSON points.

    ?type=grocery (or pantry, farmers_market) returns only that kind; any other value is a 422.
    """
    return get_place_collection(engine, place_type)


@router.get("/places/nearby", response_model=NearbyResponse)
def list_nearby_places(
    engine: Annotated[Engine, Depends(get_engine)],
    lat: Annotated[float, Query(ge=-90, le=90)],
    lng: Annotated[float, Query(ge=-180, le=180)],
    radius: Annotated[float, Query(gt=0, le=10, description="Search radius in miles")] = 1.0,
    place_type: Annotated[PlaceType | None, Query(alias="type")] = None,
    snap: Annotated[bool, Query(description="Only places known to accept SNAP")] = False,
) -> NearbyResponse:
    """Places within `radius` miles of a point, closest first, plus whether the point is in a
    low food access tract. Out-of-range values (e.g. lat=200, radius=50) are a 422.
    """
    return find_nearby(engine, lat, lng, radius, place_type, snap)
