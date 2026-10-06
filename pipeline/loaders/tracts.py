"""2020 census tract boundaries for Dallas County, from Census TIGER/Line."""

import geopandas as gpd
from sqlalchemy import Engine, text

from pipeline.download import download

# County-level file from the 2020 redistricting (PL 94-171) release: just Dallas County's 645 tracts
TRACTS_URL = (
    "https://www2.census.gov/geo/tiger/TIGER2020PL/STATE/48_TEXAS/48113/tl_2020_48113_tract20.zip"
)

UPSERT_TRACT = text(
    """
    INSERT INTO tracts (geoid, geom)
    VALUES (:geoid, ST_Multi(ST_GeomFromText(:wkt, 4326)))
    ON CONFLICT (geoid) DO UPDATE SET geom = EXCLUDED.geom
    """
)


def read_tracts(path) -> gpd.GeoDataFrame:
    tracts = gpd.read_file(path)[["GEOID20", "geometry"]].rename(columns={"GEOID20": "geoid"})
    # TIGER files use NAD83 (EPSG:4269); convert to WGS 84 (EPSG:4326) like everything else
    return tracts.to_crs(epsg=4326)


def upsert_tracts(engine: Engine, tracts: gpd.GeoDataFrame) -> int:
    # ST_Multi turns single Polygons into MultiPolygons, so every row matches the column type
    rows = [{"geoid": row.geoid, "wkt": row.geometry.wkt} for row in tracts.itertuples()]
    with engine.begin() as connection:
        connection.execute(UPSERT_TRACT, rows)
    return len(rows)


def load(engine: Engine) -> int:
    path = download(TRACTS_URL, "tl_2020_48113_tract20.zip")
    return upsert_tracts(engine, read_tracts(path))
