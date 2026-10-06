"""Alembic runs this file for every command. It decides which database to connect to and
which models to compare against when autogenerating a migration."""

from logging.config import fileConfig

from alembic import context
from geoalchemy2 import alembic_helpers
from sqlalchemy import create_engine

import app.db.models  # noqa: F401  (importing the models registers their tables on Base.metadata)
from app.config import get_settings
from app.db.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# The tables our models describe; autogenerate diffs the database against this
target_metadata = Base.metadata


def include_object(obj, name, type_, reflected, compare_to) -> bool:
    # Only manage tables our models define. The postgis Docker image also installs PostGIS's
    # TIGER geocoder (tables like "addr" and "state"), which autogenerate would otherwise
    # try to drop.
    if type_ == "table" and reflected and compare_to is None:
        return False
    # GeoAlchemy2's filter skips PostGIS internals like spatial_ref_sys and its implicit indexes
    return alembic_helpers.include_object(obj, name, type_, reflected, compare_to)


def get_url() -> str:
    # Tests point Alembic at a separate test database by setting sqlalchemy.url;
    # otherwise use the normal app settings
    return config.get_main_option("sqlalchemy.url") or get_settings().database_url


def run_migrations_offline() -> None:
    """`alembic upgrade head --sql`: print the SQL instead of running it."""
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(get_url())
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
