import numpy as np
import pandas as pd
import pytest

from ml.train import (
    CATEGORIES,
    DATA_PATH,
    EXCLUDED_FEATURES,
    FEATURES,
    build_pipeline,
    load_data,
)


@pytest.fixture(scope="module")
def data():
    return load_data()


def test_height_and_weight_are_never_inputs(data):
    features, _ = data

    assert not set(EXCLUDED_FEATURES) & set(FEATURES)
    assert not set(EXCLUDED_FEATURES) & set(features.columns)


def test_target_is_obese_or_not(data):
    _, target = data

    assert set(target.unique()) == {0, 1}
    assert 0.4 < target.mean() < 0.5  # 46% obese: roughly balanced


def test_exact_duplicate_records_are_removed(data):
    # 24 rows in the raw file are exact copies (every column, including height and weight).
    # Rows that differ only in height or weight are different people who gave the same answers,
    # so they stay.
    raw = pd.read_csv(DATA_PATH)
    features, _ = data

    assert len(features) == len(raw) - raw.duplicated().sum()


def test_pipeline_outputs_probabilities_between_0_and_1(data):
    features, target = data
    model = build_pipeline().fit(features, target)

    probability = model.predict_proba(features)[:, 1]

    assert ((probability >= 0) & (probability <= 1)).all()


def test_rare_answers_are_known_even_if_missing_from_training(data):
    features, target = data
    without_always = features["CALC"] != "Always"
    model = build_pipeline().fit(features[without_always], target[without_always])

    row = features.iloc[[0]].assign(CALC="Always")

    assert model.predict_proba(row).shape == (1, 2)  # no "unknown category" error


def test_unknown_answers_are_rejected(data):
    features, target = data
    model = build_pipeline().fit(features, target)

    with pytest.raises(ValueError):
        model.predict_proba(features.iloc[[0]].assign(MTRANS="Spaceship"))


def test_training_is_reproducible(data):
    features, target = data

    first = build_pipeline().fit(features, target).named_steps["classifier"].coef_
    second = build_pipeline().fit(features, target).named_steps["classifier"].coef_

    assert np.array_equal(first, second)


def test_every_category_list_has_at_least_two_answers():
    assert all(len(values) >= 2 for values in CATEGORIES.values())
