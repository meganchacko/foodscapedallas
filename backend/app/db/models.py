import uuid
from datetime import datetime
from decimal import Decimal

from geoalchemy2 import Geometry, WKBElement
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# WGS 84 latitude/longitude: the coordinate system GPS, the Census, OpenStreetMap, and Leaflet use
SRID = 4326


# Spatial indexes are declared explicitly (spatial_index=False + a GIST Index) instead of letting
# GeoAlchemy2 add them implicitly, so they show up plainly in the migration.


class Tract(Base):
    """A 2020 census tract in Dallas County, with the stats shown on the map.

    Data columns are nullable because the pipeline loads tract shapes first and fills in
    population and CDC numbers afterwards; null means "not known", not zero.
    Food access flags live in TractFoodAccess, one row per definition.
    """

    __tablename__ = "tracts"
    __table_args__ = (Index("ix_tracts_geom", "geom", postgresql_using="gist"),)

    # 11 digits: state (2) + county (3) + tract (6), e.g. 48113 = Dallas County, TX
    geoid: Mapped[str] = mapped_column(String(11), primary_key=True)
    geom: Mapped[WKBElement] = mapped_column(
        Geometry("MULTIPOLYGON", srid=SRID, spatial_index=False)
    )
    # A lighter copy of geom for drawing the map (borders moved by at most ~20 m). The pipeline
    # simplifies all tracts together, so neighbors keep sharing edges with no gaps or overlaps.
    # Spatial queries use the full-detail geom.
    geom_simplified: Mapped[WKBElement | None] = mapped_column(
        Geometry("MULTIPOLYGON", srid=SRID, spatial_index=False)
    )
    population: Mapped[int | None]

    # CDC PLACES: estimated % of adults with obesity
    obesity_pct: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
    median_income: Mapped[int | None]


class TractFoodAccess(Base):
    """USDA food access flags for one tract under one definition ("measure").

    A tract has one row per measure, so the map can switch between definitions:
      - "usda_2019_supermarkets": 2019 Food Access Research Atlas, which counts supermarkets and
        large grocery stores. Published on 2010 tracts; the pipeline translates it to 2020 tracts.
      - "usda_2025_snap_retailers": 2025 Atlas, which counts any SNAP-authorized store.
    Both use the standard low-access definition: over 1 mile (urban) or 10 miles (rural) from a
    store, measured in a straight line.
    """

    __tablename__ = "tract_food_access"

    geoid: Mapped[str] = mapped_column(
        String(11), ForeignKey("tracts.geoid", ondelete="CASCADE"), primary_key=True
    )
    measure: Mapped[str] = mapped_column(String(50), primary_key=True)
    low_income: Mapped[bool | None]
    low_access: Mapped[bool | None]
    low_income_low_access: Mapped[bool | None]
    low_access_population: Mapped[int | None]


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
        # Distance queries in meters cast to geography (geom::geography). Postgres can only use
        # an index built on that same expression, so the geometry index above can't help them.
        Index("ix_places_geography", text("(geom::geography)"), postgresql_using="gist"),
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
