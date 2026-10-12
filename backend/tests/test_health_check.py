import math
import uuid

import pytest
from sqlalchemy import text

from app.db.database import get_engine
from app.main import app
from app.schemas.health_check import HealthCheckRequest
from app.services.health_check import QUESTIONS, get_health_model

ANSWERS = {
    "sex": "Female",
    "age": 30,
    "family_history_overweight": True,
    "high_calorie_food_often": True,
    "vegetables": 2,
    "main_meals_per_day": 3,
    "snacking": "Sometimes",
    "smokes": False,
    "water": 2,
    "tracks_calories": False,
    "physical_activity": 1,
    "screen_time": 1,
    "alcohol": "Sometimes",
    "transportation": "Public_Transportation",
}


@pytest.fixture
def api(client, clean_engine):
    app.dependency_overrides[get_engine] = lambda: clean_engine
    return client


def saved_rows(engine):
    with engine.connect() as connection:
        return connection.execute(text("SELECT * FROM health_checks")).mappings().all()


def test_valid_answers_return_a_probability_between_0_and_1(api):
    response = api.post("/health-check", json=ANSWERS)

    assert response.status_code == 200
    body = response.json()
    assert 0 <= body["probability"] <= 1
    assert body["model_version"] == "2.0"
    assert 0 < len(body["factors"]) <= 5


def test_factors_mark_changeable_habits(api):
    factors = {f["field"]: f for f in api.post("/health-check", json=ANSWERS).json()["factors"]}

    assert factors["family_history_overweight"]["changeable"] is False
    assert all(f["changeable"] for f in factors.values() if f["field"] == "snacking")


@pytest.mark.parametrize(
    "change",
    [
        {"age": 5},  # under 18
        {"age": 150},
        {"vegetables": 7},  # answers are 1-3
        {"transportation": "Spaceship"},
        {"snacking": "sometimes"},  # values are case-sensitive
        {"sex": None},
    ],
)
def test_invalid_answers_are_rejected(api, change):
    assert api.post("/health-check", json={**ANSWERS, **change}).status_code == 422


def test_missing_answer_is_rejected(api):
    answers = {key: value for key, value in ANSWERS.items() if key != "water"}

    assert api.post("/health-check", json=answers).status_code == 422


def test_nothing_is_stored_without_opting_in(api, clean_engine):
    response = api.post("/health-check", json=ANSWERS)

    assert response.json()["saved"] is False
    assert saved_rows(clean_engine) == []


def test_opting_in_stores_answers_with_an_anonymous_id(api, clean_engine):
    anonymous_id = str(uuid.uuid4())

    response = api.post(
        "/health-check", json={**ANSWERS, "save": True, "anonymous_id": anonymous_id}
    )

    assert response.json()["saved"] is True
    [row] = saved_rows(clean_engine)
    assert str(row["anonymous_id"]) == anonymous_id
    assert row["inputs"]["vegetables"] == 2
    assert "save" not in row["inputs"]
    assert row["model_version"] == "2.0"


def test_saving_requires_an_anonymous_id(api):
    assert api.post("/health-check", json={**ANSWERS, "save": True}).status_code == 422


def test_men_and_people_over_61_get_a_reliability_note(api):
    man = api.post("/health-check", json={**ANSWERS, "sex": "Male"}).json()
    older = api.post("/health-check", json={**ANSWERS, "age": 70}).json()
    woman = api.post("/health-check", json=ANSWERS).json()

    assert any("men" in note for note in man["notes"])
    assert any("61" in note for note in older["notes"])
    assert woman["notes"] == []


# --- The model and its explanations ---


def test_factor_effects_add_up_to_the_difference_from_an_average_respondent():
    model = get_health_model()
    answers = HealthCheckRequest(**ANSWERS).model_dump()

    log_odds = math.log(model.probability(answers) / (1 - model.probability(answers)))
    intercept = model.pipeline.named_steps["classifier"].intercept_[0]
    average_log_odds = intercept + float(model.coefficients @ model.means)

    assert sum(model.effects(answers).values()) == pytest.approx(log_odds - average_log_odds)


def test_actionable_factors_really_lower_the_estimate():
    model = get_health_model()
    answers = HealthCheckRequest(**ANSWERS).model_dump()
    probability = model.probability(answers)

    for field, question in QUESTIONS.items():
        if model.is_actionable(field, answers, probability):
            healthier = {**answers, field: question.healthier}
            assert model.probability(healthier) < probability


def test_backwards_associations_are_never_suggested():
    # In this data, eating vegetables more often raises the estimate (a synthetic-data artifact).
    # So "eat more vegetables" must never be offered as a way to lower it.
    model = get_health_model()
    answers = HealthCheckRequest(**{**ANSWERS, "vegetables": 1}).model_dump()

    assert not model.is_actionable("vegetables", answers, model.probability(answers))


def test_api_choices_match_the_answers_the_model_was_trained_on():
    model = get_health_model()
    schema = HealthCheckRequest.model_json_schema()["properties"]

    def allowed(field):
        return set(schema[field]["enum"])

    assert allowed("sex") == set(model.categories["Gender"])
    assert allowed("snacking") == set(model.categories["CAEC"])
    assert allowed("alcohol") == set(model.categories["CALC"])
    assert allowed("transportation") == set(model.categories["MTRANS"])
