"""Logs as JSON: one line per event, easy for log tools to search and graph.

e.g. {"time": "...", "level": "INFO", "logger": "app.requests", "message": "request",
      "method": "GET", "path": "/tracts", "status": 200, "duration_ms": 1.3, "cache": "HIT",
      "request_id": "..."}
"""

import json
import logging
import sys
from datetime import UTC, datetime

# Extra fields a log call may attach (logger.info("request", extra={...})). Listing them means
# nothing else, like a request body, can end up in the logs by accident.
EXTRA_FIELDS = ("method", "path", "status", "duration_ms", "cache", "request_id")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "time": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in EXTRA_FIELDS:
            if hasattr(record, field):
                entry[field] = getattr(record, field)
        if record.exc_info:
            entry["error"] = self.formatException(record.exc_info)
        return json.dumps(entry)


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)
    # Our middleware logs every request (as JSON, without query strings), so uvicorn's own
    # access log would only duplicate it, and it includes full URLs with search text
    logging.getLogger("uvicorn.access").disabled = True
