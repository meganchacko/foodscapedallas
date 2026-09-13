import itertools
import os
import warnings
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from ucimlrepo import fetch_ucirepo

class ObesityDataLoader:
    def __init__(self, uci_id: int = 544):
        self.uci_id = uci_id

    def load(self):
        dataset = fetch_ucirepo(id=self.uci_id)
        return dataset.data.features, dataset.data.targets


class ObesityPreprocessor:

    BINARY_COLUMNS = ['family_history_with_overweight', 'FAVC', 'SMOKE', 'SCC']
    ORDINAL_COLUMNS = ['CAEC', 'CALC']
    ORDINAL_MAP = {'no': 0, 'Sometimes': 1, 'Frequently': 2, 'Always': 3}

    OBESITY_ORDER = {
        'Insufficient_Weight': 0,
        'Normal_Weight': 1,
        'Overweight_Level_I': 2,
        'Overweight_Level_II': 3,
        'Obesity_Type_I': 4,
        'Obesity_Type_II': 5,
        'Obesity_Type_III': 6,
    }
    TARGET_COLUMN = 'NObeyesdad'

    def __init__(self, low_corr_threshold: float = 0.05):
        self.low_corr_threshold = low_corr_threshold
        self.scaler = StandardScaler()
        self.dropped_columns_ = []
        self.feature_names_ = []

    def fit_transform(self, X: pd.DataFrame, y: pd.DataFrame):
        df = pd.concat([X, y], axis=1)
        df = df.dropna()
        df = df.drop_duplicates()

        df['Gender'] = df['Gender'].map({'Female': 0, 'Male': 1})
        for col in self.BINARY_COLUMNS:
            df[col] = df[col].map({'yes': 1, 'no': 0})
        for col in self.ORDINAL_COLUMNS:
            df[col] = df[col].map(self.ORDINAL_MAP)

        df = pd.get_dummies(df, columns=['MTRANS'], prefix='MTRANS', drop_first=True)
        mtrans_cols = [c for c in df.columns if c.startswith('MTRANS_')]
        df[mtrans_cols] = df[mtrans_cols].astype(int)

        df[self.TARGET_COLUMN] = df[self.TARGET_COLUMN].map(self.OBESITY_ORDER)

        df = df.drop(columns=['Weight'])

        correlations = df.corr(numeric_only=True)[self.TARGET_COLUMN].drop(self.TARGET_COLUMN)
        self.dropped_columns_ = correlations[correlations.abs() < self.low_corr_threshold].index.tolist()
        df = df.drop(columns=self.dropped_columns_)

        y_clean = df[self.TARGET_COLUMN]
        X_clean = df.drop(columns=[self.TARGET_COLUMN])
        self.feature_names_ = X_clean.columns.tolist()

        X_scaled = pd.DataFrame(
            self.scaler.fit_transform(X_clean), columns=X_clean.columns, index=X_clean.index
        )
        return X_scaled, y_clean


