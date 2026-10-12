"""Runs the health check model and explains its estimate.

The model is trained by ml/train.py and saved as ml/model/obesity_model.joblib: a scikit-learn
pipeline (encoding + logistic regression) plus the average of each encoded column in the
training data.

How an estimate is explained: logistic regression adds up coefficient x value for every encoded
column to get log-odds. Compared with an average respondent, the difference splits exactly into
one piece per column: coefficient x (this person's value - the average value). Summing the
pieces for one question (e.g. the 5 transportation columns) gives that answer's effect.
"""

import json
from dataclasses import dataclass
from functools import lru_cache

import joblib
import numpy as np
import pandas as pd

from app.config import get_settings
from app.schemas.health_check import (
    Factor,
    HealthCheckRequest,
    HealthCheckResponse,
    ResourceSuggestion,
)

MODEL_FILE = "obesity_model.joblib"
MODEL_CARD_FILE = "model_card.json"
TOP_FACTORS = 5
OLDEST_AGE_IN_DATA = 61


@dataclass(frozen=True)
class Question:
    column: str  # the dataset column the model knows
    label: str
    changeable: bool
    # The healthier answer for a habit, in the request's terms, if there's a clear one
    healthier: object = None


# Request field -> how it maps onto the model
QUESTIONS = {
    "sex": Question("Gender", "Sex", changeable=False),
    "age": Question("Age", "Age", changeable=False),
    "family_history_overweight": Question(
        "family_history_with_overweight", "Family history of overweight", changeable=False
    ),
    "high_calorie_food_often": Question(
        "FAVC", "High-calorie food often", changeable=True, healthier=False
    ),
    "vegetables": Question("FCVC", "Vegetables with meals", changeable=True, healthier=3),
    "main_meals_per_day": Question("NCP", "Main meals per day", changeable=True),
    "snacking": Question("CAEC", "Eating between meals", changeable=True, healthier="no"),
    "smokes": Question("SMOKE", "Smoking", changeable=True, healthier=False),
    "water": Question("CH2O", "Water per day", changeable=True, healthier=3),
    "tracks_calories": Question("SCC", "Tracking calories", changeable=True),
    "physical_activity": Question("FAF", "Physical activity", changeable=True, healthier=3),
    "screen_time": Question("TUE", "Screen time", changeable=True, healthier=0),
    "alcohol": Question("CALC", "Alcohol", changeable=True, healthier="no"),
    "transportation": Question("MTRANS", "Usual transportation", changeable=True),
}

# What to suggest when a habit is the top actionable factor. Only food-related habits point to
# places; the rest get a short note.
SUGGESTIONS = {
    "vegetables": ResourceSuggestion(
        place_type="farmers_market",
        message="Farmers markets and grocery stores near you have fresh vegetables.",
    ),
    "high_calorie_food_often": ResourceSuggestion(
        place_type="grocery",
        message="Grocery stores near you carry fresh and lower-calorie options.",
    ),
    "snacking": ResourceSuggestion(
        place_type="grocery",
        message="Grocery stores near you carry fruit and other filling snacks.",
    ),
    "physical_activity": ResourceSuggestion(
        place_type=None, message="Even short walks on more days of the week can help."
    ),
    "screen_time": ResourceSuggestion(
        place_type=None, message="Breaking up long stretches of screen time can help."
    ),
    "water": ResourceSuggestion(place_type=None, message="Drinking more water can help."),
    "smokes": ResourceSuggestion(place_type=None, message="Free help to quit: 1-800-QUIT-NOW."),
    "alcohol": ResourceSuggestion(place_type=None, message="Drinking less alcohol can help."),
}


def to_model_row(answers: dict) -> pd.DataFrame:
    """Translate request answers into the one-row table the model was trained on."""

    def yes_no(value: bool) -> str:
        return "yes" if value else "no"

    return pd.DataFrame(
        [
            {
                "Gender": answers["sex"],
                "family_history_with_overweight": yes_no(answers["family_history_overweight"]),
                "FAVC": yes_no(answers["high_calorie_food_often"]),
                "CAEC": answers["snacking"],
                "SMOKE": yes_no(answers["smokes"]),
                "SCC": yes_no(answers["tracks_calories"]),
                "CALC": answers["alcohol"],
                "MTRANS": answers["transportation"],
                "Age": answers["age"],
                "FCVC": answers["vegetables"],
                "NCP": answers["main_meals_per_day"],
                "CH2O": answers["water"],
                "FAF": answers["physical_activity"],
                "TUE": answers["screen_time"],
            }
        ]
    )


