from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy import Engine

from app.db.database import get_engine
from app.schemas.tracts import TractCollection
from app.services.tracts import get_tract_collection

router = APIRouter()


@router.get("/tracts", response_model=TractCollection)
def list_tracts(engine: Annotated[Engine, Depends(get_engine)]) -> Response:
    """Every Dallas County tract as GeoJSON, with its food access and health stats."""
    collection = get_tract_collection(engine)
    return Response(content=collection.model_dump_json(), media_type="application/json")
