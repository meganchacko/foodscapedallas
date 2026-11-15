import pytest
from fastapi.testclient import TestClient

from app.api.geocode import get_geocoder
from app.cache import create_redis, get_redis
from app.config import get_settings
from app.main import app
from app.services.geocoding import NominatimGeocoder

GEOCODE_LIMIT = 10


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


def test_the_health_endpoint_allows_azures_probe_but_is_limited(limited):
    client = TestClient(app)
    statuses = [client.get("/health").status_code for _ in range(61)]

    assert 429 not in statuses[:60]  # the readiness probe only needs 6 a minute
    assert statuses[-1] == 429


@pytest.fixture
def behind_one_proxy(monkeypatch):
    """Like production: one proxy (Azure's ingress) appends the client's IP to X-Forwarded-For."""
    monkeypatch.setattr(get_settings(), "trusted_proxy_hops", 1)


def search_via_proxy(client: TestClient, forwarded_for: str):
    return client.get(
        "/geocode", params={"q": "Fair Park"}, headers={"X-Forwarded-For": forwarded_for}
    )


def test_a_faked_forwarded_for_does_not_reset_the_limit(limited, behind_one_proxy):
    client = TestClient(app)
    # The attacker puts a new made-up IP first each time; the proxy appends their real one
    statuses = [
        search_via_proxy(client, f"10.0.0.{n}, 198.51.100.7").status_code
        for n in range(GEOCODE_LIMIT + 1)
    ]

    assert statuses[-1] == 429


def test_clients_behind_the_proxy_are_told_apart(limited, behind_one_proxy):
    client = TestClient(app)
    for _ in range(GEOCODE_LIMIT + 1):
        search_via_proxy(client, "198.51.100.7")

    assert search_via_proxy(client, "198.51.100.8").status_code != 429


def test_forwarded_for_is_ignored_without_a_proxy(limited):
    # trusted_proxy_hops is 0: anyone could send the header, so it must not pick the client
    client = TestClient(app)
    statuses = [
        search_via_proxy(client, f"198.51.100.{n}").status_code for n in range(GEOCODE_LIMIT + 1)
    ]

    assert statuses[-1] == 429
