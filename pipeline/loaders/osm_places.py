"""Grocery stores and farmers markets in Dallas County from OpenStreetMap (Overpass API)."""

import logging
import time

import requests
from sqlalchemy import Engine

from pipeline.download import USER_AGENT
from pipeline.loaders.places import sync_places

logger = logging.getLogger(__name__)

SOURCE = "osm"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Dallas County's extent (south, west, north, east) plus a small margin. The rectangle also
# covers bits of neighboring counties; sync_places keeps only places inside a Dallas tract.
DALLAS_COUNTY_BBOX = (32.53, -97.05, 33.00, -96.50)

# Grocery: supermarkets and greengrocers (produce stores). Convenience stores aren't included,
# matching the 2019 USDA supermarket-based definition.
# Farmers markets: in Dallas, most amenity=marketplace entries are flea markets or shops, so we
# only take marketplaces with "farmers" in the name.
# "out center" gives buildings (ways) and multi-part shapes (relations) a single center point.
OVERPASS_QUERY = """
[out:json][timeout:120][bbox:{south},{west},{north},{east}];
(
  nwr["shop"="supermarket"];
  nwr["shop"="greengrocer"];
  nwr["amenity"="marketplace"]["name"~"farmers",i];
);
out center tags;
"""

# OpenStreetMap places tagged shop=supermarket that aren't grocery stores (volunteer tagging
# mistakes), found by checking stores that didn't match USDA's SNAP list. Better long-term fix:
# correct the tags on openstreetmap.org, then remove them from this list.
EXCLUDED_ELEMENTS = {
    "node/12520457070": "M|C Criminal Law (a law office)",
    "node/12137269892": "Charter Furniture Clearance Outlet (a furniture store)",
    "node/12140021739": "Next Exit Logistics (a logistics company)",
}

MAX_ATTEMPTS = 3
RETRY_WAIT_SECONDS = 30


def fetch_elements() -> list[dict]:
    south, west, north, east = DALLAS_COUNTY_BBOX
    query = OVERPASS_QUERY.format(south=south, west=west, north=north, east=east)

    # Overpass is a free, shared server: it answers 429 (too many requests) or 504 (busy) when
    # overloaded, so wait and retry a few times before giving up
    for attempt in range(1, MAX_ATTEMPTS + 1):
        response = requests.post(
            OVERPASS_URL, data={"data": query}, headers={"User-Agent": USER_AGENT}, timeout=180
        )
        if response.status_code not in (429, 504) or attempt == MAX_ATTEMPTS:
            break
        logger.warning(
            "Overpass returned %s, retrying in %ss", response.status_code, RETRY_WAIT_SECONDS
        )
        time.sleep(RETRY_WAIT_SECONDS)

    response.raise_for_status()
    return response.json()["elements"]


def payment_flag(tags: dict, *keys: str) -> bool | None:
    """OSM payment tags are "yes"/"no"; anything else (usually missing) means unknown."""
    for key in keys:
        if tags.get(key) == "yes":
            return True
        if tags.get(key) == "no":
            return False
    return None


def format_address(tags: dict) -> str | None:
    street = " ".join(
        part for part in (tags.get("addr:housenumber"), tags.get("addr:street")) if part
    )
    parts = [part for part in (street, tags.get("addr:city"), tags.get("addr:postcode")) if part]
    return ", ".join(parts) or None


def parse_element(element: dict) -> dict | None:
    """Turn one Overpass result into a place dict, or None if it can't be used."""
    tags = element.get("tags", {})
    name = tags.get("name")
    if not name:
        return None  # a pin with no name isn't useful to someone looking for food

    # Points (nodes) have lat/lon; buildings and areas (ways, relations) have a center
    location = element if "lat" in element else element.get("center")
    if not location:
        return None

    return {
        "source_id": f"{element['type']}/{element['id']}",  # e.g. "way/123456", stable in OSM
        "name": name,
        "type": "farmers_market" if tags.get("amenity") == "marketplace" else "grocery",
        "lat": location["lat"],
        "lon": location["lon"],
        "address": format_address(tags),
        "hours": tags.get("opening_hours"),  # OSM's format, e.g. "Mo-Su 07:00-22:00"
        "accepts_snap": payment_flag(tags, "payment:snap", "payment:ebt"),
        "accepts_wic": payment_flag(tags, "payment:wic"),
    }


def usable_places(elements: list[dict]) -> list[dict]:
    places = [place for place in map(parse_element, elements) if place is not None]
    return [place for place in places if place["source_id"] not in EXCLUDED_ELEMENTS]


def load(engine: Engine) -> int:
    elements = fetch_elements()
    places = usable_places(elements)
    logger.info("OSM returned %d elements; %d usable", len(elements), len(places))
    return sync_places(engine, SOURCE, places)
