"""The counties FoodScape covers: the four core Dallas-Fort Worth counties in Texas.

Every loader filters its source data to these counties. To add a county, add it here (and
widen BBOX if it falls outside), then re-run the pipeline.
"""

STATE_FIPS = "48"  # Texas

# 3-digit county FIPS code -> county name (as USDA's SNAP retailer file spells it, uppercased)
COUNTIES = {
    "113": "Dallas",
    "439": "Tarrant",
    "085": "Collin",
    "121": "Denton",
}

# 5-digit state + county codes, the first 5 digits of every tract and block GEOID in the area.
# A tuple, so it can be passed straight to str.startswith.
COUNTY_GEOIDS = tuple(STATE_FIPS + county for county in COUNTIES)

# The four counties' combined extent (south, west, north, east) plus a small margin. The
# rectangle also covers bits of neighboring counties; places outside our tracts are dropped.
BBOX = (32.53, -97.56, 33.44, -96.28)
