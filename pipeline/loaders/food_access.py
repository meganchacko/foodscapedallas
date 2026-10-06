"""Shared pieces for the USDA food access loaders (2019 and 2025 definitions)."""

import pandas as pd
from sqlalchemy import Engine, text

DALLAS_COUNTY_FIPS = "48113"

# Columns every food access loader produces, one row per 2020 tract
FOOD_ACCESS_COLUMNS = [
    "geoid",
    "low_income",
    "low_access",
    "low_income_low_access",
    "low_access_population",
]

UPSERT_FOOD_ACCESS = text(
    """
    INSERT INTO tract_food_access
        (geoid, measure, low_income, low_access, low_income_low_access, low_access_population)
    VALUES
        (:geoid, :measure, :low_income, :low_access, :low_income_low_access,
         :low_access_population)
    ON CONFLICT (geoid, measure) DO UPDATE SET
        low_income = EXCLUDED.low_income,
        low_access = EXCLUDED.low_access,
        low_income_low_access = EXCLUDED.low_income_low_access,
        low_access_population = EXCLUDED.low_access_population
    """
)


# Blank values must reach the database as None (SQL NULL). Plain pandas stores blanks in number
# columns as NaN, which is a float, so these use pandas' nullable "boolean" and "Int64" types
# and then swap the missing markers for None.


def to_flag(values: pd.Series) -> pd.Series:
    """USDA flags are 1/0; blank means "not available". Convert to True/False/None."""
    flags = pd.to_numeric(values, errors="coerce").astype("boolean")
    return flags.astype(object).where(flags.notna(), None)


def to_count(values: pd.Series) -> pd.Series:
    """Round to whole people; blank stays None."""
    counts = pd.to_numeric(values, errors="coerce").round().astype("Int64")
    return counts.astype(object).where(counts.notna(), None)


def upsert_food_access(engine: Engine, measure: str, food_access: pd.DataFrame) -> int:
    rows = food_access[FOOD_ACCESS_COLUMNS].assign(measure=measure).to_dict("records")
    with engine.begin() as connection:
        connection.execute(UPSERT_FOOD_ACCESS, rows)
    return len(rows)
