"""Response shape for GET /places: a GeoJSON FeatureCollection of points."""

from typing import Literal

from pydantic import BaseModel

# Must match the CHECK constraint on places.type
PlaceType = Literal["grocery", "pantry", "farmers_market"]


class PlaceProperties(BaseModel):
    id: int
    name: str
    type: PlaceType
    address: str | None
    hours: str | None
    # None means unknown, which is different from "doesn't accept"
    accepts_snap: bool | None
    accepts_wic: bool | None


class PointGeometry(BaseModel):
    type: Literal["Point"] = "Point"
    coordinates: tuple[float, float]  # GeoJSON order is [longitude, latitude]


class PlaceFeature(BaseModel):
    type: Literal["Feature"] = "Feature"
    geometry: PointGeometry
    properties: PlaceProperties


class PlaceCollection(BaseModel):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[PlaceFeature]
