"""2020 census tract boundaries for Dallas County, from Census TIGER/Line."""

import geopandas as gpd
from sqlalchemy import Engine, text

from pipeline.download import download

# County-level file from the 2020 redistricting (PL 94-171) release: just Dallas County's 645 tracts
TRACTS_URL = (
    "https://www2.census.gov/geo/tiger/TIGER2020PL/STATE/48_TEXAS/48113/tl_2020_48113_tract20.zip"
)

# For the map's lighter copy of each shape. Measured on Dallas tracts: borders move at most
# ~20 m (median ~6 m), and the map payload is about half the size of the full-detail shapes.
SIMPLIFY_TOLERANCE_DEGREES = 0.0002

UPSERT_TRACT = text(
    """
    INSERT INTO tracts (geoid, geom, geom_simplified)
    VALUES (
        :geoid,
        ST_Multi(ST_GeomFromText(:wkt, 4326)),
        ST_Multi(ST_GeomFromText(:simplified_wkt, 4326))
    )
    ON CONFLICT (geoid) DO UPDATE
    SET geom = EXCLUDED.geom, geom_simplified = EXCLUDED.geom_simplified
    """
)


def read_tracts(path) -> gpd.GeoDataFrame:
    tracts = gpd.read_file(path)[["GEOID20", "geometry"]].rename(columns={"GEOID20": "geoid"})
    # TIGER files use NAD83 (EPSG:4269); convert to WGS 84 (EPSG:4326) like everything else
    return tracts.to_crs(epsg=4326)


def simplify_tracts(tracts: gpd.GeoDataFrame) -> gpd.GeoSeries:
    # Coverage simplification treats all tracts as one connected map: each shared border is
    # simplified once and used by both neighbors, so no gaps or overlaps appear between them.
    # (Simplifying each tract on its own lets neighbors drift apart along their shared edge.)
    return tracts.geometry.simplify_coverage(SIMPLIFY_TOLERANCE_DEGREES)


def upsert_tracts(engine: Engine, tracts: gpd.GeoDataFrame) -> int:
    simplified = simplify_tracts(tracts)
    # ST_Multi turns single Polygons into MultiPolygons, so every row matches the column type
    rows = [
        {"geoid": geoid, "wkt": shape.wkt, "simplified_wkt": simple_shape.wkt}
        for geoid, shape, simple_shape in zip(
            tracts["geoid"], tracts.geometry, simplified, strict=True
        )
    ]
    with engine.begin() as connection:
        connection.execute(UPSERT_TRACT, rows)
    return len(rows)


def load(engine: Engine) -> int:
    path = download(TRACTS_URL, "tl_2020_48113_tract20.zip")
    return upsert_tracts(engine, read_tracts(path))
