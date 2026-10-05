from typing import Literal

from pydantic import BaseModel

Status = Literal["ok", "error"]


class HealthResponse(BaseModel):
    api: Status
    db: Status
    cache: Status
