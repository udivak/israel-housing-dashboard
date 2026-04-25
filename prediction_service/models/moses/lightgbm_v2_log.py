"""
LightGBM v2 — log-target.

מתאמן על log(real_price) ומחזיר את התחזית לסקייל המקורי. מחירי דיור הם log-normal;
אימון על log בד"כ משפר MAPE.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import lightgbm as lgb

PARAMS = dict(
    n_estimators=5000,
    learning_rate=0.03,
    num_leaves=127,
    min_child_samples=20,
    subsample=0.8,
    colsample_bytree=0.8,
    reg_alpha=0.1,
    reg_lambda=0.1,
    random_state=42,
    n_jobs=-1,
    verbose=-1,
)


def train(X_train, y_train, X_val, y_val):
    y_train_log = np.log1p(y_train)
    y_val_log = np.log1p(y_val)

    model = lgb.LGBMRegressor(**PARAMS)
    model.fit(
        X_train, y_train_log,
        eval_set=[(X_val, y_val_log)],
        eval_metric="mape",
        callbacks=[lgb.early_stopping(100), lgb.log_evaluation(200)],
    )
    return model


def predict(model, X):
    return np.expm1(model.predict(X))
