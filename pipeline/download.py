import logging
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

RAW_DATA_DIR = Path(__file__).resolve().parent / "data" / "raw"

# Public data sources ask clients to identify themselves
USER_AGENT = "FoodScapeDallas/0.1 (https://github.com/meganchacko/foodscapedallas)"


def download(url: str, filename: str) -> Path:
    """Download a file once and reuse it on later runs.

    Source files (Census shapes, USDA spreadsheets) are fixed releases, so there's no need to
    fetch them again on every run. Delete pipeline/data/raw/ to force a fresh download.
    """
    path = RAW_DATA_DIR / filename
    if path.exists():
        logger.info("Using cached %s", filename)
        return path

    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Downloading %s", url)
    # Write to a temporary name first, so an interrupted download never looks like a finished file
    partial_path = path.with_suffix(path.suffix + ".partial")
    with requests.get(url, headers={"User-Agent": USER_AGENT}, stream=True, timeout=60) as response:
        response.raise_for_status()
        with open(partial_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                file.write(chunk)
    partial_path.rename(path)
    return path
