import pytest
from sqlalchemy import text

from app.db.database import get_engine
from app.main import app

# Two side-by-side squares in downtown Dallas, standing in for tracts
WEST_TRACT = (
    "MULTIPOLYGON(((-96.82 32.77, -96.80 32.77, -96.80 32.79, -96.82 32.79, -96.82 32.77)))"
)
EAST_TRACT = (
    "MULTIPOLYGON(((-96.80 32.77, -96.78 32.77, -96.78 32.79, -96.80 32.79, -96.80 32.77)))"
)


@pytest.fixture
def seeded_client(client, clean_engine):
    """A client whose API reads a test database holding two tracts and one grocery store."""
    with clean_engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO tracts (geoid, geom, population, obesity_pct) VALUES "
                "('48113000001', ST_GeomFromText(:west, 4326), 1000, 40.0), "
                "('48113000002', ST_GeomFromText(:east, 4326), 2000, 30.0)"
            ),
            {"west": WEST_TRACT, "east": EAST_TRACT},
        )
        connection.execute(
            text(
                "INSERT INTO tract_food_access "
                "(geoid, measure, low_income, low_access, low_income_low_access, "
                " low_access_population) VALUES "
                "('48113000001', 'usda_2019_supermarkets', true, true, true, 300), "
                "('48113000001', 'usda_2025_snap_retailers', true, false, false, 0)"
            )
        )
        # A grocery store inside the west tract
        connection.execute(
            text(
                "INSERT INTO places (name, type, geom, source, source_id) VALUES "
                "('Corner Grocery', 'grocery', ST_GeomFromText('POINT(-96.81 32.78)', 4326), "
                "'test', '1')"
            )
        )
    app.dependency_overrides[get_engine] = lambda: clean_engine
    return client


def features_by_geoid(response):
    return {feature["properties"]["geoid"]: feature for feature in response.json()["features"]}


def test_tracts_returns_a_geojson_feature_collection(seeded_client):
    response = seeded_client.get("/tracts")

    assert response.status_code == 200
    body = response.json()
    assert body["type"] == "FeatureCollection"
    assert len(body["features"]) == 2
    for feature in body["features"]:
        assert feature["type"] == "Feature"
        assert feature["geometry"]["type"] == "MultiPolygon"


def test_tract_properties_include_stats_and_both_food_access_definitions(seeded_client):
    west = features_by_geoid(seeded_client.get("/tracts"))["48113000001"]["properties"]

    assert west["population"] == 1000
    assert west["obesity_pct"] == 40.0
    assert west["food_access"]["usda_2019_supermarkets"]["low_access"] is True
    assert west["food_access"]["usda_2019_supermarkets"]["low_access_population"] == 300
    assert west["food_access"]["usda_2025_snap_retailers"]["low_access"] is False


def test_tract_without_food_access_data_has_an_empty_object(seeded_client):
    east = features_by_geoid(seeded_client.get("/tracts"))["48113000002"]["properties"]

    assert east["food_access"] == {}


def test_priority_area_follows_the_selected_food_access_definition(seeded_client):
    body = seeded_client.get("/tracts").json()
    west = features_by_geoid(seeded_client.get("/tracts"))["48113000001"]["properties"]

    # median of 40 and 30 is 35; the west tract (40%) is above it
    assert body["obesity_median_pct"] == 35.0
    assert west["food_access"]["usda_2019_supermarkets"]["priority_area"] is True  # low access
    assert west["food_access"]["usda_2025_snap_retailers"]["priority_area"] is False


def test_nearest_grocery_distance_is_in_meters(seeded_client):
    tracts = features_by_geoid(seeded_client.get("/tracts"))
    west_distance = tracts["48113000001"]["properties"]["nearest_grocery_m"]
    east_distance = tracts["48113000002"]["properties"]["nearest_grocery_m"]

    # The store is inside the west tract, so it's close to the west tract's inner point and
    # roughly one tract-width (~1.9 km at this latitude) from the east tract's
    assert west_distance < 500
    assert 1500 < east_distance < 2500
