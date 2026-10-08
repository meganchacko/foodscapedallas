import pandas as pd

from pipeline.loaders.snap_retailers import (
    farmers_markets,
    match_snap_stores,
    name_key,
    similar_names,
)

# A point in Dallas, and two offsets: ~100 m and ~1 km east
LAT, LNG = 32.78, -96.80
LNG_100M_EAST = -96.7989
LNG_1KM_EAST = -96.7893


def osm(name):
    return pd.DataFrame([{"id": 1, "name": name, "lat": LAT, "lng": LNG}])


def snap(name, lng):
    return pd.DataFrame([{"Store Name": name, "Latitude": str(LAT), "Longitude": str(lng)}])


def test_name_key_drops_store_numbers_punctuation_and_generic_words():
    assert name_key("Fiesta Mart #57") == name_key("FIESTA MART 57") == "fiestamart"
    assert name_key("Joe V's Smart Shop") == "joevssmartshop"


def test_similar_names():
    assert similar_names("Tom Thumb", "TOM THUMB 1973")
    assert similar_names("Food Land", "Foodland Markets 51")
    assert not similar_names("Kroger", "Dollar General 3277")
    assert not similar_names("Supermarket", "Grocery Store")  # nothing left to compare


def test_same_name_nearby_is_a_match():
    assert match_snap_stores(osm("Kroger"), snap("KROGER #589", LNG_100M_EAST)) == {1}


def test_different_store_nearby_is_not_a_match():
    assert match_snap_stores(osm("Kroger"), snap("Family Dollar 1866", LNG_100M_EAST)) == set()


def test_same_name_far_away_is_not_a_match():
    assert match_snap_stores(osm("Kroger"), snap("KROGER #589", LNG_1KM_EAST)) == set()


def retailer(record_id, name, store_type="Farmers' Market"):
    return {
        "Record ID": record_id,
        "Store Name": f"{name}  ",
        "Store Type": store_type,
        "Street Number": "1010",
        "Street Name": "S Pearl Expy",
        "City": "Dallas",
        "Zip Code": "75201",
        "Latitude": "32.7781",
        "Longitude": "-96.7900",
    }


def test_farmers_markets_become_places_and_skip_excluded_ids():
    retailers = pd.DataFrame(
        [
            retailer("1", "Dallas Farmers Market"),
            retailer("2", "Corner Store", store_type="Convenience Store"),
            retailer("1463642", "Candy Girl Chicks & Livestock"),
        ]
    )

    [market] = farmers_markets(retailers)

    assert market["name"] == "Dallas Farmers Market"
    assert market["type"] == "farmers_market"
    assert market["address"] == "1010 S Pearl Expy, Dallas 75201"
    assert market["accepts_snap"] is True
