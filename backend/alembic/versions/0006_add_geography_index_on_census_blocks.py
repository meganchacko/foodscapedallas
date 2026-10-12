"""add geography index on census blocks

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-12

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Same idea as ix_places_geography (0005): lets "how many people live within N meters of
    # here" queries (ST_DWithin on center::geography) use an index instead of a full scan
    op.create_index(
        "ix_census_blocks_geography",
        "census_blocks",
        [sa.text("(center::geography)")],
        postgresql_using="gist",
    )


def downgrade() -> None:
    op.drop_index("ix_census_blocks_geography", table_name="census_blocks")