class RegressionEvaluator:
    @staticmethod
    def mse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        return float(np.mean((y_true - y_pred) ** 2))

    @staticmethod
    def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        return float(np.sqrt(RegressionEvaluator.mse(y_true, y_pred)))

    @staticmethod
    def r2(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        ss_res = np.sum((y_true - y_pred) ** 2)
        ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
        return float(1 - ss_res / ss_tot)

    @staticmethod
    def explained_variance(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        residual = y_true - y_pred
        return float(1 - np.var(residual) / np.var(y_true))

    @classmethod
    def evaluate(cls, y_true: np.ndarray, y_pred: np.ndarray) -> dict:
        return {
            'mse': cls.mse(y_true, y_pred),
            'rmse': cls.rmse(y_true, y_pred),
            'r2': cls.r2(y_true, y_pred),
            'explained_variance': cls.explained_variance(y_true, y_pred),
        }


class LinearRegressionGD:
    def __init__(self, learning_rate: float = 0.01, n_iterations: int = 1000, tol: float = 1e-6):
        self.learning_rate = learning_rate
        self.n_iterations = n_iterations
        self.tol = tol
        self.weights_ = None
        self.bias_ = None
        self.cost_history_ = []

    def fit(self, X: np.ndarray, y: np.ndarray) -> 'LinearRegressionGD':
        n_samples, n_features = X.shape
        self.weights_ = np.zeros(n_features)
        self.bias_ = 0.0
        self.cost_history_ = []

        for _ in range(self.n_iterations):
            y_pred = X @ self.weights_ + self.bias_
            error = y_pred - y
            cost = np.mean(error ** 2)
            self.cost_history_.append(cost)

            if len(self.cost_history_) > 1 and abs(self.cost_history_[-2] - self.cost_history_[-1]) < self.tol:
                break

            dw = (2 / n_samples) * (X.T @ error)
            db = (2 / n_samples) * np.sum(error)
            self.weights_ -= self.learning_rate * dw
            self.bias_ -= self.learning_rate * db

        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        return X @ self.weights_ + self.bias_


class GridSearchLogger:
    """Grid-searches a model's hyperparameters, logging every trial's
    parameters, training error, and test error to a file on disk.
    """

    def __init__(self, model_factory, log_path: str, divergence_factor: float = 10.0):
        self.model_factory = model_factory
        self.log_path = log_path
        self.divergence_factor = divergence_factor
        self.trials_ = []

    def run(self, param_grid: dict, X_train: np.ndarray, y_train: np.ndarray,
            X_test: np.ndarray, y_test: np.ndarray) -> list:
        keys = list(param_grid.keys())
        combos = list(itertools.product(*param_grid.values()))
        self.trials_ = []

        baseline_mse = RegressionEvaluator.mse(y_train, np.full_like(y_train, y_train.mean(), dtype=float))
        divergence_threshold = baseline_mse * self.divergence_factor

        with open(self.log_path, 'w') as log_file:
            log_file.write(','.join(keys) + ',train_mse,test_mse,status\n')

            for combo in combos:
                params = dict(zip(keys, combo))
                model = self.model_factory(**params)

                try:
                    model.fit(X_train, y_train)
                    train_mse = RegressionEvaluator.mse(y_train, model.predict(X_train))
                    test_mse = RegressionEvaluator.mse(y_test, model.predict(X_test))
                    finite = np.isfinite(train_mse) and np.isfinite(test_mse)
                    diverged = not finite or train_mse > divergence_threshold or test_mse > divergence_threshold
                except (ValueError, FloatingPointError, ArithmeticError):
                    train_mse, test_mse, diverged = float('nan'), float('nan'), True

                status = 'diverged' if diverged else 'ok'
                log_file.write(','.join(str(params[k]) for k in keys) + f',{train_mse},{test_mse},{status}\n')

                self.trials_.append({
                    'params': params,
                    'model': model,
                    'train_mse': train_mse,
                    'test_mse': test_mse,
                    'diverged': diverged,
                })

        return self.trials_


    def best(self, metric: str = 'test_mse') -> dict:
        valid_trials = [t for t in self.trials_ if not t['diverged']]
        if not valid_trials:
            raise ValueError('No trial converged - widen or shift the parameter grid.')
        return min(valid_trials, key=lambda t: t[metric])


class RegressionPlotter:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def _save(self, fig, filename: str) -> str:
        path = os.path.join(self.output_dir, filename)
        fig.savefig(path, bbox_inches='tight')
        plt.close(fig)
        return path

    def plot_cost_history(self, cost_history: list, title: str, filename: str) -> str:
        fig, ax = plt.subplots()
        ax.plot(cost_history)
        ax.set_xlabel('Iteration')
        ax.set_ylabel('MSE Cost')
        ax.set_title(title)
        return self._save(fig, filename)

    def plot_predicted_vs_actual(self, y_true: np.ndarray, y_pred: np.ndarray,
                                  title: str, filename: str) -> str:
        fig, ax = plt.subplots()
        ax.scatter(y_true, y_pred, alpha=0.4)
        lims = [min(y_true.min(), y_pred.min()), max(y_true.max(), y_pred.max())]
        ax.plot(lims, lims, 'r--', label='Perfect prediction')
        ax.set_xlabel('Actual Obesity Level')
        ax.set_ylabel('Predicted Obesity Level')
        ax.set_title(title)
        ax.legend()
        return self._save(fig, filename)

    def plot_feature_vs_target(self, feature_values: np.ndarray, y_true: np.ndarray,
                                feature_name: str, title: str, filename: str) -> str:
        fig, ax = plt.subplots()
        ax.scatter(feature_values, y_true, alpha=0.4)
        ax.set_xlabel(feature_name)
        ax.set_ylabel('Obesity Level')
        ax.set_title(title)
        return self._save(fig, filename)

    def plot_weight_coefficients(self, feature_names: list, weights: np.ndarray,
                                  title: str, filename: str) -> str:
        order = np.argsort(np.abs(weights))
        fig, ax = plt.subplots(figsize=(6, max(3, 0.4 * len(feature_names))))
        ax.barh([feature_names[i] for i in order], weights[order])
        ax.set_xlabel('Weight Coefficient')
        ax.set_title(title)
        return self._save(fig, filename)


def main():
    warnings.filterwarnings('ignore', category=RuntimeWarning)

    X_raw, y_raw = ObesityDataLoader().load()

    preprocessor = ObesityPreprocessor()
    X, y = preprocessor.fit_transform(X_raw, y_raw)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    X_train_np, X_test_np = X_train.to_numpy(), X_test.to_numpy()
    y_train_np, y_test_np = y_train.to_numpy(), y_test.to_numpy()

    param_grid = {
        'learning_rate': [0.001, 0.01, 0.1, 0.5, 1.0],
        'n_iterations': [500, 1000, 5000],
    }
    tuner = GridSearchLogger(model_factory=LinearRegressionGD, log_path='logs/part1_log.txt')
    tuner.run(param_grid, X_train_np, y_train_np, X_test_np, y_test_np)
    best_trial = tuner.best(metric='test_mse')
    model = best_trial['model']

    print('=== Part 1: Linear Regression via Hand-Written Gradient Descent ===')
    print(f'Best hyperparameters: {best_trial["params"]}')

    train_metrics = RegressionEvaluator.evaluate(y_train_np, model.predict(X_train_np))
    test_metrics = RegressionEvaluator.evaluate(y_test_np, model.predict(X_test_np))
    print(f'Train metrics: {train_metrics}')
    print(f'Test metrics:  {test_metrics}')
    print(f'Bias: {model.bias_:.4f}')
    for name, weight in zip(preprocessor.feature_names_, model.weights_):
        print(f'  {name}: {weight:.4f}')

    plotter = RegressionPlotter(output_dir='plots/part1')
    plotter.plot_cost_history(
        model.cost_history_, 'Part 1: MSE vs Iterations', 'mse_vs_iterations.png'
    )
    plotter.plot_predicted_vs_actual(
        y_test_np, model.predict(X_test_np),
        'Part 1: Predicted vs Actual Obesity Level (Test Set)', 'predicted_vs_actual.png'
    )
    plotter.plot_weight_coefficients(
        preprocessor.feature_names_, model.weights_,
        'Part 1: Learned Weight Coefficients', 'weight_coefficients.png'
    )

    top_feature = max(
        preprocessor.feature_names_, key=lambda f: abs(np.corrcoef(X[f], y)[0, 1])
    )
    plotter.plot_feature_vs_target(
        X_test[top_feature].to_numpy(), y_test_np, top_feature,
        f'Part 1: Obesity Level vs {top_feature}', 'feature_vs_target.png'
    )

if __name__ == '__main__':
    main()
