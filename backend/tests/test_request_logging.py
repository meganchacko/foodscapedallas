import json
import logging

import pytest

from app.api.geocode import get_geocoder
from app.logging_config import JsonFormatter
from app.main import app
from app.services.geocoding import NominatimGeocoder
from tests.test_health_check import ANSWERS


@pytest.fixture
def request_logs(caplog):
    """The request log lines, formatted exactly as they'd be written."""
    caplog.set_level(logging.INFO, logger="app.requests")
    formatter = JsonFormatter()

    def lines():
        return [formatter.format(r) for r in caplog.records if r.name == "app.requests"]

    return lines


def test_each_request_is_one_json_line_with_the_key_fields(client, request_logs):
    response = client.get("/health")

    [line] = request_logs()
    entry = json.loads(line)
    assert entry["message"] == "request"
    assert entry["method"] == "GET"
    assert entry["path"] == "/health"
    assert entry["status"] == response.status_code
    assert entry["duration_ms"] >= 0
    assert entry["request_id"] == response.headers["X-Request-ID"]


def test_a_valid_incoming_request_id_is_kept(client):
    response = client.get("/health", headers={"X-Request-ID": "trace-12345678"})

    assert response.headers["X-Request-ID"] == "trace-12345678"


def test_a_suspicious_request_id_is_replaced(client):
    response = client.get("/health", headers={"X-Request-ID": 'bad" injected log text'})

    assert "injected" not in response.headers["X-Request-ID"]


def test_searched_addresses_never_reach_the_logs(client, test_redis, request_logs):
    app.dependency_overrides[get_geocoder] = lambda: NominatimGeocoder(
        test_redis, fetch=lambda query: []
    )

    client.get("/geocode", params={"q": "742 Evergreen Terrace"})

    [line] = request_logs()
    assert json.loads(line)["path"] == "/geocode"
    assert "Evergreen" not in line


def test_health_check_answers_never_reach_the_logs(client, request_logs):
    client.post("/health-check", json={**ANSWERS, "transportation": "Motorbike"})

    logged = "\n".join(request_logs())
    assert "/health-check" in logged
    assert "Motorbike" not in logged and "family_history" not in logged
