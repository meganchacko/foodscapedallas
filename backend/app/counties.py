"""County names for the area the pipeline loads (the pipeline's list is pipeline/counties.py).

The API and the pipeline are separate programs, so each keeps its own copy of this short list.
"""

# 5-digit state + county code (the first 5 digits of a tract GEOID) -> county name
COUNTY_NAMES = {
    "48113": "Dallas",
    "48439": "Tarrant",
    "48085": "Collin",
    "48121": "Denton",
}


def county_of(geoid: str) -> str:
    """'48439101100' -> 'Tarrant'. An unlisted county falls back to its code."""
    return COUNTY_NAMES.get(geoid[:5], geoid[:5])
