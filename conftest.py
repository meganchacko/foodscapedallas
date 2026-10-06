"""Test fixtures shared by backend/tests and pipeline/tests: a throwaway, migrated database."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, make_url, text

from app.config import get_settings

BACKEND_DIR = Path(__file__).resolve().parent / "backend"


@pytest.fixture(scope="session")
def test_database_url() -> Iterator[str]:
    """Create an empty database just for this test run, and drop it afterwards.

    Tests never touch the dev database, so running them can't wipe data the pipeline loaded.
    """
    settings = get_settings()
    test_db_name = f"{settings.postgres_db}_test"

    # CREATE/DROP DATABASE can't run inside a transaction, hence AUTOCOMMIT. We connect to the
    # main database to do it, since you can't drop the database you're connected to.
    admin_engine = create_engine(settings.database_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as connection:
        # WITH (FORCE) also clears out a test database left behind by a crashed earlier run
        connection.execute(text(f'DROP DATABASE IF EXISTS "{test_db_name}" WITH (FORCE)'))
        connection.execute(text(f'CREATE DATABASE "{test_db_name}"'))

    test_url = make_url(settings.database_url).set(database=test_db_name)
    yield test_url.render_as_string(hide_password=False)

    with admin_engine.connect() as connection:
        connection.execute(text(f'DROP DATABASE IF EXISTS "{test_db_name}" WITH (FORCE)'))
    admin_engine.dispose()


@pytest.fixture(scope="session")
def alembic_config(test_database_url: str) -> Config:
    config = Config(BACKEND_DIR / "alembic.ini")
    # alembic/env.py uses this URL instead of the dev database.
    # The .ini format treats % as special, so escape it in case the password contains one.
    config.set_main_option("sqlalchemy.url", test_database_url.replace("%", "%%"))
    return config


@pytest.fixture(scope="session")
def test_engine(alembic_config: Config, test_database_url: str) -> Iterator[Engine]:
    """An engine for the test database, with every migration applied."""
    command.upgrade(alembic_config, "head")
    engine = create_engine(test_database_url)
    yield engine
    engine.dispose()


@pytest.fixture
def clean_engine(test_engine: Engine) -> Iterator[Engine]:
    """The test database engine, with every table emptied after the test."""
    yield test_engine
    with test_engine.begin() as connection:
        connection.execute(
            text("TRUNCATE tracts, tract_food_access, census_blocks, places, health_checks CASCADE")
        )
