"""
Stacked v2 — LightGBM+KNN + CatBoost עם משקלי-MAPE אופטימליים.

ההבדל מ-stacked_v1: ה-LightGBM הוחלף בגרסה עם KNN features. אם ה-KNN עזרה,
ה-stacking הזה אמור לתת את הציון הטוב ביותר עד כה.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import lightgbm as lgb
from catboost import CatBoostRegressor

from models.moses.lightgbm_knn import (
    LGB_PARAMS, KnnFeatureBuilder, _oof_train_features
)

CAT_FEATURES = ["city", "deal_nature"]
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

    print("  [stacked_v2] building KNN features...")
    train_knn = _oof_train_features(X_train, y_train)
    builder = KnnFeatureBuilder()
    builder.fit(X_train, y_train)
    val_knn = builder.transform(X_val)

    X_train_aug = pd.concat([X_train, train_knn], axis=1)
    X_val_aug = pd.concat([X_val, val_knn], axis=1)

    print("  [stacked_v2] training LightGBM (with KNN)...")
    lgbm = lgb.LGBMRegressor(**LGB_PARAMS)
    lgbm.fit(X_train_aug, yt, eval_set=[(X_val_aug, yv)],
             eval_metric="mape",
             callbacks=[lgb.early_stopping(150, verbose=False)])

    print("  [stacked_v2] training CatBoost...")
    X_train_cb = _prep_for_catboost(X_train_aug)
    X_val_cb = _prep_for_catboost(X_val_aug)
    cat = [c for c in CAT_FEATURES if c in X_train_cb.columns]
    cb = CatBoostRegressor(cat_features=cat, **CAT_PARAMS)
    cb.fit(X_train_cb, yt, eval_set=(X_val_cb, yv), use_best_model=True)

    print("  [stacked_v2] searching best weight on val...")
    p_lgb_val = np.expm1(lgbm.predict(X_val_aug))
    p_cat_val = np.expm1(cb.predict(X_val_cb))
    best_w, best_mape = None, np.inf
    for w in np.linspace(0, 1, 21):
        blend = w * p_lgb_val + (1 - w) * p_cat_val
        mape = np.mean(np.abs(blend - y_val) / y_val)
        if mape < best_mape:
            best_mape = mape
            best_w = w
    print(f"  [stacked_v2] best weight: lgb={best_w:.2f}  cat={1-best_w:.2f}  "
          f"val_mape={best_mape:.4f}")

    return {"lgbm": lgbm, "cb": cb, "w": best_w, "builder": builder}


def predict(model, X):
    knn = model["builder"].transform(X)
    X_aug = pd.concat([X, knn], axis=1)
    p_lgb = np.expm1(model["lgbm"].predict(X_aug))
    p_cat = np.expm1(model["cb"].predict(_prep_for_catboost(X_aug)))
    return model["w"] * p_lgb + (1 - model["w"]) * p_cat
