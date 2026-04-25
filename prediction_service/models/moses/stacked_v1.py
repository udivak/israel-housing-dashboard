"""
Stacked ensemble — LightGBM + CatBoost + weight optimization.

זרימה:
    1. מאמן LightGBM ו-CatBoost על train (log target)
    2. מוצא משקל w∈[0,1] שממזער MAPE על val: w·lgb + (1-w)·cat
    3. בחיזוי: ממוצע משוקלל של שני המודלים

הבחירה לא ב-Ridge כי הוא ניסה לתת אינטרספט שלילי ולשבש את ה-scale.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import lightgbm as lgb
from catboost import CatBoostRegressor

CAT_FEATURES = ["city", "deal_nature"]

LGB_PARAMS = dict(
    n_estimators=10000, learning_rate=0.01, num_leaves=511,
    min_child_samples=5, subsample=0.8, colsample_bytree=0.8,
    reg_alpha=0.01, reg_lambda=0.01,
    random_state=42, n_jobs=-1, verbose=-1,
)

CAT_PARAMS = dict(
    iterations=5000, depth=10, learning_rate=0.02,
    loss_function="RMSE", random_seed=42,
    od_type="Iter", od_wait=150, verbose=False,
)


def _prep_for_catboost(X: pd.DataFrame) -> pd.DataFrame:
    X = X.copy()
    for c in CAT_FEATURES:
        if c in X.columns:
            X[c] = X[c].astype(str).fillna("NA")
    return X


def train(X_train, y_train, X_val, y_val):
    yt = np.log1p(y_train)
    yv = np.log1p(y_val)

    print("  [stacked] training LightGBM...")
    lgbm = lgb.LGBMRegressor(**LGB_PARAMS)
    lgbm.fit(X_train, yt, eval_set=[(X_val, yv)],
             eval_metric="mape",
             callbacks=[lgb.early_stopping(150, verbose=False)])

    print("  [stacked] training CatBoost...")
    X_train_cb = _prep_for_catboost(X_train)
    X_val_cb = _prep_for_catboost(X_val)
    cat = [c for c in CAT_FEATURES if c in X_train_cb.columns]
    cb = CatBoostRegressor(cat_features=cat, **CAT_PARAMS)
    cb.fit(X_train_cb, yt, eval_set=(X_val_cb, yv), use_best_model=True)

    print("  [stacked] searching best weight on val...")
    p_lgb_val = np.expm1(lgbm.predict(X_val))
    p_cat_val = np.expm1(cb.predict(X_val_cb))

    best_w, best_mape = None, np.inf
    for w in np.linspace(0, 1, 21):  # 0.00, 0.05, ..., 1.00
        blend = w * p_lgb_val + (1 - w) * p_cat_val
        mape = np.mean(np.abs(blend - y_val) / y_val)
        if mape < best_mape:
            best_mape = mape
            best_w = w
    print(f"  [stacked] best weight: lgb={best_w:.2f}  cat={1-best_w:.2f}  "
          f"val_mape={best_mape:.4f}")

    return {"lgbm": lgbm, "cb": cb, "w": best_w}


def predict(model, X):
    p_lgb = np.expm1(model["lgbm"].predict(X))
    p_cat = np.expm1(model["cb"].predict(_prep_for_catboost(X)))
    return model["w"] * p_lgb + (1 - model["w"]) * p_cat