class HealthModel:
    def __init__(self, bundle: dict):
        self.pipeline = bundle["pipeline"]
        self.version: str = bundle["model_version"]
        self.categories: dict[str, list[str]] = bundle["categories"]
        preprocess = self.pipeline.named_steps["preprocess"]
        self.column_names = list(preprocess.get_feature_names_out())
        self.coefficients = self.pipeline.named_steps["classifier"].coef_[0]
        means = bundle["encoded_feature_means"]
        self.means = np.array([means[name] for name in self.column_names])

    def probability(self, answers: dict) -> float:
        return float(self.pipeline.predict_proba(to_model_row(answers))[0, 1])

    def effects(self, answers: dict) -> dict[str, float]:
        """Each question's effect on the log-odds, compared with an average respondent."""
        encoded = self.pipeline.named_steps["preprocess"].transform(to_model_row(answers))[0]
        pieces = self.coefficients * (encoded - self.means)
        effects = {}
        for field, question in QUESTIONS.items():
            # Encoded column names look like "numbers__Age" or "categories__MTRANS_Walking"
            prefixes = (f"numbers__{question.column}", f"categories__{question.column}_")
            effects[field] = float(
                sum(
                    piece
                    for name, piece in zip(self.column_names, pieces, strict=True)
                    if name == prefixes[0] or name.startswith(prefixes[1])
                )
            )
        return effects

    def is_actionable(self, field: str, answers: dict, probability: float) -> bool:
        """Would switching to the healthier answer lower this person's estimate?

        Checking the model itself, instead of assuming, matters here: in this dataset some
        relationships run backwards (e.g. more vegetables raises the estimate, an artifact of
        the synthetic rows), and we must never turn those into advice.
        """
        question = QUESTIONS[field]
        if not question.changeable or question.healthier is None:
            return False
        if answers[field] == question.healthier:
            return False
        healthier = {**answers, field: question.healthier}
        return self.probability(healthier) < probability

    def check(self, request: HealthCheckRequest) -> HealthCheckResponse:
        answers = request.model_dump()
        probability = self.probability(answers)

        effects = self.effects(answers)
        ranked = sorted(effects, key=lambda field: abs(effects[field]), reverse=True)
        factors = [
            Factor(
                field=field,
                label=QUESTIONS[field].label,
                effect=round(effects[field], 3),
                direction="raises" if effects[field] > 0 else "lowers",
                changeable=QUESTIONS[field].changeable,
                actionable=(effects[field] > 0 and self.is_actionable(field, answers, probability)),
            )
            for field in ranked[:TOP_FACTORS]
        ]

        top_actionable = next((f.field for f in factors if f.actionable), None)
        return HealthCheckResponse(
            probability=round(probability, 3),
            model_version=self.version,
            factors=factors,
            suggestion=SUGGESTIONS.get(top_actionable) if top_actionable else None,
            notes=self.notes(request),
            saved=False,
        )

    @staticmethod
    def notes(request: HealthCheckRequest) -> list[str]:
        notes = []
        if request.sex == "Male":
            notes.append(
                "This estimate is less accurate for men: the model was much better at telling "
                "apart women's answers in its training data."
            )
        if request.age > OLDEST_AGE_IN_DATA:
            notes.append(
                f"Nobody over {OLDEST_AGE_IN_DATA} was in the training data, so this estimate "
                "is less reliable."
            )
        return notes


@lru_cache
def get_health_model() -> HealthModel:
    """Load the model once and reuse it (it's read-only, so sharing it is safe).

    joblib files can run code when loaded, so only ever load a model file we built ourselves.
    """
    return HealthModel(joblib.load(get_settings().model_dir / MODEL_FILE))


@lru_cache
def get_model_card() -> dict:
    """The model card written by ml/train.py: how the model was built, how well it works, and its
    limits. Read once; it only changes when the model is retrained (and the server restarted).
    """
    return json.loads((get_settings().model_dir / MODEL_CARD_FILE).read_text())
