"""Train the health check model: logistic regression for "obese vs. not", without height or weight.

Run from the repo root:  python -m ml.train

Writes ml/model/obesity_model.joblib (the fitted pipeline plus what the API needs to explain a
prediction) and ml/model/model_card.json (how the model was built, how well it works, and its
limits).

Compared with the original model (ml/v1_linear_regression):
- Target is yes/no (Obesity Type I-III) instead of a 0-6 number, and the model outputs a
  probability (logistic regression).
- Height and weight are excluded: the label was assigned from BMI (weight / height^2), so they
  leak the answer.
- Scaling and encoding happen inside a Pipeline, so they're learned from the training rows only.
- The regularization strength is chosen by cross-validation on the training set, and the test
  set is used once, at the end.
"""

import json
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    brier_score_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GridSearchCV, StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ML_DIR = Path(__file__).resolve().parent
DATA_PATH = ML_DIR / "data" / "obesity.csv"
MODEL_DIR = ML_DIR / "model"
MODEL_PATH = MODEL_DIR / "obesity_model.joblib"
MODEL_CARD_PATH = MODEL_DIR / "model_card.json"

# v1 was the linear regression in ml/v1_linear_regression
MODEL_VERSION = "2.0"
RANDOM_STATE = 42  # fixed, so training gives the same model every time

TARGET = "NObeyesdad"
OBESE_LEVELS = ("Obesity_Type_I", "Obesity_Type_II", "Obesity_Type_III")

# The label comes from BMI, so these would leak the answer
EXCLUDED_FEATURES = ("Height", "Weight")

# Every allowed answer, listed explicitly so the model knows each one even if a rare answer
# (e.g. CALC "Always", which appears once) doesn't land in the training split. The API's input
# validation is tested against this same list.
CATEGORIES = {
    "Gender": ["Female", "Male"],
    "family_history_with_overweight": ["no", "yes"],
    "FAVC": ["no", "yes"],  # eats high-calorie food often
    "CAEC": ["no", "Sometimes", "Frequently", "Always"],  # eats between meals
    "SMOKE": ["no", "yes"],
    "SCC": ["no", "yes"],  # monitors calories
    "CALC": ["no", "Sometimes", "Frequently", "Always"],  # drinks alcohol
    "MTRANS": ["Automobile", "Bike", "Motorbike", "Public_Transportation", "Walking"],
}
NUMERIC = [
    "Age",
    "FCVC",  # vegetables with meals: 1 never, 2 sometimes, 3 always
    "NCP",  # main meals per day: 1-4
    "CH2O",  # water per day: 1 (<1 L), 2 (1-2 L), 3 (>2 L)
    "FAF",  # physical activity: 0 none, 1 (1-2 days/wk), 2 (2-4 days), 3 (4-5 days)
    "TUE",  # screen time: 0 (0-2 h/day), 1 (3-5 h), 2 (>5 h)
]
FEATURES = list(CATEGORIES) + NUMERIC

# Regularization strengths to try (smaller C = simpler model)
C_GRID = [0.01, 0.1, 1.0, 10.0, 100.0]


def load_data(path: Path = DATA_PATH) -> tuple[pd.DataFrame, pd.Series]:
    data = pd.read_csv(path)
    # Remove exact duplicates first, so the same row can't end up in both train and test
    data = data.drop_duplicates()
    target = data[TARGET].isin(OBESE_LEVELS).astype(int).rename("obese")
    return data[FEATURES], target


def build_pipeline(c: float = 1.0) -> Pipeline:
    preprocess = ColumnTransformer(
        [
            # yes/no answers become one 0/1 column; multi-choice answers get a column per choice
            (
                "categories",
                OneHotEncoder(categories=list(CATEGORIES.values()), drop="if_binary"),
                list(CATEGORIES),
            ),
            # numbers are rescaled to mean 0, standard deviation 1, so coefficients are comparable
            ("numbers", StandardScaler(), NUMERIC),
        ]
    )
    return Pipeline(
        [
            ("preprocess", preprocess),
            ("classifier", LogisticRegression(C=c, max_iter=1000, random_state=RANDOM_STATE)),
        ]
    )


def tune(features: pd.DataFrame, target: pd.Series) -> GridSearchCV:
    """Pick C by 5-fold cross-validation on the training set (never the test set)."""
    folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    search = GridSearchCV(build_pipeline(), {"classifier__C": C_GRID}, cv=folds, scoring="roc_auc")
    return search.fit(features, target)


