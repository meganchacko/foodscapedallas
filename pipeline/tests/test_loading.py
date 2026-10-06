"""Writing to the database: loaders must be idempotent (running twice changes nothing)."""

import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon
from sqlalchemy import text

from pipeline.loaders.census_blocks import upsert_blocks
from pipeline.loaders.food_access import upsert_food_access
from pipeline.loaders.places import sync_places
from pipeline.loaders.tracts import upsert_tracts

TRACT_GEOID = "48113000100"

# A small square in downtown Dallas, standing in for a tract
TRACT_SHAPE = Polygon([(-96.81, 32.77), (-96.79, 32.77), (-96.79, 32.79), (-96.81, 32.79)])


def count(engine, table):
    with engine.connect() as connection:
        return connection.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()


def load_tract(engine):
    tracts = gpd.GeoDataFrame({"geoid": [TRACT_GEOID]}, geometry=[TRACT_SHAPE], crs="EPSG:4326")
    upsert_tracts(engine, tracts)


def place(source_id, lat=32.78, lon=-96.80):
    return {
        "source_id": source_id,
        "name": f"Store {source_id}",
        "type": "grocery",
        "lat": lat,
        "lon": lon,
        "address": None,
        "hours": None,
        "accepts_snap": None,
        "accepts_wic": None,
    }


def test_tracts_load_twice_without_duplicates(clean_engine):
    load_tract(clean_engine)
    load_tract(clean_engine)

    assert count(clean_engine, "tracts") == 1


def test_blocks_load_twice_and_set_tract_population(clean_engine):
    load_tract(clean_engine)
    blocks = pd.DataFrame(
        {
            "geoid": [TRACT_GEOID + "1001", TRACT_GEOID + "1002"],
            "lat": [32.78, 32.781],
            "lon": [-96.80, -96.801],
            "population": [30, 12],
        }
    )

    upsert_blocks(clean_engine, blocks)
    upsert_blocks(clean_engine, blocks)

    assert count(clean_engine, "census_blocks") == 2
    with clean_engine.connect() as connection:
        population = connection.execute(text("SELECT population FROM tracts")).scalar_one()
    assert population == 42


def test_food_access_keeps_one_row_per_tract_and_measure(clean_engine):
    load_tract(clean_engine)
    food_access = pd.DataFrame(
        [
            {
                "geoid": TRACT_GEOID,
                "low_income": True,
                "low_access": True,
                "low_income_low_access": True,
                "low_access_population": 500,
            }
        ]
    )

    upsert_food_access(clean_engine, "usda_2019_supermarkets", food_access)
    upsert_food_access(clean_engine, "usda_2019_supermarkets", food_access)
    upsert_food_access(clean_engine, "usda_2025_snap_retailers", food_access)

    assert count(clean_engine, "tract_food_access") == 2


def test_places_load_twice_without_duplicates(clean_engine):
    load_tract(clean_engine)

    sync_places(clean_engine, "osm", [place("node/1"), place("node/2")])
    kept = sync_places(clean_engine, "osm", [place("node/1"), place("node/2")])

    assert kept == 2
    assert count(clean_engine, "places") == 2


def test_places_outside_dallas_county_are_skipped(clean_engine):
    load_tract(clean_engine)

    kept = sync_places(clean_engine, "osm", [place("node/fort-worth", lat=32.75, lon=-97.33)])

    assert kept == 0


def test_places_missing_from_the_source_are_deleted(clean_engine):
    load_tract(clean_engine)
    sync_places(clean_engine, "osm", [place("node/1"), place("node/2")])

    kept = sync_places(clean_engine, "osm", [place("node/1")])  # node/2 closed

    assert kept == 1


def test_syncing_one_source_leaves_other_sources_alone(clean_engine):
    load_tract(clean_engine)
    sync_places(clean_engine, "osm", [place("node/1")])

    sync_places(clean_engine, "pantry_seed", [])

    assert count(clean_engine, "places") == 1
