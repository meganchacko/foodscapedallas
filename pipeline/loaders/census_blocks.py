"""2020 census blocks for Dallas County: a center point and population for each block.

Shapes come from the county TIGER/Line file, which has no population column, so population
comes from the Census Bureau's data API (2020 redistricting data, P1_001N = total population).
"""

import geopandas as gpd
import pandas as pd
import requests
from sqlalchemy import Engine, text

from pipeline.config import get_settings
from pipeline.download import USER_AGENT, download

BLOCKS_URL = (
    "https://www2.census.gov/geo/tiger/TIGER2020PL/STATE/48_TEXAS/48113/"
    "tl_2020_48113_tabblock20.zip"
)
POPULATION_API_URL = "https://api.census.gov/data/2020/dec/pl"

UPSERT_BLOCK = text(
    """
    INSERT INTO census_blocks (geoid, center, population)
    VALUES (:geoid, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), :population)
    ON CONFLICT (geoid) DO UPDATE
    SET center = EXCLUDED.center, population = EXCLUDED.population
    """
)

# A tract's population is the sum of its blocks (the first 11 digits of a block GEOID are its tract)
UPDATE_TRACT_POPULATION = text(
    """
    UPDATE tracts
    SET population = block_totals.population
    FROM (
        SELECT left(geoid, 11) AS tract_geoid, sum(population) AS population
        FROM census_blocks
        GROUP BY left(geoid, 11)
    ) AS block_totals
    WHERE tracts.geoid = block_totals.tract_geoid
    """
)


def read_block_centers(path) -> pd.DataFrame:
    # INTPTLAT/INTPTLON is the Census "internal point": like a center, but guaranteed to be
    # inside the block even when the block is an odd shape (a plain centroid might not be)
    blocks = gpd.read_file(
        path, columns=["GEOID20", "INTPTLAT20", "INTPTLON20"], ignore_geometry=True
    )
    return pd.DataFrame(
        {
            "geoid": blocks["GEOID20"],
            "lat": blocks["INTPTLAT20"].astype(float),
            "lon": blocks["INTPTLON20"].astype(float),
        }
    )


def fetch_block_population(api_key: str) -> pd.DataFrame:
    params = {
        "get": "P1_001N",
        "for": "block:*",
        "in": ["state:48", "county:113", "tract:*"],
        "key": api_key,
    }
    response = requests.get(
        POPULATION_API_URL, params=params, headers={"User-Agent": USER_AGENT}, timeout=120
    )
    response.raise_for_status()
    return parse_population_response(response.json())


def parse_population_response(rows: list[list[str]]) -> pd.DataFrame:
    """The API returns a header row then data rows: [P1_001N, state, county, tract, block]."""
    header, *data = rows
    table = pd.DataFrame(data, columns=header)
    return pd.DataFrame(
        {
            "geoid": table["state"] + table["county"] + table["tract"] + table["block"],
            "population": table["P1_001N"].astype(int),
        }
    )


def upsert_blocks(engine: Engine, blocks: pd.DataFrame) -> int:
    rows = blocks[["geoid", "lat", "lon", "population"]].to_dict("records")
    with engine.begin() as connection:
        connection.execute(UPSERT_BLOCK, rows)
        connection.execute(UPDATE_TRACT_POPULATION)
    return len(rows)


def load(engine: Engine) -> int:
    api_key = get_settings().census_api_key
    if not api_key:
        raise RuntimeError(
            "CENSUS_API_KEY is not set. Get a free key at "
            "https://api.census.gov/data/key_signup.html and add it to .env"
        )

    centers = read_block_centers(download(BLOCKS_URL, "tl_2020_48113_tabblock20.zip"))
    population = fetch_block_population(api_key)
    # inner join: keep blocks that have both a location and a population
    blocks = centers.merge(population, on="geoid", how="inner")
    return upsert_blocks(engine, blocks)
