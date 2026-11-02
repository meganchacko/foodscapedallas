"""Response shape for GET /places/nearby."""

from pydantic import BaseModel

from app.schemas.places import PlaceProperties


class NearbyPlace(PlaceProperties):
    lat: float
    lng: float
    distance_m: int  # straight-line distance from the searched point


class SearchLocation(BaseModel):
    lat: float
    lng: float
    in_coverage_area: bool  # inside one of the covered counties' tracts
    tract_geoid: str | None
    # Whether the point's tract is low access under the 2019 supermarket definition (what
    # "food desert" usually means). None when unknown or outside the covered counties.
    low_access: bool | None


class NearbyResponse(BaseModel):
    location: SearchLocation
    radius_miles: float
    places: list[NearbyPlace]  # closest first
