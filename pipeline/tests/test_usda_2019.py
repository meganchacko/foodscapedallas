"""The 2010 -> 2020 tract crosswalk, with small made-up tracts so the math is easy to check."""

import pandas as pd

from pipeline.loaders.usda_2019 import crosswalk_to_2020


def usda_2010(*rows):
    return pd.DataFrame(
        rows,
        columns=[
            "geoid_2010",
            "low_income",
            "low_access",
            "low_income_low_access",
            "low_access_population",
        ],
    )


def relationship(*rows):
    return pd.DataFrame(
        rows,
        columns=["geoid", "geoid_2010", "land_2010_total", "land_overlap", "water_overlap"],
    )


def by_geoid(result):
    return result.set_index("geoid").to_dict("index")


def test_split_tract_copies_flags_and_divides_population_by_land():
    # 2010 tract A was split into 2020 tracts X (60% of A's land) and Y (40%)
    result = crosswalk_to_2020(
        usda_2010(("A", True, True, True, 100)),
        relationship(("X", "A", 1000, 600, 0), ("Y", "A", 1000, 400, 0)),
    )

    rows = by_geoid(result)
    assert rows["X"]["low_income_low_access"] is True
    assert rows["Y"]["low_income_low_access"] is True
    assert rows["X"]["low_access_population"] == 60
    assert rows["Y"]["low_access_population"] == 40


def test_tract_spanning_two_old_tracts_takes_flags_from_the_bigger_overlap():
    # 2020 tract Z is 700 land units from A (70% of A) and 300 from B (50% of B)
    result = crosswalk_to_2020(
        usda_2010(("A", True, True, True, 100), ("B", False, False, False, 60)),
        relationship(("Z", "A", 1000, 700, 0), ("Z", "B", 600, 300, 0)),
    )

    row = by_geoid(result)["Z"]
    assert row["low_access"] is True  # A covers more of Z's land than B does
    assert row["low_access_population"] == 70 + 30  # 70% of A's 100 + 50% of B's 60


def test_population_stays_blank_when_the_source_is_blank():
    result = crosswalk_to_2020(
        usda_2010(("A", False, False, False, None)),
        relationship(("X", "A", 1000, 1000, 0)),
    )

    assert by_geoid(result)["X"]["low_access_population"] is None


def test_water_only_tract_still_gets_flags():
    # A 2020 tract that is all water has no land overlap; water overlap picks the parent
    result = crosswalk_to_2020(
        usda_2010(("A", True, True, False, 50), ("B", False, False, False, 10)),
        relationship(("LAKE", "A", 1000, 0, 500), ("LAKE", "B", 1000, 0, 20)),
    )

    row = by_geoid(result)["LAKE"]
    assert row["low_access"] is True
    assert row["low_access_population"] == 0  # no land, so no share of anyone's population


def test_tract_with_no_2019_data_is_left_out():
    result = crosswalk_to_2020(usda_2010(), relationship(("NEW", "UNKNOWN", 1000, 1000, 0)))

    assert result.empty
