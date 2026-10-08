"""Builds the map's tract data (GET /tracts) from the database."""

import json
from collections import defaultdict

from sqlalchemy import Engine, text

from app.schemas.tracts import FoodAccess, TractCollection, TractFeature, TractProperties

# 5 decimal places of latitude/longitude is about 1 m: plenty for a map, and much smaller JSON
COORDINATE_DECIMALS = 5

TRACTS_QUERY = text(
    """
    SELECT
        tracts.geoid,
        tracts.population,
        tracts.obesity_pct,
        ST_AsGeoJSON(COALESCE(tracts.geom_simplified, tracts.geom), :decimals) AS geometry,
        nearest_grocery.distance_m AS nearest_grocery_m
    FROM tracts
    -- For each tract, find the closest grocery store. LATERAL lets the subquery use this row's
    -- tract. The inner query uses the spatial index (<-> is "nearest first") to grab the 5
    -- closest stores quickly; <-> measures in degrees, which is only approximately distance,
    -- so the outer query then measures those 5 properly in meters (::geography) and keeps
    -- the smallest.
    LEFT JOIN LATERAL (
        SELECT min(
            ST_Distance(candidates.geom::geography, ST_PointOnSurface(tracts.geom)::geography)
        ) AS distance_m
        FROM (
            SELECT places.geom
            FROM places
            WHERE places.type = 'grocery'
            ORDER BY places.geom <-> ST_PointOnSurface(tracts.geom)
            LIMIT 5
        ) AS candidates
    ) AS nearest_grocery ON true
    ORDER BY tracts.geoid
    """
)

FOOD_ACCESS_QUERY = text(
    """
    SELECT geoid, measure, low_income, low_access, low_income_low_access, low_access_population
    FROM tract_food_access
    """
)


def get_tract_collection(engine: Engine) -> TractCollection:
    with engine.connect() as connection:
        tract_rows = connection.execute(TRACTS_QUERY, {"decimals": COORDINATE_DECIMALS}).all()
        food_access_rows = connection.execute(FOOD_ACCESS_QUERY).all()

    # geoid -> {measure -> FoodAccess}
    food_access: dict[str, dict[str, FoodAccess]] = defaultdict(dict)
    for row in food_access_rows:
        food_access[row.geoid][row.measure] = FoodAccess(
            low_income=row.low_income,
            low_access=row.low_access,
            low_income_low_access=row.low_income_low_access,
            low_access_population=row.low_access_population,
        )

    features = [
        TractFeature(
            geometry=json.loads(row.geometry),
            properties=TractProperties(
                geoid=row.geoid,
                population=row.population,
                obesity_pct=float(row.obesity_pct) if row.obesity_pct is not None else None,
                nearest_grocery_m=(
                    round(row.nearest_grocery_m) if row.nearest_grocery_m is not None else None
                ),
                food_access=food_access.get(row.geoid, {}),
            ),
        )
        for row in tract_rows
    ]
    return TractCollection(features=features)
