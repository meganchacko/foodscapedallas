import pytest
from fastapi.testclient import TestClient

from app.main import app

# Database fixtures (test_engine, alembic_config, ...) are in the repo-root conftest.py,
# shared with the pipeline tests.


@pytest.fixture
def client():
    yield TestClient(app)
    # undo any dependency overrides a test set, so tests don't leak into each other
    app.dependency_overrides.clear()
