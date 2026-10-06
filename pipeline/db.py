from sqlalchemy import Engine, create_engine

from pipeline.config import get_settings


def create_db_engine() -> Engine:
    return create_engine(get_settings().database_url)
