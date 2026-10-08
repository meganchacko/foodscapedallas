import pytest
from sqlalchemy import text

from app.db.database import get_engine
from app.main import app


@pytest.fixture
def seeded_client(client, clean_engine):
    """A client whose API reads a test database holding one grocery store and one pantry."""
    with clean_engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO places (name, type, geom, address, accepts_snap, source, source_id) "
                "VALUES "
                "('Corner Grocery', 'grocery', ST_GeomFromText('POINT(-96.81 32.78)', 4326), "
                " '100 Main St', true, 'test', '1'), "
                "('Hope Pantry', 'pantry', ST_GeomFromText('POINT(-96.79 32.77)', 4326), "
                " NULL, NULL, 'test', '2')"
            )
        )
    app.dependency_overrides[get_engine] = lambda: clean_engine
    return client


def test_places_returns_all_places_as_geojson_points(seeded_client):
    response = seeded_client.get("/places")

    assert response.status_code == 200
    body = response.json()
    assert body["type"] == "FeatureCollection"
    assert [feature["properties"]["name"] for feature in body["features"]] == [
        "Corner Grocery",
        "Hope Pantry",
    ]
    grocery = body["features"][0]
    assert grocery["geometry"] == {"type": "Point", "coordinates": [-96.81, 32.78]}
    assert grocery["properties"]["accepts_snap"] is True


def test_places_can_be_filtered_by_type(seeded_client):
    response = seeded_client.get("/places", params={"type": "pantry"})

    names = [feature["properties"]["name"] for feature in response.json()["features"]]
    assert names == ["Hope Pantry"]


def test_unknown_place_type_is_rejected(seeded_client):
    response = seeded_client.get("/places", params={"type": "restaurant"})

    assert response.status_code == 422
