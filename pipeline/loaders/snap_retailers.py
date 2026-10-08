"""USDA SNAP Retailer Locator data: which stores accept SNAP, plus SNAP-authorized farmers markets.

USDA publishes every store authorized to accept SNAP (food stamps), with its location and
authorization dates. A store with no end date is currently authorized. This loader:

1. Marks OpenStreetMap grocery stores that match a current SNAP store as accepts_snap = true.
   A match needs a SNAP store within MATCH_DISTANCE_M *and* a similar name. Both are needed:
   OSM usually places a big store at its building's center while USDA places it at its street
   address, often 100-200 m apart, and shopping centers put different stores side by side.
   Stores without a match stay "unknown" (None), not "no": a miss can be our matching, not
   the store.
2. Adds SNAP-authorized farmers markets as places (OpenStreetMap has almost none in Dallas).
"""

import difflib
import logging
import re
import zipfile

import geopandas as gpd
import pandas as pd
from sqlalchemy import Engine, text

from pipeline.download import download
from pipeline.loaders.places import sync_places

logger = logging.getLogger(__name__)

SNAP_URL = (
    "https://www.fns.usda.gov/sites/default/files/resource-files/"
    "snap-retailer-locator-data2005-2025.zip"
)
SOURCE = "usda_snap"

# Chosen by testing on Dallas data: 250 m matched 242 of 290 OSM grocery stores with names that
# agree; 150 m missed many large stores whose building center is far from their street address
MATCH_DISTANCE_M = 250

# Meters-based coordinate system for Dallas (UTM zone 14N), so buffers are in meters
METERS_CRS = "EPSG:32614"

# Listed as a SNAP "Farmers' Market" but it's a livestock seller, not a market
EXCLUDED_RECORD_IDS = {"1463642"}  # Candy Girl Chicks & Livestock

# Words that don't help tell stores apart ("Fiesta Mart" vs "Fiesta Mart Supermarket")
GENERIC_WORDS = {
    "the", "store", "stores", "inc", "llc", "co", "market", "markets", "supermarket",
    "food", "foods", "grocery", "neighborhood", "supercenter",
}  # fmt: skip

OSM_GROCERY_QUERY = text(
    "SELECT id, name, ST_X(geom) AS lng, ST_Y(geom) AS lat FROM places "
    "WHERE source = 'osm' AND type = 'grocery'"
)
# Set every OSM grocery store's SNAP flag in one statement: true if matched, unknown otherwise.
# Recomputing all of them each run keeps the loader idempotent as stores gain or lose SNAP.
UPDATE_SNAP_FLAGS = text(
    "UPDATE places "
    "SET accepts_snap = CASE WHEN id = ANY(:matched_ids) THEN true ELSE NULL END "
    "WHERE source = 'osm' AND type = 'grocery'"
)


def read_current_dallas_retailers(path) -> pd.DataFrame:
    """Dallas County stores that are authorized right now (no end date)."""
    with zipfile.ZipFile(path) as archive, archive.open(archive.namelist()[0]) as file:
        retailers = pd.read_csv(file, dtype=str, encoding="utf-8-sig").fillna("")
    in_dallas = (retailers["State"] == "TX") & (
        retailers["County"].str.strip().str.upper() == "DALLAS"
    )
    current = retailers["End Date"].str.strip() == ""
    return retailers[in_dallas & current].reset_index(drop=True)


def name_key(name: str) -> str:
    """'Fiesta Mart #57' -> 'fiestamart': lowercase letters only, generic words dropped."""
    words = re.sub(r"[^a-z ]", " ", name.lower().replace("'", "")).split()
    return "".join(word for word in words if word not in GENERIC_WORDS)


def similar_names(a: str, b: str) -> bool:
    key_a, key_b = name_key(a), name_key(b)
    if not key_a or not key_b:
        return False
    # "tomthumb" is in "tomthumb" (store numbers are already dropped); "koMart" ~ "komartplace"
    if key_a in key_b or key_b in key_a:
        return True
    return difflib.SequenceMatcher(None, key_a, key_b).ratio() >= 0.85


def match_snap_stores(osm_stores: pd.DataFrame, snap_stores: pd.DataFrame) -> set[int]:
    """IDs of OSM stores with a similarly named SNAP store within MATCH_DISTANCE_M.

    osm_stores needs id, name, lat, lng; snap_stores needs Store Name, Latitude, Longitude.
    """
    if osm_stores.empty or snap_stores.empty:
        return set()
    osm = gpd.GeoDataFrame(
        osm_stores, geometry=gpd.points_from_xy(osm_stores["lng"], osm_stores["lat"]), crs=4326
    ).to_crs(METERS_CRS)
    snap = gpd.GeoDataFrame(
        snap_stores[["Store Name"]],
        geometry=gpd.points_from_xy(
            snap_stores["Longitude"].astype(float), snap_stores["Latitude"].astype(float)
        ),
        crs=4326,
    ).to_crs(METERS_CRS)

    # Pair each OSM store with every SNAP store within the match distance, then keep the pairs
    # whose names agree
    snap["geometry"] = snap.buffer(MATCH_DISTANCE_M)
    pairs = gpd.sjoin(osm, snap, predicate="within")
    if pairs.empty:
        return set()
    matched = pairs[
        [similar_names(a, b) for a, b in zip(pairs["name"], pairs["Store Name"], strict=True)]
    ]
    return set(matched["id"].astype(int))


def join_parts(*parts: str, separator: str = " ") -> str:
    return separator.join(part.strip() for part in parts if part.strip())


def farmers_markets(retailers: pd.DataFrame) -> list[dict]:
    markets = retailers[
        (retailers["Store Type"] == "Farmers' Market")
        & ~retailers["Record ID"].isin(EXCLUDED_RECORD_IDS)
    ]
    return [
        {
            "source_id": market["Record ID"],
            "name": market["Store Name"].strip(),
            "type": "farmers_market",
            "lat": float(market["Latitude"]),
            "lon": float(market["Longitude"]),
            "address": join_parts(
                join_parts(market["Street Number"], market["Street Name"]),
                join_parts(market["City"], market["Zip Code"]),
                separator=", ",
            )
            or None,
            "hours": None,  # not in the USDA data; many markets are seasonal
            "accepts_snap": True,
            "accepts_wic": None,
        }
        for market in markets.to_dict("records")
    ]


def load(engine: Engine) -> int:
    retailers = read_current_dallas_retailers(download(SNAP_URL, "usda_snap_retailers.zip"))

    with engine.connect() as connection:
        osm_stores = pd.DataFrame(connection.execute(OSM_GROCERY_QUERY).mappings().all())
    matched_ids = match_snap_stores(osm_stores, retailers)
    with engine.begin() as connection:
        connection.execute(UPDATE_SNAP_FLAGS, {"matched_ids": list(matched_ids)})

    market_count = sync_places(engine, SOURCE, farmers_markets(retailers))
    logger.info(
        "Marked %d of %d OSM grocery stores as accepting SNAP; loaded %d farmers markets",
        len(matched_ids),
        len(osm_stores),
        market_count,
    )
    return len(matched_ids) + market_count
