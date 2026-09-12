"""Model families for per-job water consumption."""

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import LinearRegression

from data_loader import SEED


class GlobalMean(BaseEstimator, RegressorMixin):
    """Predict the training mean for every job."""

    def fit(self, X, y):
        self.mean_ = float(np.mean(y))
        return self

    def predict(self, X):
        return np.full(len(X), self.mean_)


class GroupMean(BaseEstimator, RegressorMixin):
    """Predict the training mean of each distinct feature row."""

    def fit(self, X, y):
        frame = pd.DataFrame(X).copy()
        self.columns_ = list(frame.columns)
        frame["_target"] = np.asarray(y)
        self.means_ = frame.groupby(self.columns_)["_target"].mean()
        self.fallback_ = float(np.mean(y))
        return self

    def predict(self, X):
        keys = pd.MultiIndex.from_frame(pd.DataFrame(X)[self.columns_])
        return self.means_.reindex(keys).fillna(self.fallback_).to_numpy()


class IntervalRegressor(BaseEstimator, RegressorMixin):
    """Wrap a regressor with residual-quantile prediction intervals.

    Residual spread is ~3 L on exterior jobs against ~8 L on interior ones, so the
    quantiles are held per job type instead of pooled into one misleading band.
    Calibrate on data the estimator was not fitted on.
    """

    def __init__(self, estimator, level=0.90):
        self.estimator = estimator
        self.level = level

    def fit(self, X, y):
        self.estimator.fit(X, y)
        return self

    def calibrate(self, X, y):
        residuals = np.asarray(y) - self.estimator.predict(X)
        interior = _interior_flag(X)
        lo_q, hi_q = (1 - self.level) / 2, (1 + self.level) / 2
        self.offsets_ = {
            group: (
                float(np.quantile(residuals[interior == group], lo_q)),
                float(np.quantile(residuals[interior == group], hi_q)),
            )
            for group in (0, 1)
        }
        return self

    def predict(self, X):
        return self.estimator.predict(X)

    def predict_interval(self, X):
        prediction = self.predict(X)
        interior = _interior_flag(X)
        lo = np.array([self.offsets_[g][0] for g in interior])
        hi = np.array([self.offsets_[g][1] for g in interior])
        return prediction + lo, prediction + hi


def _interior_flag(X):
    return pd.DataFrame(X)["interior_clean"].to_numpy().astype(int)


MODELS = {
    "global_mean": lambda: GlobalMean(),
    "size_mean": lambda: GroupMean(),
    "linear": lambda: LinearRegression(),
    "gbm": lambda: HistGradientBoostingRegressor(random_state=SEED),
}

# Ascending complexity, used to break near-ties in favour of the model that is
# easier to defend and to hand to the next module.
MODEL_ORDER = ["global_mean", "size_mean", "linear", "gbm"]


def build_model(name):
    if name not in MODELS:
        raise ValueError(f"unknown model {name!r}, expected one of {sorted(MODELS)}")
    return MODELS[name]()
