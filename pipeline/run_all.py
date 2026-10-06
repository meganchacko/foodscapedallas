"""Load all Dallas County data into the database, in order.

Run from the repo root:  python -m pipeline.run_all

Every loader is idempotent (it upserts on a stable key), so running this again updates
existing rows instead of creating duplicates.
"""

import logging
import time

from pipeline.db import create_db_engine
from pipeline.loaders import (
    cdc_places,
    census_blocks,
    osm_places,
    pantries,
    tracts,
    usda_2019,
    usda_2025,
)

logger = logging.getLogger("pipeline")

# (name, load function) in the order they must run: later steps need earlier ones' rows
STEPS = [
    ("tracts", tracts.load),
    ("census_blocks", census_blocks.load),
    ("usda_2019", usda_2019.load),
    ("usda_2025", usda_2025.load),
    ("cdc_places", cdc_places.load),
    ("osm_places", osm_places.load),
    ("pantries", pantries.load),
]


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    engine = create_db_engine()

    for name, load in STEPS:
        started = time.perf_counter()
        row_count = load(engine)
        elapsed = time.perf_counter() - started
        logger.info("%s: %d rows (%.1fs)", name, row_count, elapsed)

    engine.dispose()


if __name__ == "__main__":
    main()
