from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Gives every index and constraint a predictable name (e.g. "uq_places_source_source_id").
# Alembic needs names to be able to drop or change constraints in later migrations.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Parent class for all models. Base.metadata collects every table, which Alembic reads."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
