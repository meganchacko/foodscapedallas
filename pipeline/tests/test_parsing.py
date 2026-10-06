"""Turning raw source data into rows, without touching the network or the database."""

import pandas as pd

from pipeline.loaders.cdc_places import parse_obesity
from pipeline.loaders.census_blocks import parse_population_response
from pipeline.loaders.food_access import to_count, to_flag
from pipeline.loaders.osm_places import parse_element
from pipeline.loaders.pantries import read_pantries


def test_usda_flags_and_counts_turn_blanks_into_none():
    assert to_flag(pd.Series(["1", "0", "", None])).tolist() == [True, False, None, None]
    assert to_count(pd.Series([2.6, None, "5"])).tolist() == [3, None, 5]


def test_census_population_response_builds_block_geoids():
    rows = [
        ["P1_001N", "state", "county", "tract", "block"],
        ["42", "48", "113", "000100", "1001"],
    ]

    blocks = parse_population_response(rows)

    assert blocks.to_dict("records") == [{"geoid": "481130001001001", "population": 42}]


def test_cdc_obesity_skips_tracts_without_an_estimate():
    records = [
        {"tractfips": "48113000100", "obesity_crudeprev": "27.6"},
        {"tractfips": "48113980000"},  # unpopulated tract: no estimate
    ]

    obesity = parse_obesity(records)

    assert obesity.to_dict("records") == [{"geoid": "48113000100", "obesity_pct": 27.6}]


def test_osm_node_becomes_a_grocery_place():
    element = {
        "type": "node",
        "id": 123,
        "lat": 32.78,
        "lon": -96.80,
        "tags": {
            "shop": "supermarket",
            "name": "Corner Grocery",
            "addr:housenumber": "100",
            "addr:street": "Main St",
            "addr:city": "Dallas",
            "opening_hours": "Mo-Su 07:00-22:00",
            "payment:snap": "yes",
        },
    }

    place = parse_element(element)

    assert place == {
        "source_id": "node/123",
        "name": "Corner Grocery",
        "type": "grocery",
        "lat": 32.78,
        "lon": -96.80,
        "address": "100 Main St, Dallas",
        "hours": "Mo-Su 07:00-22:00",
        "accepts_snap": True,
        "accepts_wic": None,
    }


def test_osm_building_uses_its_center_point():
    element = {
        "type": "way",
        "id": 9,
        "center": {"lat": 32.7, "lon": -96.9},
        "tags": {"amenity": "marketplace", "name": "Farmers Market"},
    }

    place = parse_element(element)

    assert (place["source_id"], place["type"], place["lat"]) == ("way/9", "farmers_market", 32.7)


def test_osm_place_without_a_name_is_skipped():
    element = {"type": "node", "id": 1, "lat": 32.7, "lon": -96.9, "tags": {"shop": "supermarket"}}

    assert parse_element(element) is None


def test_pantry_csv_rows_become_places(tmp_path):
    seed = tmp_path / "pantries.csv"
    seed.write_text(
        "id,name,address,latitude,longitude,hours,accepts_snap,accepts_wic\n"
        "p1,Hope Pantry,1 Elm St,32.77,-96.79,Tue 9-12,,yes\n"
    )

    [pantry] = read_pantries(seed)

    assert pantry["source_id"] == "p1"
    assert pantry["type"] == "pantry"
    assert (pantry["lat"], pantry["lon"]) == (32.77, -96.79)
    assert pantry["accepts_snap"] is None  # blank means unknown
    assert pantry["accepts_wic"] is True
