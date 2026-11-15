import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request
from redis import Redis
from sqlalchemy import Engine, delete, insert

from app.cache import get_redis
from app.db.database import get_engine
from app.db.models import HealthCheck
from app.rate_limit import RateLimit, allow, client_key
from app.schemas.health_check import (
    DeleteSavedResponse,
    HealthCheckRequest,
    HealthCheckResponse,
)
from app.services.health_check import HealthModel, get_health_model, get_model_card

router = APIRouter()

# Saving is optional, so it has its own, much lower limits: enough for a person to save a few
# results, too few for a script to fill the database. Past either one, the user still gets their
# result, just not saved.
SAVES_PER_CLIENT_PER_HOUR = 10
SAVES_PER_DAY = 2000
NOT_SAVED_NOTE = "Your answers couldn't be saved right now. Your estimate above is unaffected."


def save_allowed(request: Request, cache: Redis) -> bool:
    """Within this client's hourly limit and the site's daily limit?

    Fails closed: if Redis is down, nothing is saved (the result is still returned), since an
    unlimited burst of saves while the limiter is out would defeat the point. The client's limit
    is checked first, so one client hitting theirs doesn't use up everyone's daily allowance.
    """
    client = f"health_check_save:{client_key(request)}"
    within_client_limit = allow(cache, client, SAVES_PER_CLIENT_PER_HOUR, 60 * 60, fail_open=False)
    # "and" stops early: the site-wide count only goes up for clients within their own limit
    return within_client_limit and allow(
        cache, "health_check_save:all", SAVES_PER_DAY, 24 * 60 * 60, fail_open=False
    )


@router.post(
    "/health-check",
    response_model=HealthCheckResponse,
    dependencies=[Depends(RateLimit("health_check", limit=20))],
)
def health_check(
    answers: HealthCheckRequest,
    request: Request,
    model: Annotated[HealthModel, Depends(get_health_model)],
    engine: Annotated[Engine, Depends(get_engine)],
    cache: Annotated[Redis, Depends(get_redis)],
) -> HealthCheckResponse:
    """Estimate the likelihood of obesity from habits and background (no height or weight).

    Educational, not medical advice. Nothing is stored unless `save` is true; then only the
    answers, the result, the model version, and the browser's random anonymous ID are kept.
    """
    result = model.check(answers)

    if answers.save and save_allowed(request, cache):
        with engine.begin() as connection:
            connection.execute(
                insert(HealthCheck).values(
                    id=uuid.uuid4(),
                    anonymous_id=answers.anonymous_id,
                    inputs=answers.model_dump(exclude={"save", "anonymous_id"}),
                    probability=result.probability,
                    model_version=result.model_version,
                )
            )
        result.saved = True
    elif answers.save:
        result.notes.append(NOT_SAVED_NOTE)

    return result


@router.delete(
    "/health-checks",
    response_model=DeleteSavedResponse,
    dependencies=[Depends(RateLimit("health_check_delete", limit=10))],
)
def delete_saved_health_checks(
    anonymous_id: Annotated[uuid.UUID, Header(alias="X-Anonymous-ID")],
    engine: Annotated[Engine, Depends(get_engine)],
) -> DeleteSavedResponse:
    """Delete every saved result made with this browser's anonymous ID.

    The random ID is the only key to someone's saved results, so it's sent in a header, not the
    URL: URLs end up in server, proxy, and browser history logs. A random UUID can't be guessed,
    so only the browser that saved the results can delete them.
    """
    with engine.begin() as connection:
        result = connection.execute(
            delete(HealthCheck).where(HealthCheck.anonymous_id == anonymous_id)
        )
    return DeleteSavedResponse(deleted=result.rowcount)


@router.get("/model-card")
def model_card(card: Annotated[dict, Depends(get_model_card)]) -> dict:
    """How the health check model was built, how accurate it is overall and for different
    groups, and its limitations (see ml/train.py)."""
    return card
