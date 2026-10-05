from functools import lru_cache

from sqlalchemy import Engine, create_engine

from app.config import get_settings


@lru_cache
def get_engine() -> Engine:
    # One engine for the whole app; it manages a pool of reusable database connections.
    # create_engine doesn't connect yet; the first query does.
    return create_engine(
        get_settings().database_url,
        pool_pre_ping=True,  # check a pooled connection is still alive before using it
        connect_args={"connect_timeout": 2},  # fail fast instead of hanging if the DB is down
    )
