"""XGBoost v2 — native categorical + MAPE-aware early stopping.

Diffs vs v1:
    1. אין יותר ColumnTransformer/OrdinalEncoder. מעבירים DataFrame גולמי
       ל-XGBRegressor(enable_categorical=True, tree_method="hist") שמטפל בקטגוריות
       ובחסרים native (split direction default).
    2. Early-stopping על MAPE בסקלה האמיתית (callable eval_metric) במקום RMSE
       על log1p — זה מה שמסנכרן בין הסלקציה לבין metric של ה-leaderboard.
    3. מיישרים cat.categories בין train/val/test לפני האימון. ב-data_v2.py
       `select_features` נקרא בנפרד לכל פרוסה → pandas מחשב Categorical שונה
       על כל פרוסה. בלי יישור, native-cat XGB יפרש קוד 7 ב-train ובטסט בתור
       קטגוריות *שונות* בלי לזרוק שגיאה (silent correctness bug).
    4. Drop של 4 פיצ'רים ב-importance==0.0 ב-v1: is_old, is_new,
       is_new_project, real_price_imputed.
    5. Candidate grid הוסר xgb_fast (lr גבוה מדי), הוסר xgb_slow_wide
       (overfitter); נוספו xgb_deep_reg ו-xgb_mid_reg עם רגולריזציה חזקה יותר.

כדי להפעיל:
    python run.py udi/xgboost_v2 --data v2
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from xgboost import XGBRegressor  # pyright: ignore[reportMissingImports]
from xgboost.callback import EarlyStopping  # pyright: ignore[reportMissingImports]

RANDOM_STATE = 42

ARTIFACTS_DIR = (
    Path(__file__).resolve().parents[2] / "artifacts" / "udi" / "xgboost_v2"
)

CAT_COLS: tuple[str, ...] = ("city", "neighborhood", "deal_nature")

# 4 פיצ'רים שב-v1 קיבלו importance==0.0 בדיוק. real_price_imputed מתווסף ב-
# data_v2.clean רק כשהיו NaN ב-target — לכן drop רק אם העמודה קיימת.
DEAD_COLS: tuple[str, ...] = (
    "is_old",
    "is_new",
    "is_new_project",
    "real_price_imputed",
)

# שותף לכל ה-candidates. eval_metric עוברת ל-mape_real_scale (callable);
# eval_metric="rmse" של v1 הוסר — XGB ≥ 2.0 רוצה רק אחד.
#
# שימו לב: ב-xgboost 3.x ה-`early_stopping_rounds` של ה-constructor מניח
# maximize=True כש-eval_metric הוא callable (אין הסקה אוטומטית מהשם של
# הפונקציה). זה גורם ל-best_iter=0 כי ה-MAPE שלנו יורד עם האימון. הפתרון —
# callback EarlyStopping מפורש עם maximize=False; כל candidate מקבל מופע
# חדש (אסור לחלוק callback בין fits).
COMMON: dict[str, Any] = {
    "n_estimators": 4000,
    "tree_method": "hist",
    "enable_categorical": True,
    "n_jobs": -1,
    "random_state": RANDOM_STATE,
    "objective": "reg:squarederror",
}

EARLY_STOPPING_ROUNDS = 150

CANDIDATES: tuple[tuple[str, dict[str, Any]], ...] = (
    (
        "xgb_balanced",
        {
            "max_depth": 8,
            "learning_rate": 0.05,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "reg_lambda": 1.0,
            "reg_alpha": 0.01,
            "min_child_weight": 3,
        },
    ),
    (
        "xgb_deep",
        {
            "max_depth": 10,
            "learning_rate": 0.03,
            "subsample": 0.8,
            "colsample_bytree": 0.7,
            "reg_lambda": 2.0,
            "reg_alpha": 0.05,
            "min_child_weight": 3,
        },
    ),
    (
        "xgb_regularized",
        {
            "max_depth": 8,
            "learning_rate": 0.03,
            "subsample": 0.7,
            "colsample_bytree": 0.6,
            "reg_lambda": 5.0,
            "reg_alpha": 0.5,
            "min_child_weight": 10,
        },
    ),
    (
        "xgb_deep_reg",
        {
            "max_depth": 10,
            "learning_rate": 0.03,
            "subsample": 0.8,
            "colsample_bytree": 0.7,
            "reg_lambda": 3.0,
            "reg_alpha": 0.05,
            "min_child_weight": 8,
        },
    ),
    (
        "xgb_mid_reg",
        {
            "max_depth": 8,
            "learning_rate": 0.04,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "reg_lambda": 2.0,
            "reg_alpha": 0.05,
            "min_child_weight": 10,
            "gamma": 0.1,
        },
    ),
)


def _mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    mask = y_true > 0
    return float(np.mean(np.abs(y_pred[mask] - y_true[mask]) / y_true[mask]))


def mape_real_scale(y_true_log: np.ndarray, y_pred_log: np.ndarray) -> float:
    """
    eval_metric callable עבור XGB ≥ 2.0 sklearn API.
    הקלט הוא log1p(y) (כי זה מה שהזרקנו ל-fit); מחזירים MAPE בסקלה האמיתית.
    XGB ממזער ערך סקלרי מ-callable → early stopping ירדוף את ה-MAPE עצמה,
    לא את ה-RMSLE (כמו ב-v1).
    """
    y_true = np.expm1(y_true_log)
    y_pred = np.maximum(np.expm1(y_pred_log), 1.0)
    mask = y_true > 0
    if not mask.any():
        return float("nan")
    return float(np.mean(np.abs(y_pred[mask] - y_true[mask]) / y_true[mask]))


def _align_categories(
    X_train: pd.DataFrame, X_val: pd.DataFrame, X_test: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, pd.Index]]:
    """
    נוגע רק ב-CAT_COLS שקיימות. ב-data_v2 הן כבר מומרות ל-Categorical *לחוד*
    בכל פרוסה — אנחנו דוחפים את ה-categories של train גם ל-val ול-test.
    ערכים שלא קיימים ב-train הופכים ל-NaN (ולא ל-int code אקראי) — XGB
    enable_categorical יודע לטפל ב-NaN של category.
    """
    X_train = X_train.copy()
    X_val = X_val.copy()
    X_test = X_test.copy()

    cat_categories: dict[str, pd.Index] = {}
    for c in CAT_COLS:
        if c not in X_train.columns:
            continue
        cats = X_train[c].astype("category").cat.categories
        cat_categories[c] = cats
        X_train[c] = pd.Categorical(X_train[c], categories=cats)
        if c in X_val.columns:
            X_val[c] = pd.Categorical(X_val[c], categories=cats)
        if c in X_test.columns:
            X_test[c] = pd.Categorical(X_test[c], categories=cats)
    return X_train, X_val, X_test, cat_categories


def _drop_dead(X: pd.DataFrame, dropped_cols: list[str]) -> pd.DataFrame:
    return X.drop(columns=[c for c in dropped_cols if c in X.columns])


def train(
    X_train: pd.DataFrame,
    y_train: np.ndarray,
    X_val: pd.DataFrame,
    y_val: np.ndarray,
) -> dict[str, Any]:
    """אימון של כל ה-candidates; מחזיר dict עם הזוכה לפי MAPE על val."""
    y_train_log = np.log1p(y_train)
    y_val_log = np.log1p(y_val)

    # יישור categories — קריטי כש-enable_categorical=True. בלי זה, code 7
    # ב-train יכול להתחפש לעיר אחרת ב-val. אנחנו נצרוך את X_test רק בזמן
    # predict — אז כאן אנחנו מאחדים train ⇄ val ושומרים את categories
    # כדי לדחוף אותם גם על X_test ב-predict().
    X_train_a, X_val_a, _, cat_categories = _align_categories(
        X_train, X_val, X_val.iloc[:0]  # placeholder — predict idoes the rest
    )

    dropped_cols = [c for c in DEAD_COLS if c in X_train_a.columns]
    if dropped_cols:
        print(f"  [xgboost_v2] dropping dead features: {dropped_cols}")
    X_train_a = _drop_dead(X_train_a, dropped_cols)
    X_val_a = _drop_dead(X_val_a, dropped_cols)

    best_booster: XGBRegressor | None = None
    best_result: dict[str, Any] | None = None
    results: list[dict[str, Any]] = []

    for name, params in CANDIDATES:
        print(f"  [xgboost_v2] training {name}...")
        booster = XGBRegressor(
            **COMMON,
            eval_metric=mape_real_scale,
            callbacks=[
                EarlyStopping(rounds=EARLY_STOPPING_ROUNDS, maximize=False)
            ],
            **params,
        )
        booster.fit(
            X_train_a,
            y_train_log,
            eval_set=[(X_val_a, y_val_log)],
            verbose=False,
        )

        val_pred_log = booster.predict(X_val_a)
        val_pred = np.maximum(np.expm1(val_pred_log), 1.0)
        val_mape = _mape(y_val, val_pred)
        best_iter = int(getattr(booster, "best_iteration", booster.n_estimators))

        result = {
            "name": name,
            "params": params,
            "val_mape": val_mape,
            "best_iteration": best_iter,
        }
        results.append(result)
        print(
            f"  [xgboost_v2] {name} val_mape={val_mape:.4f}  best_iter={best_iter}"
        )

        if best_result is None or val_mape < best_result["val_mape"]:
            best_booster = booster
            best_result = result

    if best_booster is None or best_result is None:
        raise RuntimeError("No XGBoost candidates were trained.")

    feature_names = list(X_train_a.columns)
    importances_df = (
        pd.DataFrame(
            {"column": feature_names, "importance": best_booster.feature_importances_}
        )
        .sort_values("importance", ascending=False)
        .reset_index(drop=True)
    )

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    (ARTIFACTS_DIR / "candidate_results.json").write_text(
        json.dumps(results, indent=2)
    )
    importances_df.to_csv(ARTIFACTS_DIR / "feature_importances.csv", index=False)

    print(
        "  [xgboost_v2] best="
        f"{best_result['name']} val_mape={best_result['val_mape']:.4f}  "
        f"best_iter={best_result['best_iteration']}"
    )

    return {
        "model": best_booster,
        "dropped_cols": dropped_cols,
        "cat_categories": cat_categories,
        "candidate_results": results,
        "best_candidate": best_result,
    }


def predict(model: dict[str, Any], X: pd.DataFrame) -> np.ndarray:
    """
    מיישר categories של train על X חדש (test/serving) ואז predict + clamp.
    ערכי-עיר/שכונה שלא נראו ב-train הופכים ל-NaN — XGB enable_categorical
    יטפל בהם דרך default split direction (כמו missing).
    """
    X = X.copy()
    for c, cats in model["cat_categories"].items():
        if c in X.columns:
            X[c] = pd.Categorical(X[c], categories=cats)
    X = X.drop(columns=[c for c in model["dropped_cols"] if c in X.columns])
    return np.maximum(np.expm1(model["model"].predict(X)), 1.0)
