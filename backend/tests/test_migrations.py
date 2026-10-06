import pytest
from alembic import command
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

EXPECTED_TABLES = {"tracts", "tract_food_access", "census_blocks", "places", "health_checks"}

# A valid point in downtown Dallas, for inserts
DALLAS_POINT = "ST_GeomFromText('POINT(-96.797 32.776)', 4326)"


def test_migrations_create_all_tables(test_engine):
    tables = set(inspect(test_engine).get_table_names())

    assert EXPECTED_TABLES <= tables


def test_postgis_is_enabled(test_engine):
    with test_engine.connect() as connection:
        postgis = connection.execute(
            text("SELECT 1 FROM pg_extension WHERE extname = 'postgis'")
        ).scalar()

    assert postgis == 1


def test_geometry_columns_use_srid_4326(test_engine):
    with test_engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT f_table_name, f_geometry_column, srid, type FROM geometry_columns "
                "WHERE f_table_schema = 'public'"
            )
        ).all()

    assert set(rows) == {
        ("tracts", "geom", 4326, "MULTIPOLYGON"),
        ("census_blocks", "center", 4326, "POINT"),
        ("places", "geom", 4326, "POINT"),
    }


@pytest.mark.parametrize(
    ("table", "column"),
    [("tracts", "geom"), ("census_blocks", "center"), ("places", "geom")],
)
def test_geometry_columns_have_gist_index(test_engine, table, column):
    with test_engine.connect() as connection:
        index_definitions = (
            connection.execute(
                text("SELECT indexdef FROM pg_indexes WHERE tablename = :table"),
                {"table": table},
            )
            .scalars()
            .all()
        )

    assert any(
        "USING gist" in definition and f"({column})" in definition
        for definition in index_definitions
    )


def test_place_type_must_be_a_known_type(test_engine):
    with test_engine.connect() as connection, pytest.raises(IntegrityError):
        connection.execute(
            text(
                "INSERT INTO places (name, type, geom, source, source_id) "
                f"VALUES ('Taco Stand', 'restaurant', {DALLAS_POINT}, 'test', '1')"
            )
        )


def test_place_source_and_source_id_must_be_unique(test_engine):
    insert = text(
        "INSERT INTO places (name, type, geom, source, source_id) "
        f"VALUES ('Corner Grocery', 'grocery', {DALLAS_POINT}, 'test', 'dup')"
    )
    # The connection is closed without committing, so the first insert is rolled back too
    with test_engine.connect() as connection:
        connection.execute(insert)
        with pytest.raises(IntegrityError):
            connection.execute(insert)


def test_models_match_migrations(alembic_config, test_engine):
    # Fails if someone changes a model in app/db/models.py without writing a migration for it
    command.check(alembic_config)


def test_migrations_downgrade_and_upgrade_cleanly(alembic_config, test_engine):
    command.downgrade(alembic_config, "base")
    assert not EXPECTED_TABLES & set(inspect(test_engine).get_table_names())

    command.upgrade(alembic_config, "head")
    assert EXPECTED_TABLES <= set(inspect(test_engine).get_table_names())
