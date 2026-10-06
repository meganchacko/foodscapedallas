"""CDC PLACES adult obesity estimates for Dallas County tracts (2025 release, 2020 tracts).

PLACES estimates the share of adults with obesity in each tract from a national health survey
(BRFSS) plus census data. These are modeled estimates, not counts of real diagnoses. We query
CDC's open data API for just Dallas County instead of downloading the whole country.
"""

import pandas as pd
import requests
from sqlalchemy import Engine, text

from pipeline.download import USER_AGENT
from pipeline.loaders.food_access import DALLAS_COUNTY_FIPS

# "PLACES: Census Tract Data (GIS Friendly Format), 2025 release" on data.cdc.gov
PLACES_API_URL = "https://data.cdc.gov/resource/yjkw-uj5s.json"

UPDATE_OBESITY = text("UPDATE tracts SET obesity_pct = :obesity_pct WHERE geoid = :geoid")


def fetch_obesity() -> list[dict]:
    params = {
        "countyfips": DALLAS_COUNTY_FIPS,
        "$select": "tractfips,obesity_crudeprev",
        "$limit": 5000,  # Dallas County has 645 tracts; the API's default page size is 1000
    }
    response = requests.get(
        PLACES_API_URL, params=params, headers={"User-Agent": USER_AGENT}, timeout=60
    )
    response.raise_for_status()
    return response.json()


def parse_obesity(records: list[dict]) -> pd.DataFrame:
    table = pd.DataFrame(records, columns=["tractfips", "obesity_crudeprev"])
    obesity = pd.to_numeric(table["obesity_crudeprev"], errors="coerce")
    return pd.DataFrame({"geoid": table["tractfips"], "obesity_pct": obesity}).dropna()


def update_obesity(engine: Engine, obesity: pd.DataFrame) -> int:
    with engine.begin() as connection:
        result = connection.execute(UPDATE_OBESITY, obesity.to_dict("records"))
    return result.rowcount


def load(engine: Engine) -> int:
    return update_obesity(engine, parse_obesity(fetch_obesity()))
