from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.middleware import configure_cors

FRONTEND = "https://foodscape.example.org"


def client_allowing(origins: list[str]) -> TestClient:
    app = FastAPI()
    app.get("/ping")(lambda: {"ok": True})
    configure_cors(app, origins)
    return TestClient(app)


def test_the_configured_frontend_may_call_the_api():
    response = client_allowing([FRONTEND]).get("/ping", headers={"Origin": FRONTEND})

    assert response.headers["access-control-allow-origin"] == FRONTEND
    assert "X-Cache" in response.headers["access-control-expose-headers"]


def test_other_websites_may_not():
    response = client_allowing([FRONTEND]).get(
        "/ping", headers={"Origin": "https://evil.example.com"}
    )

    assert "access-control-allow-origin" not in response.headers


def test_allowed_origins_setting_is_a_comma_separated_list():
    settings = Settings(
        postgres_user="u",
        postgres_password="p",
        postgres_db="d",
        allowed_origins=f" {FRONTEND} , https://other.example.org,",
    )

    assert settings.cors_origins == [FRONTEND, "https://other.example.org"]


def test_passwords_with_special_characters_are_escaped():
    url = Settings(postgres_user="u", postgres_password="p@ss/word#1", postgres_db="d").database_url

    assert "p%40ss%2Fword%231" in url
    assert url.endswith("?sslmode=prefer")
