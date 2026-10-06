"""move food access to its own table

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-06

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FOOD_ACCESS_COLUMNS = ("low_income", "low_access", "low_income_low_access", "low_access_population")


def upgrade() -> None:
    # One row per (tract, definition), so the map can switch between food access definitions.
    # The old columns on tracts are dropped without copying data: no data had been loaded yet.
    op.create_table(
        "tract_food_access",
        sa.Column("geoid", sa.String(length=11), nullable=False),
        sa.Column("measure", sa.String(length=50), nullable=False),
        sa.Column("low_income", sa.Boolean(), nullable=True),
        sa.Column("low_access", sa.Boolean(), nullable=True),
        sa.Column("low_income_low_access", sa.Boolean(), nullable=True),
        sa.Column("low_access_population", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["geoid"],
            ["tracts.geoid"],
            name=op.f("fk_tract_food_access_geoid_tracts"),
            ondelete="CASCADE",  # deleting a tract also deletes its food access rows
        ),
        sa.PrimaryKeyConstraint("geoid", "measure", name=op.f("pk_tract_food_access")),
    )
    for column in FOOD_ACCESS_COLUMNS:
        op.drop_column("tracts", column)


def downgrade() -> None:
    op.add_column("tracts", sa.Column("low_income", sa.Boolean(), nullable=True))
    op.add_column("tracts", sa.Column("low_access", sa.Boolean(), nullable=True))
    op.add_column("tracts", sa.Column("low_income_low_access", sa.Boolean(), nullable=True))
    op.add_column("tracts", sa.Column("low_access_population", sa.Integer(), nullable=True))
    op.drop_table("tract_food_access")
