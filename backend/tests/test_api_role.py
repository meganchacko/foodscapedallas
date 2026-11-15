import uuid

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError

from app.db.api_role import grant_api_role

# Roles belong to the whole Postgres server, not one database, so use a name that can't clash
# with a real role
TEST_ROLE = "foodscape_api_test"


@pytest.fixture
def api_engine(clean_engine):
    """An engine that logs in as the limited API role, against the test database."""
    password = uuid.uuid4().hex
    grant_api_role(clean_engine, TEST_ROLE, password)
    engine = create_engine(clean_engine.url.set(username=TEST_ROLE, password=password))
    yield engine
    engine.dispose()
    with clean_engine.begin() as connection:
        # DROP OWNED removes the role's permissions, which must go before the role can
        connection.execute(text(f"DROP OWNED BY {TEST_ROLE}"))
        connection.execute(text(f"DROP ROLE {TEST_ROLE}"))


def insert_health_check(connection):
    connection.execute(
        text(
            "INSERT INTO health_checks (id, anonymous_id, inputs, probability, model_version) "
            "VALUES (:id, :anon, '{}', 0.5, 'test')"
        ),
        {"id": uuid.uuid4(), "anon": uuid.uuid4()},
    )


def test_the_api_role_can_read_map_data(api_engine):
    with api_engine.connect() as connection:
        connection.execute(text("SELECT count(*) FROM tracts"))
        connection.execute(text("SELECT count(*) FROM places"))


def test_the_api_role_can_save_and_delete_health_checks(api_engine):
    with api_engine.begin() as connection:
        insert_health_check(connection)
        connection.execute(text("DELETE FROM health_checks"))


@pytest.mark.parametrize(
    "statement",
    [
        "DELETE FROM places",
        "UPDATE tracts SET obesity_pct = 0",
        "INSERT INTO places (name, type, source, source_id, geom) "
        "VALUES ('x', 'grocery', 'x', 'x', ST_GeomFromText('POINT(0 0)', 4326))",
        "DROP TABLE health_checks",
        "CREATE TABLE sneaky (id int)",
    ],
)
def test_the_api_role_cannot_change_anything_else(api_engine, statement):
    with pytest.raises(ProgrammingError, match="permission denied|must be owner"):
        with api_engine.begin() as connection:
            connection.execute(text(statement))


def test_granting_twice_is_safe(clean_engine, api_engine):
    # Runs after every deploy's migrations, so it must work when the role already exists
    grant_api_role(clean_engine, TEST_ROLE, "a-new-password")
