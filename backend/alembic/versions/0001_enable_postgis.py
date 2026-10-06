"""enable postgis

Revision ID: 0001
Revises:
Create Date: 2026-10-05

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # The postgis/postgis Docker image already turns this on, but managed cloud databases
    # (Phase 9) start without it. IF NOT EXISTS makes this safe either way.
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS postgis")
