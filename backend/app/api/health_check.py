import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import Engine, insert

from app.db.database import get_engine
from app.db.models import HealthCheck
from app.schemas.health_check import HealthCheckRequest, HealthCheckResponse
from app.services.health_check import HealthModel, get_health_model

router = APIRouter()


@router.post("/health-check", response_model=HealthCheckResponse)
def health_check(
    request: HealthCheckRequest,
    model: Annotated[HealthModel, Depends(get_health_model)],
    engine: Annotated[Engine, Depends(get_engine)],
) -> HealthCheckResponse:
    """Estimate the likelihood of obesity from habits and background (no height or weight).

    Educational, not medical advice. Nothing is stored unless `save` is true; then only the
    answers, the result, the model version, and the browser's random anonymous ID are kept.
    """
    result = model.check(request)

    if request.save:
        with engine.begin() as connection:
            connection.execute(
                insert(HealthCheck).values(
                    id=uuid.uuid4(),
                    anonymous_id=request.anonymous_id,
                    inputs=request.model_dump(exclude={"save", "anonymous_id"}),
                    probability=result.probability,
                    model_version=result.model_version,
                )
            )
        result.saved = True

    return result
