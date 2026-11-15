"""Creates the database role the API logs in as, with only the permissions it needs.

Least privilege: the API only reads map data, adds saved health checks, and deletes them when
the person who saved them asks, so its role can do exactly that. If the API were ever
compromised, the attacker couldn't drop tables, change map data, or create anything. Migrations
and the data pipeline keep using the admin role.

Run after every migration (deploy/azure runs `migrate.sh` as a job), so tables added by a new
migration are covered:

    python -m app.db.api_role

Does nothing if API_POSTGRES_PASSWORD isn't set (e.g. locally, where the API uses the admin).
"""

import logging

from psycopg import sql
from sqlalchemy import Engine, create_engine

from app.config import get_settings

logger = logging.getLogger(__name__)


def grant_api_role(engine: Engine, user: str, password: str) -> None:
    """Create (or update) the role, then set its permissions from scratch.

    Everything runs in one transaction, so the API never sees a moment with missing permissions.
    """
    # Database objects (role, table names) can't be query parameters, so the SQL is built with
    # psycopg's sql module, which quotes identifiers and values safely.
    role = sql.Identifier(user)
    statements = [
        sql.SQL(
            "DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = {name}) "
            "THEN CREATE ROLE {role}; END IF; END $$"
        ).format(name=sql.Literal(user), role=role),
        sql.SQL("ALTER ROLE {role} LOGIN PASSWORD {password}").format(
            role=role, password=sql.Literal(password)
        ),
        sql.SQL("GRANT CONNECT ON DATABASE {db} TO {role}").format(
            db=sql.Identifier(engine.url.database), role=role
        ),
        sql.SQL("GRANT USAGE ON SCHEMA public TO {role}").format(role=role),
        # Start from nothing, so a permission removed from this list doesn't linger
        sql.SQL("REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {role}").format(role=role),
        sql.SQL("GRANT SELECT ON ALL TABLES IN SCHEMA public TO {role}").format(role=role),
        # Insert to save a result, delete for "delete my saved results"
        sql.SQL("GRANT INSERT, DELETE ON health_checks TO {role}").format(role=role),
    ]
    with engine.begin() as connection:
        cursor = connection.connection.cursor()  # the underlying psycopg connection
        for statement in statements:
            cursor.execute(statement)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    if not settings.api_postgres_password:
        logger.info("API_POSTGRES_PASSWORD not set; the API uses the admin role")
        return
    engine = create_engine(settings.database_url)
    grant_api_role(engine, settings.api_postgres_user, settings.api_postgres_password)
    engine.dispose()
    logger.info("Granted permissions to role %s", settings.api_postgres_user)


if __name__ == "__main__":
    main()
