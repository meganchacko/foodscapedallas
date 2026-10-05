from redis import Redis
from sqlalchemy import create_engine

from app.cache import get_redis
from app.db.database import get_engine
from app.main import app

# Port 1 has nothing listening on it, so connecting fails right away: a real "service is down"
UNREACHABLE_PORT = 1


def test_health_ok_when_db_and_cache_are_up(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"api": "ok", "db": "ok", "cache": "ok"}


def test_health_reports_db_down(client):
    app.dependency_overrides[get_engine] = lambda: create_engine(
        f"postgresql+psycopg://user:pass@localhost:{UNREACHABLE_PORT}/none",
        connect_args={"connect_timeout": 1},
    )

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json()["db"] == "error"


def test_health_reports_cache_down(client):
    app.dependency_overrides[get_redis] = lambda: Redis(
        host="localhost", port=UNREACHABLE_PORT, socket_connect_timeout=1
    )

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json()["cache"] == "error"
