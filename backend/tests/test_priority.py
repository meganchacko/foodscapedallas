from app.services.priority import county_median, is_priority_area

MEDIAN = 35.0


def test_low_access_and_above_median_obesity_is_a_priority_area():
    assert is_priority_area(low_access=True, obesity_pct=40.0, obesity_median=MEDIAN) is True


def test_low_access_alone_is_not_a_priority_area():
    assert is_priority_area(low_access=True, obesity_pct=30.0, obesity_median=MEDIAN) is False


def test_high_obesity_alone_is_not_a_priority_area():
    assert is_priority_area(low_access=False, obesity_pct=40.0, obesity_median=MEDIAN) is False


def test_obesity_exactly_at_the_median_is_not_above_it():
    assert is_priority_area(low_access=True, obesity_pct=35.0, obesity_median=MEDIAN) is False


def test_missing_data_is_never_a_priority_area():
    assert is_priority_area(low_access=None, obesity_pct=40.0, obesity_median=MEDIAN) is False
    assert is_priority_area(low_access=True, obesity_pct=None, obesity_median=MEDIAN) is False
    assert is_priority_area(low_access=True, obesity_pct=40.0, obesity_median=None) is False


def test_county_median_ignores_missing_values():
    assert county_median([30.0, None, 40.0, 50.0]) == 40.0
    assert county_median([None, None]) is None
