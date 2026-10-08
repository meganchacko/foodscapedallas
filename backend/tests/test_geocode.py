import pytest
import requests

from app.api.geocode import get_geocoder
from app.main import app
from app.services.geocoding import NominatimGeocoder, normalize, parse_nominatim

# Shaped like a real Nominatim jsonv2 result (trimmed)
CITY_HALL = [
    {
        "lat": "32.7763",
        "lon": "-96.7969",
        "display_name": "Dallas City Hall, 1500, Marilla Street, Dallas, Texas, 75201",
    }
]


class FakeNominatim:
    """Stands in for the network call and counts how often it's used."""

    def __init__(self, results=CITY_HALL, error=None):
        self.results = results
        self.error = error
        self.calls = 0

    def __call__(self, query):
        self.calls += 1
        if self.error:
            raise self.error
        return self.results


@pytest.fixture
def client_with(client, test_redis):
    """Returns a function that points the API's geocoder at a given fake."""

    def use(fake):
        app.dependency_overrides[get_geocoder] = lambda: NominatimGeocoder(test_redis, fetch=fake)
        return client

    return use


def test_parse_nominatim_reads_coordinates_from_strings():
    result = parse_nominatim(CITY_HALL)

    assert (result.lat, result.lng) == (32.7763, -96.7969)
    assert parse_nominatim([]) is None


def test_queries_that_differ_only_in_case_or_spacing_are_the_same():
    assert normalize("  1500  Marilla St ") == normalize("1500 marilla st")


def test_geocode_returns_coordinates(client_with):
    response = client_with(FakeNominatim()).get("/geocode", params={"q": "1500 Marilla St"})

    assert response.status_code == 200
    assert response.json()["lat"] == 32.7763


def test_repeated_search_is_served_from_the_cache(client_with):
    fake = FakeNominatim()
    client = client_with(fake)

    client.get("/geocode", params={"q": "1500 Marilla St"})
    second = client.get("/geocode", params={"q": "1500 marilla st"})

    assert second.status_code == 200
    assert fake.calls == 1  # the second search never reached Nominatim


def test_no_match_is_a_404_and_is_cached(client_with):
    fake = FakeNominatim(results=[])
    client = client_with(fake)

    first = client.get("/geocode", params={"q": "zzzz not a place"})
    second = client.get("/geocode", params={"q": "zzzz not a place"})

    assert first.status_code == second.status_code == 404
    assert fake.calls == 1


def test_nominatim_failure_is_a_503(client_with):
    fake = FakeNominatim(error=requests.ConnectionError("down"))

    response = client_with(fake).get("/geocode", params={"q": "1500 Marilla St"})

    assert response.status_code == 503


def test_too_short_query_is_rejected(client_with):
    assert client_with(FakeNominatim()).get("/geocode", params={"q": "ab"}).status_code == 422
