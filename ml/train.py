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
from datetime import date
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
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


# Survey answers to these questions are whole numbers (e.g. vegetables: 1, 2, or 3); the synthetic
# rows were generated by interpolating between people, so most have values like 2.37
WHOLE_NUMBER_ANSWERS = ["Age", "FCVC", "NCP", "CH2O", "FAF", "TUE"]


def looks_like_survey_response(features: pd.DataFrame) -> pd.Series:
    """True for rows whose answers are all whole numbers, which is what a real response looks like.

    About 23% of rows pass, matching the 23% the dataset's authors say are real. It's a heuristic:
    some synthetic rows can land on whole numbers too.
    """
    answers = features[WHOLE_NUMBER_ANSWERS]
    return (answers - answers.round()).abs().lt(1e-9).all(axis=1)


def coefficients(pipeline: Pipeline) -> dict[str, float]:
    """Each encoded column's coefficient: its effect on the log-odds of obesity."""
    names = pipeline.named_steps["preprocess"].get_feature_names_out()
    values = pipeline.named_steps["classifier"].coef_[0]
    return {name: round(float(value), 3) for name, value in zip(names, values, strict=True)}


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

    # A second score on just the test rows that look like real survey responses: closer to how
    # the model will do for real people than the score on the mostly synthetic test set
    survey = looks_like_survey_response(test_x)
    survey_metrics = evaluate(test_y[survey], test_probability[survey.to_numpy()])
    survey_metrics["baseline_accuracy"] = round(
        float(max(test_y[survey].mean(), 1 - test_y[survey].mean())), 3
    )
    survey_metrics["mean_predicted"] = round(float(test_probability[survey.to_numpy()].mean()), 3)

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

    results = {
        "test_metrics": test_metrics,
        "survey_metrics": survey_metrics,
        "groups": per_group(test_x, test_y, test_probability),
        "calibration": calibration_table(test_y, test_probability),
        "coefficients": coefficients(model),
    }
    card = build_model_card(search, train_x, len(features), results)
    MODEL_CARD_PATH.write_text(json.dumps(card, indent=2) + "\n")

    print(
        f"Best C: {search.best_params_['classifier__C']} (cross-validated ROC AUC "
        f"{search.best_score_:.3f})"
    )
    print("Test set:", json.dumps(test_metrics))
    print("Test rows that look like real survey responses:", json.dumps(survey_metrics))
    print(f"Saved {MODEL_PATH.name} and {MODEL_CARD_PATH.name} to {MODEL_DIR}")


FEATURE_DESCRIPTIONS = {
    "Gender": "Sex (female / male)",
    "Age": "Age in years",
    "family_history_with_overweight": "A family member is or was overweight",
    "FAVC": "Often eats high-calorie food",
    "FCVC": "How often meals include vegetables (never / sometimes / always)",
    "NCP": "Main meals per day (1-4)",
    "CAEC": "Eats between meals (no / sometimes / frequently / always)",
    "SMOKE": "Smokes",
    "CH2O": "Water per day (under 1 L / 1-2 L / over 2 L)",
    "SCC": "Tracks calories",
    "FAF": "Physical activity (none / 1-2 / 2-4 / 4-5 days a week)",
    "TUE": "Screen time per day (0-2 / 3-5 / over 5 hours)",
    "CALC": "Drinks alcohol (no / sometimes / frequently / always)",
    "MTRANS": "Usual transportation",
}


