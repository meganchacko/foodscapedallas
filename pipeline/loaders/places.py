"""Shared code for loaders that write to the places table (OpenStreetMap, food pantry seed)."""

from sqlalchemy import Engine, bindparam, text

# Insert a place only if it falls inside a Dallas County tract. Sources are fetched by bounding
# box (a rectangle), which also catches slivers of neighboring counties.
UPSERT_PLACE = text(
    """
    INSERT INTO places
        (name, type, geom, address, hours, accepts_snap, accepts_wic, source, source_id,
         last_updated)
    SELECT
        :name, :type, location.point, :address, :hours, :accepts_snap, :accepts_wic, :source,
        :source_id, now()
    FROM (SELECT ST_SetSRID(ST_MakePoint(:lon, :lat), 4326) AS point) AS location
    WHERE EXISTS (SELECT 1 FROM tracts WHERE ST_Contains(tracts.geom, location.point))
    ON CONFLICT (source, source_id) DO UPDATE SET
        name = EXCLUDED.name,
        type = EXCLUDED.type,
        geom = EXCLUDED.geom,
        address = EXCLUDED.address,
        hours = EXCLUDED.hours,
        accepts_snap = EXCLUDED.accepts_snap,
        accepts_wic = EXCLUDED.accepts_wic,
        last_updated = now()
    """
)

# Places this source no longer lists (closed, or removed from the map) get deleted
DELETE_MISSING = text(
    "DELETE FROM places WHERE source = :source AND source_id NOT IN :source_ids"
).bindparams(bindparam("source_ids", expanding=True))

COUNT_PLACES = text("SELECT count(*) FROM places WHERE source = :source")


def sync_places(engine: Engine, source: str, places: list[dict]) -> int:
    """Make the places table match `places` for this source: upsert them, delete the rest.

    Each place dict needs: source_id, name, type, lat, lon, address, hours, accepts_snap,
    accepts_wic. Returns how many places from this source are in the table afterwards.
    """
    rows = [{**place, "source": source} for place in places]
    with engine.begin() as connection:
        if rows:
            connection.execute(UPSERT_PLACE, rows)
            connection.execute(
                DELETE_MISSING,
                {"source": source, "source_ids": [row["source_id"] for row in rows]},
            )
        else:
            connection.execute(
                text("DELETE FROM places WHERE source = :source"), {"source": source}
            )
        return connection.execute(COUNT_PLACES, {"source": source}).scalar_one()
