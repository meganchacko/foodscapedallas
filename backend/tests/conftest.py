import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    yield TestClient(app)
    # undo any dependency overrides a test set, so tests don't leak into each other
    app.dependency_overrides.clear()
