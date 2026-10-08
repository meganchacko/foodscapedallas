"""Priority areas: tracts where low food access and higher obesity occur together.

This marks where two problems coincide. It does not mean low food access causes obesity: both
are linked to things like income, so the map shows overlap, not cause and effect.
"""

from statistics import median


def county_median(values: list[float | None]) -> float | None:
    """Median of the known values; None if there are none."""
    known = [value for value in values if value is not None]
    return median(known) if known else None


def is_priority_area(
    low_access: bool | None, obesity_pct: float | None, obesity_median: float | None
) -> bool:
    """Low access AND obesity above the county median.

    Missing data is never a priority area: we only highlight what the data actually shows.
    """
    if low_access is not True or obesity_pct is None or obesity_median is None:
        return False
    return obesity_pct > obesity_median
