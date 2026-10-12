# Health check model

Logistic regression that estimates the likelihood of obesity (yes/no) from habits and background. It powers the health check (`POST /health-check`); it is never used for the map.

```bash
pip install -r ml/requirements.txt
python -m ml.train          # from the repo root
```

`train.py` reads `data/obesity.csv` (see `data/README.md`) and writes:

- `model/obesity_model.joblib`: the fitted scikit-learn pipeline (one-hot encoding + scaling + logistic regression), plus the average of each encoded column, which the API uses to explain estimates.
- `model/model_card.json`: training data, inputs, metrics, performance by sex and age, calibration, coefficients, the effects of the synthetic data, and limitations. Shown in the app's model card page.

How it's built:

- **No height or weight.** The label was assigned from BMI, so they would leak the answer.
- **Target:** obese (Obesity Type I-III) vs. not. About 46% of rows are obese.
- **No leakage from the test set:** duplicates are removed before splitting; encoding and scaling happen inside the pipeline; the regularization strength is chosen by 5-fold cross-validation on the training set; the test set (20%) is used once.
- **Reproducible:** fixed random seed, the dataset is committed, and versions are pinned. The backend pins the same versions (a saved scikit-learn model can break under a different version).

The model is trained on all rows, including the 77% that are synthetic. The model card documents what that does: much better accuracy for women than men, and some backwards associations (more vegetables goes with a higher estimate). The API only suggests a habit change when the model says the healthier answer would actually lower the estimate, so those artifacts are never turned into advice.

`v1_linear_regression/` is the original model, kept for comparison.
