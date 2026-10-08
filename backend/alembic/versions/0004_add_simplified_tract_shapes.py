"""add simplified tract shapes

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-08

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Filled in by the pipeline; no spatial index because it's only used for drawing the map
    op.add_column(
        "tracts",
        sa.Column(
            "geom_simplified",
            Geometry("MULTIPOLYGON", srid=4326, spatial_index=False),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("tracts", "geom_simplified")
