"""Response shape for GET /tracts: a GeoJSON FeatureCollection, one Feature per census tract.

GeoJSON is the standard format for map data: each Feature has a geometry (the tract's shape)
and properties (its stats). Leaflet can draw it directly.
"""

from typing import Literal

from pydantic import BaseModel


class FoodAccess(BaseModel):
    """A tract's USDA food access flags under one definition."""

    low_income: bool | None
    low_access: bool | None
    low_income_low_access: bool | None
    low_access_population: int | None


class TractProperties(BaseModel):
    geoid: str
    population: int | None
    obesity_pct: float | None
    # straight-line distance from inside the tract to the closest grocery store, in meters
    nearest_grocery_m: int | None
    # keyed by measure, e.g. "usda_2019_supermarkets" and "usda_2025_snap_retailers"
    food_access: dict[str, FoodAccess]


class TractFeature(BaseModel):
    type: Literal["Feature"] = "Feature"
    geometry: dict  # GeoJSON MultiPolygon, built by PostGIS
    properties: TractProperties


class TractCollection(BaseModel):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[TractFeature]
