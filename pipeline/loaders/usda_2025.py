"""USDA Food Access Research Atlas, 2025 (the SNAP-authorized Retailer Access Map).

Counts any SNAP-authorized store as food access, including convenience and dollar stores, so far
fewer tracts are flagged than under the 2019 supermarket-based definition. Already on 2020
census tracts, so no translation is needed.

We use the straight-line distance version, matching how the 2019 data was measured.
"""

import zipfile

import pandas as pd
from sqlalchemy import Engine

from pipeline.download import download
from pipeline.loaders.food_access import (
    DALLAS_COUNTY_FIPS,
    FOOD_ACCESS_COLUMNS,
    to_count,
    to_flag,
    upsert_food_access,
)

MEASURE = "usda_2025_snap_retailers"

USDA_2025_URL = (
    "https://www.ers.usda.gov/media/29395/2025-snap-authorized-retailer-access-map-sram-data.zip"
)


def read_dallas_rows(archive: zipfile.ZipFile, filename: str, columns: list[str]) -> pd.DataFrame:
    with archive.open(filename) as file:
        table = pd.read_csv(file, usecols=columns, dtype={"CensusTract20": str}, encoding="latin-1")
    table["CensusTract20"] = table["CensusTract20"].str.zfill(11)
    return table[table["CensusTract20"].str.startswith(DALLAS_COUNTY_FIPS)]


def read_usda_2025(path) -> pd.DataFrame:
    # The low-income flag is in the general tract file; low-access measures are in the
    # straight-line distance file
    with zipfile.ZipFile(path) as archive:
        general = read_dallas_rows(
            archive,
            "SRAM General Tract Characteristics Data.csv",
            ["CensusTract20", "LowIncomeTracts"],
        )
        distance = read_dallas_rows(
            archive,
            "SRAM Straight Line Distance Data.csv",
            [
                "CensusTract20",
                "SD_SRAM_LA1and10",
                "SD_SRAM_LILATracts_1And10",
                "SD_SRAM_LAPOP1_10",
            ],
        )
    atlas = general.merge(distance, on="CensusTract20", how="inner")
    food_access = pd.DataFrame(
        {
            "geoid": atlas["CensusTract20"],
            "low_income": to_flag(atlas["LowIncomeTracts"]),
            "low_access": to_flag(atlas["SD_SRAM_LA1and10"]),
            "low_income_low_access": to_flag(atlas["SD_SRAM_LILATracts_1And10"]),
            "low_access_population": to_count(atlas["SD_SRAM_LAPOP1_10"]),
        }
    )
    return food_access[FOOD_ACCESS_COLUMNS].reset_index(drop=True)


def load(engine: Engine) -> int:
    return upsert_food_access(
        engine, MEASURE, read_usda_2025(download(USDA_2025_URL, "usda_2025_food_access.zip"))
    )
