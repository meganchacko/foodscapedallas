import pytest
from sqlalchemy import text

from app.db.database import get_engine
from app.main import app

# The search point, inside the test tract (a square in downtown Dallas)
HERE = {"lat": 32.78, "lng": -96.81}
TRACT = "MULTIPOLYGON(((-96.82 32.77, -96.80 32.77, -96.80 32.79, -96.82 32.79, -96.82 32.77)))"


@pytest.fixture
def seeded_client(client, clean_engine):
    """One low-access tract and four places at known distances from HERE."""
    with clean_engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO tracts (geoid, geom) VALUES ('48113000001', ST_GeomFromText(:t, 4326))"
            ),
            {"t": TRACT},
        )
        connection.execute(
            text(
                "INSERT INTO tract_food_access (geoid, measure, low_access) "
                "VALUES ('48113000001', 'usda_2019_supermarkets', true)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO places (name, type, geom, accepts_snap, source, source_id) VALUES "
                # ~190 m east
                "('Near Grocery', 'grocery', ST_GeomFromText('POINT(-96.808 32.78)', 4326), "
                " NULL, 'test', '1'), "
                # ~470 m east
                "('Hope Pantry', 'pantry', ST_GeomFromText('POINT(-96.805 32.78)', 4326), "
                " NULL, 'test', '2'), "
                # ~1.1 km northeast, accepts SNAP
                "('SNAP Grocery', 'grocery', ST_GeomFromText('POINT(-96.80 32.786)', 4326), "
                " true, 'test', '3'), "
                # ~10 km east, outside a 1-mile radius
                "('Far Grocery', 'grocery', ST_GeomFromText('POINT(-96.70 32.78)', 4326), "
                " NULL, 'test', '4')"
            )
        )
    app.dependency_overrides[get_engine] = lambda: clean_engine
    return client


def names(response):
    return [place["name"] for place in response.json()["places"]]


def test_nearby_returns_places_within_the_radius_closest_first(seeded_client):
    response = seeded_client.get("/places/nearby", params={**HERE, "radius": 1})

    assert response.status_code == 200
    assert names(response) == ["Near Grocery", "Hope Pantry", "SNAP Grocery"]
    distances = [place["distance_m"] for place in response.json()["places"]]
    assert 150 < distances[0] < 250


def test_a_bigger_radius_finds_farther_places(seeded_client):
    response = seeded_client.get("/places/nearby", params={**HERE, "radius": 10})

    assert names(response)[-1] == "Far Grocery"


def test_nearby_can_filter_by_type_and_snap(seeded_client):
    pantries = seeded_client.get("/places/nearby", params={**HERE, "type": "pantry"})
    snap = seeded_client.get("/places/nearby", params={**HERE, "snap": "true"})

    assert names(pantries) == ["Hope Pantry"]
    assert names(snap) == ["SNAP Grocery"]


def test_nearby_reports_the_tract_and_whether_it_is_low_access(seeded_client):
    location = seeded_client.get("/places/nearby", params=HERE).json()["location"]

    assert location["in_dallas_county"] is True
    assert location["tract_geoid"] == "48113000001"
    assert location["low_access"] is True


def test_point_outside_dallas_county_is_flagged(seeded_client):
    fort_worth = {"lat": 32.75, "lng": -97.33}

    location = seeded_client.get("/places/nearby", params=fort_worth).json()["location"]

    assert location["in_dallas_county"] is False
    assert location["low_access"] is None


@pytest.mark.parametrize(
    "params",
    [
        {"lat": 200, "lng": -96.81},  # latitude out of range
        {"lat": 32.78, "lng": -96.81, "radius": 50},  # radius too large
        {"lat": 32.78, "lng": -96.81, "radius": 0},  # radius must be positive
        {"lat": "downtown", "lng": -96.81},  # not a number
        {"lng": -96.81},  # missing lat
    ],
)
def test_bad_input_is_rejected(seeded_client, params):
    assert seeded_client.get("/places/nearby", params=params).status_code == 422
