import pytest
from fastapi.testclient import TestClient

from app.api.geocode import get_geocoder
from app.cache import create_redis, get_redis
from app.config import get_settings
from app.main import app
from app.services.geocoding import NominatimGeocoder

GEOCODE_LIMIT = 30


@pytest.fixture
def limited(monkeypatch, test_redis):
    """Rate limiting on, counting in the test Redis database, with a fake geocoder."""
    monkeypatch.setattr(get_settings(), "rate_limit_enabled", True)
    app.dependency_overrides[get_redis] = lambda: test_redis
    app.dependency_overrides[get_geocoder] = lambda: NominatimGeocoder(
        test_redis, fetch=lambda query: []
    )
    yield
    app.dependency_overrides.clear()


def search(client: TestClient):
    return client.get("/geocode", params={"q": "Fair Park"})


def test_requests_over_the_limit_get_a_429(limited):
    client = TestClient(app)
    statuses = [search(client).status_code for _ in range(GEOCODE_LIMIT + 1)]

    assert 429 not in statuses[:GEOCODE_LIMIT]  # 404s here: the fake geocoder finds nothing
    assert statuses[-1] == 429


def test_a_429_says_when_to_retry(limited):
    client = TestClient(app)
    for _ in range(GEOCODE_LIMIT):
        search(client)

    response = search(client)

    assert 0 < int(response.headers["Retry-After"]) <= 60
    assert "try again" in response.json()["detail"]


def test_each_client_has_its_own_limit(limited):
    busy = TestClient(app, client=("203.0.113.1", 50000))
    other = TestClient(app, client=("203.0.113.2", 50000))
    for _ in range(GEOCODE_LIMIT + 1):
        search(busy)

    assert search(other).status_code != 429


def test_requests_are_allowed_if_redis_is_down(limited):
    app.dependency_overrides[get_redis] = lambda: create_redis("localhost", 1)
    client = TestClient(app)

    statuses = [search(client).status_code for _ in range(GEOCODE_LIMIT + 1)]

    assert 429 not in statuses


def test_the_health_endpoint_is_not_limited(limited):
    client = TestClient(app)

    assert all(client.get("/health").status_code != 429 for _ in range(100))
