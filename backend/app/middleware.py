"""Code that runs around every request."""

import time

from fastapi import Request, Response
from starlette.middleware.base import RequestResponseEndpoint


async def add_server_timing(request: Request, call_next: RequestResponseEndpoint) -> Response:
    """Add how long the server spent on the request, as a standard Server-Timing header.

    Browser dev tools show it in the Network tab ("Timing"), separate from network time.
    """
    started = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - started) * 1000
    response.headers["Server-Timing"] = f"app;dur={duration_ms:.1f}"
    return response
