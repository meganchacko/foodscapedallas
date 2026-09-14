# obesity-linear-regression
Linear regression model to predict likelihood of obesity in subjects based on eating habits and physical conditions.

## Setup

Dataset is fetched live from UCI, via uciml package.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running

Scripts to run both models, for parts 1 and 2 of assignment. Logs/plots are automatically saved in their respective folder.
Logs include every trial's parameters, training error, and test error.
Plots include the cost-history convergence curve, scatter plot of actual vs. predicted, scatter plot of feature vs. target (for the most correlated feature), and a bar chart of weight coefficients.

```bash
python part1.py   
python part2.py        
```

## Libraries used

- `numpy` was used for array math, and logic for gradient descent math in part 1
- `pandas` was used for loading and pre-processing of the dataset
- `scikit-learn`, `StandardScaler`, and `train_test_split`, `SGDRegressor` were used for the regression model in part 2
- `matplotlib` was used for making the plots
- `ucimlrepo` was used to fetch the obesity dataset from the UCI repository