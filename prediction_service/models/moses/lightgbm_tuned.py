"""
LightGBM tuned — הכי טוב שיצא לי עד עכשיו.
log target + עצים עמוקים + lr איטי.

test MAPE ≈ 0.188  |  R² ≈ 0.80
"""
from __future__ import annotations

import numpy as np
import lightgbm as lgb

PARAMS = dict(
    n_estimators=10000,
    learning_rate=0.01,
    num_leaves=511,
    min_child_samples=5,
    subsample=0.8,
    colsample_bytree=0.8,
    reg_alpha=0.01,
    reg_lambda=0.01,
    random_state=42,
    n_jobs=-1,
    verbose=-1,
)


def train(X_train, y_train, X_val, y_val):
    yt = np.log1p(y_train)
    yv = np.log1p(y_val)
    model = lgb.LGBMRegressor(**PARAMS)
    model.fit(
        X_train, yt,
        eval_set=[(X_val, yv)],
        eval_metric="mape",
        callbacks=[lgb.early_stopping(150), lgb.log_evaluation(200)],
    )
    return model


def predict(model, X):
    return np.expm1(model.predict(X))