def build_model_card(search, train_x, row_count: int, results: dict) -> dict:
    """Everything someone needs to judge whether and how to use this model."""
    by_sex = results["groups"]["sex"]
    vegetables = results["coefficients"]["numbers__FCVC"]
    survey = results["survey_metrics"]
    return {
        "name": "FoodScape Dallas health check model",
        "model_version": MODEL_VERSION,
        "trained_on": date.today().isoformat(),
        "scikit_learn_version": sklearn.__version__,
        "intended_use": (
            "A personal, educational estimate in the FoodScape Dallas health check: how likely "
            "someone with similar answers was to have obesity in the survey data, and which "
            "answers moved that estimate."
        ),
        "not_intended_for": [
            "Diagnosis or medical decisions. It is not medical advice.",
            "Estimating obesity rates for places. The map uses CDC PLACES for that.",
            "Decisions about other people (insurance, hiring, eligibility, and so on).",
        ],
        "training_data": {
            "source": (
                "UCI Machine Learning Repository: Estimation of Obesity Levels Based On Eating "
                "Habits and Physical Condition"
            ),
            "citation": "https://doi.org/10.24432/C5H31Z",
            "license": "CC BY 4.0",
            "rows_used": row_count,
            "countries": ["Mexico", "Peru", "Colombia"],
            "synthetic_share": 0.77,
            "notes": (
                "77% of rows were generated with SMOTE to balance the classes; 23% are survey "
                "responses. 24 exact duplicate rows were removed."
            ),
        },
        "target": (
            "1 if the person's obesity level is Obesity Type I, II, or III (assigned from BMI "
            "of 30 or more), otherwise 0"
        ),
        "features": [
            {"name": name, "description": FEATURE_DESCRIPTIONS[name]} for name in FEATURES
        ],
        "excluded_features": [
            {
                "name": name,
                "reason": "The label was assigned from BMI (weight / height squared), so these "
                "would leak the answer.",
            }
            for name in EXCLUDED_FEATURES
        ],
        "model": {
            "type": "Logistic regression (scikit-learn), with one-hot encoding and scaling",
            "regularization_C": search.best_params_["classifier__C"],
            "selection": (
                f"C chosen from {C_GRID} by 5-fold cross-validation on the training set "
                f"(ROC AUC {search.best_score_:.3f})"
            ),
            "train_rows": int(len(train_x)),
        },
        "test_metrics": results["test_metrics"],
        "test_metrics_survey_like_rows": {
            "description": (
                "The same test set, limited to rows whose answers are all whole numbers, which "
                "is what real survey responses look like (most synthetic rows have fractional "
                "answers). Closer to how the model does for real people. Small, so noisy."
            ),
            **survey,
        },
        "calibration": results["calibration"],
        "performance_by_group": results["groups"],
        "coefficients": results["coefficients"],
        "synthetic_data_effects": [
            (
                "The most severe class (Obesity Type III) is 323 women and 1 man, and all 324 "
                "rows answer 'always' to the vegetables question, are aged 18-26, and share 3 "
                "answer patterns: hundreds of generated copies of a few people."
            ),
            (
                f"As a result the model is much more accurate for women (ROC AUC "
                f"{by_sex['Female'].get('roc_auc')}) than for men (ROC AUC "
                f"{by_sex['Male'].get('roc_auc')}). Much of the women's score comes from "
                "recognizing that generated cluster, not from real patterns."
            ),
            (
                f"It also learned that eating vegetables more often raises the estimate "
                f"(coefficient {vegetables:+.2f}). That reflects the generated cluster, not "
                "health evidence, so the health check never presents it as advice."
            ),
            (
                f"On test rows that look like real survey responses (n={survey['n']}), ROC AUC is "
                f"{survey.get('roc_auc')}, compared with {results['test_metrics'].get('roc_auc')} "
                "on the full test set."
            ),
            (
                "Estimates run high for typical people: about 46% of training rows are obese, but "
                f"only {survey['obese_share']:.0%} of the survey-like test rows are, while the "
                f"model's average estimate for them is {survey['mean_predicted']:.0%}."
            ),
        ],
        "limitations": [
            "77% of the training data is synthetic (see synthetic_data_effects), and the real "
            "responses come from Mexico, Peru, and Colombia, not Dallas. Patterns may not carry "
            "over.",
            "The estimate is less accurate for men than for women.",
            "Respondents are young: the median age is about 23, and 95% are under 38. Estimates "
            "for older adults are less reliable, and there were no respondents over 61.",
            "Answers are self-reported, and the label comes from self-reported height and weight.",
            "The model finds associations, not causes. A factor that raises the estimate isn't "
            "necessarily something that causes obesity.",
            "BMI-based obesity is a population screening measure and doesn't describe any one "
            "person's health.",
        ],
    }


if __name__ == "__main__":
    main()
