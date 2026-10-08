from sqlalchemy import Engine, text

from app.schemas.places import (
    PlaceCollection,
    PlaceFeature,
    PlaceProperties,
    PlaceType,
    PointGeometry,
)

# CAST tells Postgres the parameter's type even when it's NULL ("no filter")
PLACES_QUERY = text(
    """
    SELECT
        id, name, type, address, hours, accepts_snap, accepts_wic,
        ST_X(geom) AS lon,
        ST_Y(geom) AS lat
    FROM places
    WHERE CAST(:type AS varchar) IS NULL OR type = :type
    ORDER BY name
    """
)


def get_place_collection(engine: Engine, place_type: PlaceType | None) -> PlaceCollection:
    with engine.connect() as connection:
        rows = connection.execute(PLACES_QUERY, {"type": place_type}).all()

    features = [
        PlaceFeature(
            # 5 decimal places is about 1 m
            geometry=PointGeometry(coordinates=(round(row.lon, 5), round(row.lat, 5))),
            properties=PlaceProperties(
                id=row.id,
                name=row.name,
                type=row.type,
                address=row.address,
                hours=row.hours,
                accepts_snap=row.accepts_snap,
                accepts_wic=row.accepts_wic,
            ),
        )
        for row in rows
    ]
    return PlaceCollection(features=features)
