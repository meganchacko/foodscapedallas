"""create tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-05

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Every geometry column uses SRID 4326 (WGS 84 latitude/longitude). Spatial indexes are created
# explicitly below with op.create_index(..., postgresql_using="gist"), so spatial_index=False here.


def upgrade() -> None:
    op.create_table(
        "tracts",
        sa.Column("geoid", sa.String(length=11), nullable=False),
        sa.Column("geom", Geometry("MULTIPOLYGON", srid=4326, spatial_index=False), nullable=False),
        sa.Column("population", sa.Integer(), nullable=True),
        sa.Column("low_income", sa.Boolean(), nullable=True),
        sa.Column("low_access", sa.Boolean(), nullable=True),
        sa.Column("low_income_low_access", sa.Boolean(), nullable=True),
        sa.Column("low_access_population", sa.Integer(), nullable=True),
        sa.Column("obesity_pct", sa.Numeric(precision=4, scale=1), nullable=True),
        sa.Column("median_income", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("geoid", name=op.f("pk_tracts")),
    )
    op.create_index("ix_tracts_geom", "tracts", ["geom"], postgresql_using="gist")

    op.create_table(
        "census_blocks",
        sa.Column("geoid", sa.String(length=15), nullable=False),
        sa.Column("center", Geometry("POINT", srid=4326, spatial_index=False), nullable=False),
        sa.Column("population", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("geoid", name=op.f("pk_census_blocks")),
    )
    op.create_index("ix_census_blocks_center", "census_blocks", ["center"], postgresql_using="gist")

    op.create_table(
        "places",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("geom", Geometry("POINT", srid=4326, spatial_index=False), nullable=False),
        sa.Column("address", sa.String(), nullable=True),
        sa.Column("hours", sa.String(), nullable=True),
        sa.Column("accepts_snap", sa.Boolean(), nullable=True),
        sa.Column("accepts_wic", sa.Boolean(), nullable=True),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("source_id", sa.String(length=100), nullable=False),
        sa.Column(
            "last_updated",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "type IN ('grocery', 'pantry', 'farmers_market')",
            name=op.f("ck_places_type_valid"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_places")),
        sa.UniqueConstraint("source", "source_id", name=op.f("uq_places_source_source_id")),
    )
    op.create_index("ix_places_geom", "places", ["geom"], postgresql_using="gist")

    op.create_table(
        "health_checks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("anonymous_id", sa.Uuid(), nullable=False),
        sa.Column("inputs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("probability", sa.Double(), nullable=False),
        sa.Column("model_version", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "probability >= 0 AND probability <= 1",
            name=op.f("ck_health_checks_probability_range"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_health_checks")),
    )


def downgrade() -> None:
    # Reverse order of upgrade(). Dropping a table also drops its indexes and constraints.
    op.drop_table("health_checks")
    op.drop_table("places")
    op.drop_table("census_blocks")
    op.drop_table("tracts")
