"""XGBoost v1 — סריקת 5 candidates על loader v2 עם early stopping.

מקבילה ל-random_forest_v2.py, אבל עם XGBRegressor במקום RandomForest. הפיצ'רים
מטופלים באותו preprocessor (median imputer לנומריים, OrdinalEncoder לקטגוריות)
כדי שההשוואה ל-RF תהיה apples-to-apples — את ה-native XGB categorical (
enable_categorical=True) שומרים ל-xgboost_v2.

Train pattern:
    1. fit ה-preprocessor פעם אחת.
    2. transform → X_train_t / X_val_t.
    3. XGBRegressor(early_stopping_rounds=...).fit עם eval_set על המטריצה
       המעובדת (כך booster מקבל ישירות את ה-validation מטריצה — בלי לעבור
       דרך Pipeline.fit(...model__eval_set=...) שמדיף ב-xgboost ≥ 2.0).
    4. עוטפים post-hoc ב-Pipeline כדי ש-joblib.dump / model.predict יקבלו
       את אותו interface כמו RF v2 (preprocess → model).

כדי להפעיל:
    python run.py udi/xgboost_v1 --data v2
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer  # pyright: ignore[reportMissingImports]
from sklearn.impute import SimpleImputer  # pyright: ignore[reportMissingImports]
from sklearn.pipeline import Pipeline  # pyright: ignore[reportMissingImports]
from sklearn.preprocessing import (  # pyright: ignore[reportMissingImports]
    FunctionTransformer,
    OrdinalEncoder,
)
from xgboost import XGBRegressor  # pyright: ignore[reportMissingImports]

RANDOM_STATE = 42

ARTIFACTS_DIR = (
    Path(__file__).resolve().parents[2] / "artifacts" / "udi" / "xgboost_v1"
)

CATEGORICAL_COLS = ("city", "neighborhood", "deal_nature")

# שותף לכל ה-candidates. early_stopping_rounds חייב להיות constructor-arg ב-
# xgboost ≥ 2.0 — להעביר אותו ל-fit() מרים TypeError.
COMMON: dict[str, Any] = {
    "n_estimators": 4000,
    "tree_method": "hist",
    "n_jobs": -1,
    "random_state": RANDOM_STATE,
    "objective": "reg:squarederror",
    "eval_metric": "rmse",
    "early_stopping_rounds": 100,
}

CANDIDATES: tuple[tuple[str, dict[str, Any]], ...] = (
    (
        "xgb_fast",
        {
            "max_depth": 6,
            "learning_rate": 0.1,
            "subsample": 0.9,
            "colsample_bytree": 0.9,
            "reg_lambda": 1.0,
            "reg_alpha": 0.0,
            "min_child_weight": 5,
        },
    ),
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
        "xgb_slow_wide",
        {
            "max_depth": 12,
            "learning_rate": 0.02,
            "subsample": 0.85,
            "colsample_bytree": 0.85,
            "reg_lambda": 1.0,
            "reg_alpha": 0.0,
            "min_child_weight": 2,
        },
    ),
)


def _mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    mask = y_true > 0
    return float(np.mean(np.abs(y_pred[mask] - y_true[mask]) / y_true[mask]))


def _to_object_str(df: pd.DataFrame) -> pd.DataFrame:
    """
    קטגוריות-pandas מומרות ל-object כדי ש-NaN ישרוד (אם נמיר ישירות ל-str,
    NaN הופך ל-'nan' מחרוזתי — ואז SimpleImputer לא יראה את ערכי-החסר).
    """
    return df.astype(object)


def _make_preprocessor(X: pd.DataFrame) -> ColumnTransformer:
    """
    קטגוריות → most_frequent imputer + OrdinalEncoder (-1 ל-unknown).
    נומריות → median imputer בלבד.
    """
    cat_cols = [c for c in CATEGORICAL_COLS if c in X.columns]
    num_cols = [c for c in X.columns if c not in cat_cols]

    return ColumnTransformer(
        transformers=[
            (
                "numeric",
                SimpleImputer(strategy="median"),
                num_cols,
            ),
            (
                "categorical",
                Pipeline(
                    steps=[
                        ("to_object", FunctionTransformer(_to_object_str,
                                                          feature_names_out="one-to-one")),
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        (
                            "ordinal",
                            OrdinalEncoder(
                                handle_unknown="use_encoded_value",
                                unknown_value=-1,
                            ),
                        ),
                    ]
                ),
                cat_cols,
            ),
        ],
        remainder="drop",
        sparse_threshold=0.0,
    )


def _feature_importances_df(pipeline: Pipeline) -> pd.DataFrame:
    """ממפה importances חזרה לשמות העמודות אחרי ה-ColumnTransformer."""
    pre = pipeline.named_steps["preprocess"]
    booster = pipeline.named_steps["model"]
    names = pre.get_feature_names_out()
    return (
        pd.DataFrame({"column": names, "importance": booster.feature_importances_})
        .sort_values("importance", ascending=False)
        .reset_index(drop=True)
    )


def train(
    X_train: pd.DataFrame,
    y_train: np.ndarray,
    X_val: pd.DataFrame,
    y_val: np.ndarray,
) -> Any:
    """אימון של כל ה-candidates; מחזיר את הזוכה לפי val MAPE (real scale)."""
    y_train_log = np.log1p(y_train)
    y_val_log = np.log1p(y_val)

    # preprocessor משותף — נתפר פעם אחת, ואז transform על val כדי לתת ל-XGB
    # eval_set מטריצה מעובדת. כל candidate מקבל את אותו pre (immutable אחרי fit).
    pre = _make_preprocessor(X_train)
    pre.fit(X_train)
    X_train_t = pre.transform(X_train)
    X_val_t = pre.transform(X_val)

    best_model: Pipeline | None = None
    best_result: dict[str, Any] | None = None
    results: list[dict[str, Any]] = []

    for name, params in CANDIDATES:
        print(f"  [xgboost_v1] training {name}...")
        booster = XGBRegressor(**COMMON, **params)
        booster.fit(
            X_train_t,
            y_train_log,
            eval_set=[(X_val_t, y_val_log)],
            verbose=False,
        )

        val_pred_log = booster.predict(X_val_t)
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
            f"  [xgboost_v1] {name} val_mape={val_mape:.4f}  best_iter={best_iter}"
        )

        if best_result is None or val_mape < best_result["val_mape"]:
            # post-hoc: עוטפים את ה-pre המאומן + ה-booster המאומן ב-Pipeline
            # יחיד. ה-Pipeline לא ייזרק שוב fit — joblib.dump שומר אותו כמו שהוא.
            best_model = Pipeline(
                steps=[
                    ("preprocess", pre),
                    ("model", booster),
                ]
            )
            best_result = result

    if best_model is None or best_result is None:
        raise RuntimeError("No XGBoost candidates were trained.")

    importances_df = _feature_importances_df(best_model)

    best_model.candidate_results_ = results
    best_model.best_candidate_ = best_result
    best_model.feature_importances_df_ = importances_df

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    (ARTIFACTS_DIR / "candidate_results.json").write_text(
        json.dumps(results, indent=2)
    )
    importances_df.to_csv(ARTIFACTS_DIR / "feature_importances.csv", index=False)

    print(
        "  [xgboost_v1] best="
        f"{best_result['name']} val_mape={best_result['val_mape']:.4f}  "
        f"best_iter={best_result['best_iteration']}"
    )
    return best_model


def predict(model: Any, X: pd.DataFrame) -> np.ndarray:
    """החזרה ל-real_price (clamp ≥ 1.0 כמו ב-RF v2)."""
    return np.maximum(np.expm1(model.predict(X)), 1.0)
