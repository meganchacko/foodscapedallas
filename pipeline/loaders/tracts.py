"""2020 census tract boundaries for our counties, from Census TIGER/Line."""

import geopandas as gpd
import pandas as pd
from sqlalchemy import Engine, text

from pipeline.counties import COUNTY_GEOIDS
from pipeline.download import download

# County-level files from the 2020 redistricting (PL 94-171) release, one per county
TRACTS_URL = "https://www2.census.gov/geo/tiger/TIGER2020PL/STATE/48_TEXAS/{county}/{filename}"

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


def download_county_tracts(county: str) -> gpd.GeoDataFrame:
    filename = f"tl_2020_{county}_tract20.zip"
    return read_tracts(download(TRACTS_URL.format(county=county, filename=filename), filename))


def load(engine: Engine) -> int:
    # One table for all counties, so simplification keeps borders between counties aligned too
    tracts = pd.concat([download_county_tracts(county) for county in COUNTY_GEOIDS])
    return upsert_tracts(engine, tracts.reset_index(drop=True))
