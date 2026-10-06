import uuid
from datetime import datetime
from decimal import Decimal

from geoalchemy2 import Geometry, WKBElement
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# WGS 84 latitude/longitude: the coordinate system GPS, the Census, OpenStreetMap, and Leaflet use
SRID = 4326


# Spatial indexes are declared explicitly (spatial_index=False + a GIST Index) instead of letting
# GeoAlchemy2 add them implicitly, so they show up plainly in the migration.


class Tract(Base):
    """A census tract in Dallas County, with the stats shown on the map.

    Data columns are nullable because the pipeline loads tract shapes first and fills in
    USDA and CDC numbers afterwards; null means "not known", not zero.
    """

    __tablename__ = "tracts"
    __table_args__ = (Index("ix_tracts_geom", "geom", postgresql_using="gist"),)

    # 11 digits: state (2) + county (3) + tract (6), e.g. 48113 = Dallas County, TX
    geoid: Mapped[str] = mapped_column(String(11), primary_key=True)
    geom: Mapped[WKBElement] = mapped_column(
        Geometry("MULTIPOLYGON", srid=SRID, spatial_index=False)
    )
    population: Mapped[int | None]

    # USDA Food Access Research Atlas flags, using the standard 1-mile (urban) / 10-mile (rural)
    # low-access definition
    low_income: Mapped[bool | None]
    low_access: Mapped[bool | None]
    low_income_low_access: Mapped[bool | None]
    low_access_population: Mapped[int | None]

    # CDC PLACES: estimated % of adults with obesity
    obesity_pct: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
    median_income: Mapped[int | None]


class CensusBlock(Base):
    """A 2020 census block, stored as its center point. Used to count people near a location."""

    __tablename__ = "census_blocks"
    __table_args__ = (Index("ix_census_blocks_center", "center", postgresql_using="gist"),)

    # 15 digits: the tract GEOID (11) + block number (4)
    geoid: Mapped[str] = mapped_column(String(15), primary_key=True)
    center: Mapped[WKBElement] = mapped_column(Geometry("POINT", srid=SRID, spatial_index=False))
    population: Mapped[int]


class Place(Base):
    """A grocery store, food pantry, or farmers market."""

    __tablename__ = "places"
    __table_args__ = (
        # A CHECK constraint instead of a Postgres ENUM: adding a type later is a one-line change
        CheckConstraint("type IN ('grocery', 'pantry', 'farmers_market')", name="type_valid"),
        # The stable key the pipeline upserts on, so re-running it never creates duplicates
        UniqueConstraint("source", "source_id"),
        Index("ix_places_geom", "geom", postgresql_using="gist"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    type: Mapped[str] = mapped_column(String(20))
    geom: Mapped[WKBElement] = mapped_column(Geometry("POINT", srid=SRID, spatial_index=False))
    address: Mapped[str | None]
    hours: Mapped[str | None]

    # null = unknown, which is different from "does not accept"
    accepts_snap: Mapped[bool | None]
    accepts_wic: Mapped[bool | None]

    # where the row came from, e.g. source="osm", source_id="node/123456"
    source: Mapped[str] = mapped_column(String(50))
    source_id: Mapped[str] = mapped_column(String(100))
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class HealthCheck(Base):
    """A saved health check result. Only written when the user opts in."""

    __tablename__ = "health_checks"
    __table_args__ = (
        CheckConstraint("probability >= 0 AND probability <= 1", name="probability_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # random ID generated in the browser; not linked to a name, email, or account
    anonymous_id: Mapped[uuid.UUID]
    inputs: Mapped[dict] = mapped_column(JSONB)
    probability: Mapped[float]
    model_version: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
