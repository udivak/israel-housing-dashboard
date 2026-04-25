"""
CatBoost v1 — deep_slow config (הטוב מבין 4).
test MAPE ≈ 0.194 — מעט גרוע מ-lightgbm_tuned (0.188).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from catboost import CatBoostRegressor

CAT_FEATURES = ["city", "deal_nature"]


def _prep(X: pd.DataFrame) -> pd.DataFrame:
    X = X.copy()
    for c in CAT_FEATURES:
        if c in X.columns:
            X[c] = X[c].astype(str).fillna("NA")
    return X


def train(X_train, y_train, X_val, y_val):
    X_train = _prep(X_train)
    X_val = _prep(X_val)
    cat = [c for c in CAT_FEATURES if c in X_train.columns]

    model = CatBoostRegressor(
        iterations=5000,
        depth=10,
        learning_rate=0.02,
        loss_function="RMSE",
        cat_features=cat,
        random_seed=42,
        od_type="Iter", od_wait=150,
        verbose=200,
    )
    model.fit(X_train, np.log1p(y_train),
              eval_set=(X_val, np.log1p(y_val)),
              use_best_model=True)
    return model


def predict(model, X):
    return np.expm1(model.predict(_prep(X)))