def evaluate(target: pd.Series, probability: np.ndarray) -> dict:
    predicted = (probability >= 0.5).astype(int)
    metrics = {
        "n": int(len(target)),
        "obese_share": round(float(target.mean()), 3),
        "accuracy": round(accuracy_score(target, predicted), 3),
        "precision": round(precision_score(target, predicted, zero_division=0), 3),
        "recall": round(recall_score(target, predicted, zero_division=0), 3),
        # Brier score: mean squared error of the probabilities (0 is perfect, lower is better)
        "brier_score": round(brier_score_loss(target, probability), 3),
    }
    # ROC AUC needs both outcomes present; a small group might have only one
    if target.nunique() == 2:
        metrics["roc_auc"] = round(roc_auc_score(target, probability), 3)
    return metrics


def age_band(age: pd.Series) -> pd.Series:
    return pd.cut(
        age, bins=[0, 20, 30, 40, 200], right=False, labels=["14-19", "20-29", "30-39", "40+"]
    )


def per_group(features: pd.DataFrame, target: pd.Series, probability: np.ndarray) -> dict:
    groups = {
        "sex": features["Gender"],
        "age_band": age_band(features["Age"]).astype(str),
    }
    results = {}
    for name, labels in groups.items():
        results[name] = {
            str(label): evaluate(target[labels == label], probability[(labels == label).to_numpy()])
            for label in sorted(labels.unique())
        }
    return results


def calibration_table(target: pd.Series, probability: np.ndarray) -> list[dict]:
    """Does "40%" mean about 40%? Average predicted vs. actual obese share, in 5 equal-size bins."""
    actual, predicted = calibration_curve(target, probability, n_bins=5, strategy="quantile")
    return [
        {"mean_predicted": round(float(p), 3), "actual_share": round(float(a), 3)}
        for p, a in zip(predicted, actual, strict=True)
    ]


def encoded_feature_means(pipeline: Pipeline, features: pd.DataFrame) -> dict[str, float]:
    """Average of each encoded column over the training set: the "average respondent".

    For logistic regression, the difference between someone's log-odds and the average
    respondent's splits exactly into one piece per column: coefficient x (their value - average).
    The API uses this to explain which answers moved an estimate up or down.
    """
    encoded = pipeline.named_steps["preprocess"].transform(features)
    names = pipeline.named_steps["preprocess"].get_feature_names_out()
    return {name: float(mean) for name, mean in zip(names, encoded.mean(axis=0), strict=True)}


def main() -> None:
    # On macOS, numpy's Apple Accelerate backend raises spurious "divide by zero / overflow in
    # matmul" warnings. Checked: training on Linux (as in CI and Docker) with these warnings
    # turned into errors gives identical coefficients and metrics.
    warnings.filterwarnings("ignore", message=".*encountered in matmul", category=RuntimeWarning)

    features, target = load_data()
    train_x, test_x, train_y, test_y = train_test_split(
        features, target, test_size=0.2, stratify=target, random_state=RANDOM_STATE
    )

    search = tune(train_x, train_y)
    model = search.best_estimator_  # refit on the full training set with the best C
    test_probability = model.predict_proba(test_x)[:, 1]

    test_metrics = evaluate(test_y, test_probability)
    # What you'd get by always guessing the more common answer ("not obese")
    test_metrics["baseline_accuracy"] = round(float(max(test_y.mean(), 1 - test_y.mean())), 3)

    MODEL_DIR.mkdir(exist_ok=True)
    joblib.dump(
        {
            "pipeline": model,
            "encoded_feature_means": encoded_feature_means(model, train_x),
            "model_version": MODEL_VERSION,
            "categories": CATEGORIES,
            "numeric_features": NUMERIC,
        },
        MODEL_PATH,
    )

    card = build_model_card(
        search,
        train_x,
        test_metrics,
        per_group(test_x, test_y, test_probability),
        calibration_table(test_y, test_probability),
        len(features),
    )
    MODEL_CARD_PATH.write_text(json.dumps(card, indent=2) + "\n")

    print(
        f"Best C: {search.best_params_['classifier__C']} (cross-validated ROC AUC "
        f"{search.best_score_:.3f})"
    )
    print("Test set:", json.dumps(test_metrics))
    print(f"Saved {MODEL_PATH.name} and {MODEL_CARD_PATH.name} to {MODEL_DIR}")


def build_model_card(search, train_x, test_metrics, groups, calibration, row_count) -> dict:
    """Filled in by commit 3 (model card); kept minimal here."""
    return {"model_version": MODEL_VERSION, "test_metrics": test_metrics}


if __name__ == "__main__":
    main()
