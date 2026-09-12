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

    Calibrate on data the estimator was not fitted on, otherwise the band reports the
    nominal level back by construction.
    """

    def __init__(self, estimator, level=0.90):
        self.estimator = estimator
        self.level = level

    def fit(self, X, y):
        self.estimator.fit(X, y)
        return self

    def calibrate(self, X, y):
        residuals = np.asarray(y) - self.estimator.predict(X)
        lo_q, hi_q = (1 - self.level) / 2, (1 + self.level) / 2
        self.offsets_ = (
            float(np.quantile(residuals, lo_q)),
            float(np.quantile(residuals, hi_q)),
        )
        return self

    def predict(self, X):
        return self.estimator.predict(X)

    def predict_interval(self, X):
        prediction = self.predict(X)
        return prediction + self.offsets_[0], prediction + self.offsets_[1]


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
