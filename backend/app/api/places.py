from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Engine

from app.db.database import get_engine
from app.schemas.places import PlaceCollection, PlaceType
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
