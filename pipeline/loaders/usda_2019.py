"""USDA Food Access Research Atlas, 2019 (now called the Large Retailer Access Map).

Counts supermarkets, supercenters, and large grocery stores as food access. Published on 2010
census tract boundaries, so this loader translates ("crosswalks") it onto 2020 tracts using the
Census Bureau's 2020-to-2010 tract relationship file:

- Flags come from the 2010 tract that covers the most of the 2020 tract's land.
- Low-access population is split by land area: a 2020 tract gets each overlapping 2010 tract's
  count times the share of that 2010 tract's land it covers. This assumes people are spread
  evenly across a tract, which is an approximation.

In Dallas County, 565 of 645 2020 tracts sit at least 99% inside a single 2010 tract, so for
most tracts the translation is exact.
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

MEASURE = "usda_2019_supermarkets"

USDA_2019_URL = (
    "https://www.ers.usda.gov/media/5627/"
    "2019-large-retailer-access-map-lram-formerly-known-as-the-food-access-research-atlas-fara-data.zip"
)
RELATIONSHIP_URL = (
    "https://www2.census.gov/geo/docs/maps-data/data/rel2020/tract/tab20_tract20_tract10_natl.txt"
)


def read_usda_2019(path) -> pd.DataFrame:
    """Dallas County rows from the 2019 Atlas, keyed by 2010 tract."""
    with zipfile.ZipFile(path) as archive, archive.open("Food Access Research Atlas.csv") as file:
        atlas = pd.read_csv(
            file,
            usecols=[
                "CensusTract",
                "LowIncomeTracts",
                "LA1and10",
                "LILATracts_1And10",
                "LAPOP1_10",
            ],
            dtype={"CensusTract": str},
            encoding="latin-1",
        )
    atlas["CensusTract"] = atlas["CensusTract"].str.zfill(11)
    atlas = atlas[atlas["CensusTract"].str.startswith(DALLAS_COUNTY_FIPS)]
    return pd.DataFrame(
        {
            "geoid_2010": atlas["CensusTract"],
            "low_income": to_flag(atlas["LowIncomeTracts"]),
            "low_access": to_flag(atlas["LA1and10"]),
            "low_income_low_access": to_flag(atlas["LILATracts_1And10"]),
            "low_access_population": pd.to_numeric(atlas["LAPOP1_10"], errors="coerce"),
        }
    )


def read_relationship(path) -> pd.DataFrame:
    """Rows linking each Dallas County 2020 tract to the 2010 tracts it overlaps."""
    relationship = pd.read_csv(
        path,
        sep="|",
        usecols=[
            "GEOID_TRACT_20",
            "GEOID_TRACT_10",
            "AREALAND_TRACT_10",
            "AREALAND_PART",
            "AREAWATER_PART",
        ],
        dtype={"GEOID_TRACT_20": str, "GEOID_TRACT_10": str},
        encoding="utf-8-sig",
    )
    relationship = relationship[relationship["GEOID_TRACT_20"].str.startswith(DALLAS_COUNTY_FIPS)]
    return relationship.rename(
        columns={
            "GEOID_TRACT_20": "geoid",
            "GEOID_TRACT_10": "geoid_2010",
            "AREALAND_TRACT_10": "land_2010_total",
            "AREALAND_PART": "land_overlap",
            "AREAWATER_PART": "water_overlap",
        }
    )


def crosswalk_to_2020(usda_2010: pd.DataFrame, relationship: pd.DataFrame) -> pd.DataFrame:
    """Translate 2010-tract food access rows onto 2020 tracts (see module docstring)."""
    overlaps = relationship.merge(usda_2010, on="geoid_2010", how="inner")

    # Flags: take them from the 2010 tract with the most land overlap. Water overlap breaks
    # ties, so a 2020 tract that's all water (no land at all) still gets a parent.
    main_parent = overlaps.sort_values(
        ["geoid", "land_overlap", "water_overlap"], ascending=[True, False, False]
    ).drop_duplicates("geoid")
    flags = main_parent[["geoid", "low_income", "low_access", "low_income_low_access"]]

    # Low-access population: each 2010 tract's count, split by the share of its land in this
    # 2020 tract
    land_share = (overlaps["land_overlap"] / overlaps["land_2010_total"]).where(
        overlaps["land_2010_total"] > 0, 0
    )
    overlaps = overlaps.assign(population_part=overlaps["low_access_population"] * land_share)
    population = (
        overlaps.groupby("geoid")["population_part"]
        .sum(min_count=1)  # all parts blank -> blank, instead of 0
        .rename("low_access_population")
        .reset_index()
    )

    result = flags.merge(population, on="geoid", how="left")
    result["low_access_population"] = to_count(result["low_access_population"])
    return result[FOOD_ACCESS_COLUMNS].reset_index(drop=True)


def load(engine: Engine) -> int:
    usda_2010 = read_usda_2019(download(USDA_2019_URL, "usda_2019_food_access.zip"))
    relationship = read_relationship(download(RELATIONSHIP_URL, "tab20_tract20_tract10_natl.txt"))
    return upsert_food_access(engine, MEASURE, crosswalk_to_2020(usda_2010, relationship))
