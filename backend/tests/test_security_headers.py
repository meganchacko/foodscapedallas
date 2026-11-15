import pytest

from app.middleware import SECURITY_HEADERS


@pytest.mark.parametrize("path", ["/model-card", "/no-such-page"])
def test_every_response_has_the_security_headers(client, path):
    # Errors too: a 404 is still a response a browser might render
    response = client.get(path)

    for name, value in SECURITY_HEADERS.items():
        assert response.headers[name] == value
