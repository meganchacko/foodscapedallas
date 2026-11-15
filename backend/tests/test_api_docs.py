from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import docs_options


def test_docs_are_served_by_default(client):
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").status_code == 200


def test_docs_can_be_turned_off():
    # As in production (API_DOCS_ENABLED=false)
    client = TestClient(FastAPI(**docs_options(False)))

    for path in ["/docs", "/redoc", "/openapi.json"]:
        assert client.get(path).status_code == 404
