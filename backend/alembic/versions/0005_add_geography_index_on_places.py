"""add geography index on places

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-08

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # An expression index: Postgres indexes the result of geom::geography, so queries like
    # ST_DWithin(geom::geography, <point>, <meters>) can use it instead of scanning every row
    op.create_index(
        "ix_places_geography",
        "places",
        [sa.text("(geom::geography)")],
        postgresql_using="gist",
    )


def downgrade() -> None:
    op.drop_index("ix_places_geography", table_name="places")
