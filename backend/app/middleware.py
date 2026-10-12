"""Code that runs around every request."""

import logging
import re
import time
import uuid

from fastapi import Request, Response
from starlette.middleware.base import RequestResponseEndpoint

logger = logging.getLogger("app.requests")

# Accept a caller's request ID (e.g. from a load balancer) only if it looks like an ID, so
# arbitrary text can't be injected into the logs
VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9-]{8,64}$")


async def observe_request(request: Request, call_next: RequestResponseEndpoint) -> Response:
    """Time the request, give it an ID, and log one line about it.

    Privacy: only the path is logged (e.g. /geocode), never the query string (which holds the
    searched address) or the body (which holds health check answers), and never the IP.
    """
    incoming_id = request.headers.get("X-Request-ID", "")
    request_id = incoming_id if VALID_REQUEST_ID.match(incoming_id) else uuid.uuid4().hex
    started = time.perf_counter()
    response: Response | None = None
    try:
        response = await call_next(request)
    finally:
        # "finally" runs even if the endpoint crashed, so failed requests are logged too
        duration_ms = round((time.perf_counter() - started) * 1000, 1)
        logger.info(
            "request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code if response else 500,
                "duration_ms": duration_ms,
                "cache": response.headers.get("X-Cache") if response else None,
                "request_id": request_id,
            },
        )

    # Server-Timing: browser dev tools show it in the Network tab, separate from network time
    response.headers["Server-Timing"] = f"app;dur={duration_ms}"
    # Returning the ID lets someone report a problem with an ID we can find in the logs
    response.headers["X-Request-ID"] = request_id
    return response
