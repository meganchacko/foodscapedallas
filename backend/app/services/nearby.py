"""Finds food near a point (GET /places/nearby)."""

from sqlalchemy import Engine, text

from app.schemas.nearby import NearbyPlace, NearbyResponse, SearchLocation
from app.schemas.places import PlaceType

METERS_PER_MILE = 1609.344
MAX_RESULTS = 50

# The food access definition the resident view reports on
LOW_ACCESS_MEASURE = "usda_2019_supermarkets"

# ST_DWithin keeps places within the radius and uses the geography index (ix_places_geography);
# ST_Distance then measures each one. Both work in meters because of ::geography.
NEARBY_QUERY = text(
    """
    WITH here AS (SELECT ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography AS point)
    SELECT
        places.id, places.name, places.type, places.address, places.hours,
        places.accepts_snap, places.accepts_wic,
        ST_X(places.geom) AS lng,
        ST_Y(places.geom) AS lat,
        ST_Distance(places.geom::geography, here.point) AS distance_m
    FROM places, here
    WHERE ST_DWithin(places.geom::geography, here.point, :radius_m)
      AND (CAST(:type AS varchar) IS NULL OR places.type = :type)
      AND (NOT :snap_only OR places.accepts_snap)
    ORDER BY distance_m
    LIMIT :limit
    """
)

# Which tract contains the point, and is it low access?
TRACT_QUERY = text(
    """
    SELECT tracts.geoid, tract_food_access.low_access
    FROM tracts
    LEFT JOIN tract_food_access
        ON tract_food_access.geoid = tracts.geoid AND tract_food_access.measure = :measure
    WHERE ST_Contains(tracts.geom, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326))
    LIMIT 1
    """
)


def find_nearby(
    engine: Engine,
    lat: float,
    lng: float,
    radius_miles: float,
    place_type: PlaceType | None,
    snap_only: bool,
) -> NearbyResponse:
    with engine.connect() as connection:
        tract = connection.execute(
            TRACT_QUERY, {"lat": lat, "lng": lng, "measure": LOW_ACCESS_MEASURE}
        ).first()
        rows = connection.execute(
            NEARBY_QUERY,
            {
                "lat": lat,
                "lng": lng,
                "radius_m": radius_miles * METERS_PER_MILE,
                "type": place_type,
                "snap_only": snap_only,
                "limit": MAX_RESULTS,
            },
        ).all()

    location = SearchLocation(
        lat=lat,
        lng=lng,
        in_dallas_county=tract is not None,
        tract_geoid=tract.geoid if tract else None,
        low_access=tract.low_access if tract else None,
    )
    places = [
        NearbyPlace(
            id=row.id,
            name=row.name,
            type=row.type,
            address=row.address,
            hours=row.hours,
            accepts_snap=row.accepts_snap,
            accepts_wic=row.accepts_wic,
            lat=round(row.lat, 5),
            lng=round(row.lng, 5),
            distance_m=round(row.distance_m),
        )
        for row in rows
    ]
    return NearbyResponse(location=location, radius_miles=radius_miles, places=places)
