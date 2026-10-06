"""Food pantries from a hand-built seed file (pipeline/seeds/pantries.csv).

The North Texas Food Bank's pantry finder has no downloadable data, so pantries are entered by
hand from https://ntfb.org/get-help/. One row per pantry:

    id            short stable ID you choose, e.g. "ntfb-crossroads" (never reuse or change it)
    name          pantry name
    address       street address
    latitude      e.g. 32.7767
    longitude     e.g. -96.7970
    hours         free text, e.g. "Tue/Thu 9am-12pm"
    accepts_snap  yes / no / blank if unknown
    accepts_wic   yes / no / blank if unknown

Deleting a row and re-running the pipeline removes that pantry from the database.
"""

import csv
from pathlib import Path

from sqlalchemy import Engine

from pipeline.loaders.places import sync_places

SOURCE = "pantry_seed"
SEED_PATH = Path(__file__).resolve().parents[1] / "seeds" / "pantries.csv"


def yes_no(value: str) -> bool | None:
    value = value.strip().lower()
    if value == "yes":
        return True
    if value == "no":
        return False
    return None


def read_pantries(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as file:
        return [
            {
                "source_id": row["id"].strip(),
                "name": row["name"].strip(),
                "type": "pantry",
                "lat": float(row["latitude"]),
                "lon": float(row["longitude"]),
                "address": row["address"].strip() or None,
                "hours": row["hours"].strip() or None,
                "accepts_snap": yes_no(row["accepts_snap"]),
                "accepts_wic": yes_no(row["accepts_wic"]),
            }
            for row in csv.DictReader(file)
        ]


def load(engine: Engine) -> int:
    return sync_places(engine, SOURCE, read_pantries(SEED_PATH))
