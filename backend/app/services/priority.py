"""Priority areas: tracts where low food access and higher obesity occur together.

This marks where two problems coincide. It does not mean low food access causes obesity: both
are linked to things like income, so the map shows overlap, not cause and effect.
"""

from collections import defaultdict
from statistics import median

from app.counties import county_of


def county_median(values: list[float | None]) -> float | None:
    """Median of the known values; None if there are none."""
    known = [value for value in values if value is not None]
    return median(known) if known else None


def county_medians(obesity_by_geoid: dict[str, float | None]) -> dict[str, float | None]:
    """County name -> median obesity of its tracts.

    Each tract is compared with its own county, so "above the county median" means the same
    thing in Dallas as in Tarrant even though the counties' overall rates differ.
    """
    by_county: dict[str, list[float | None]] = defaultdict(list)
    for geoid, obesity_pct in obesity_by_geoid.items():
        by_county[county_of(geoid)].append(obesity_pct)
    return {county: county_median(values) for county, values in by_county.items()}


def is_priority_area(
    low_access: bool | None, obesity_pct: float | None, obesity_median: float | None
) -> bool:
    """Low access AND obesity above the median for the tract's county.

    Missing data is never a priority area: we only highlight what the data actually shows.
    """
    if low_access is not True or obesity_pct is None or obesity_median is None:
        return False
    return obesity_pct > obesity_median
