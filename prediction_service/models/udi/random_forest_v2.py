"""Random Forest v2 — לרוץ על loader v2 (3 מקורות: temporal+normalized+osm).

שיפורים מול v1:
    1. OrdinalEncoder במקום OneHotEncoder לקטגוריות (city/neighborhood בעלי
       cardinality גבוה → OHE מנפח אלפי עמודות; trees לא צריכים OHE).
    2. הוסר rf_wide (max_features=1.0 הוא bagging, לא RF).
    3. הוספו rf_mid_features ו-rf_logn — סריקה ממוקדת יותר על max_features.
    4. oob_score=True על כל candidate — אינדיקציה פנימית בחינם.
    5. נשמרים candidate_results.json ו-feature_importances.csv ב-artifacts/.

כדי להפעיל:
    python run.py udi/random_forest_v2 --data v2
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer  # pyright: ignore[reportMissingImports]
from sklearn.ensemble import RandomForestRegressor  # pyright: ignore[reportMissingImports]
from sklearn.impute import SimpleImputer  # pyright: ignore[reportMissingImports]
from sklearn.pipeline import Pipeline  # pyright: ignore[reportMissingImports]
from sklearn.preprocessing import (  # pyright: ignore[reportMissingImports]
    FunctionTransformer,
    OrdinalEncoder,
)

RANDOM_STATE = 42

ARTIFACTS_DIR = (
    Path(__file__).resolve().parents[2] / "artifacts" / "udi" / "random_forest_v2"
)

CATEGORICAL_COLS = ("city", "neighborhood", "deal_nature")

CANDIDATES: tuple[tuple[str, dict[str, Any]], ...] = (
    (
        "rf_fast",
        {
            "n_estimators": 120,
            "max_depth": 18,
            "min_samples_leaf": 2,
            "max_features": "sqrt",
        },
    ),
    (
        "rf_balanced",
        {
            "n_estimators": 240,
            "max_depth": 28,
            "min_samples_leaf": 3,
            "max_features": "sqrt",
        },
    ),
    (
        "rf_deep",
        {
            "n_estimators": 320,
            "max_depth": None,
            "min_samples_leaf": 2,
            "max_features": 0.7,
        },
    ),
    (
        "rf_mid_features",
        {
            "n_estimators": 400,
            "max_depth": None,
            "min_samples_leaf": 2,
            "max_features": 0.5,
        },
    ),
    (
        "rf_logn",
        {
            "n_estimators": 600,
            "max_depth": None,
            "min_samples_leaf": 2,
            "max_features": "log2",
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
        sparse_threshold=0.0,  # הכל dense — קטגוריות אחרי OrdinalEncoder הן עמודות עם ערך אחד.
    )


def _make_pipeline(X: pd.DataFrame, params: dict[str, Any]) -> Pipeline:
    return Pipeline(
        steps=[
            ("preprocess", _make_preprocessor(X)),
            (
                "model",
                RandomForestRegressor(
                    **params,
                    random_state=RANDOM_STATE,
                    n_jobs=-1,
                    oob_score=True,
                ),
            ),
        ]
    )


def _feature_importances_df(pipeline: Pipeline) -> pd.DataFrame:
    """ממפה importances של ה-RF חזרה לשמות העמודות אחרי ה-ColumnTransformer."""
    pre = pipeline.named_steps["preprocess"]
    rf = pipeline.named_steps["model"]
    names = pre.get_feature_names_out()
    return (
        pd.DataFrame({"column": names, "importance": rf.feature_importances_})
        .sort_values("importance", ascending=False)
        .reset_index(drop=True)
    )


def train(
    X_train: pd.DataFrame,
    y_train: np.ndarray,
    X_val: pd.DataFrame,
    y_val: np.ndarray,
) -> Any:
    """אימון של כל ה-candidates; מחזיר את הזוכה לפי val MAPE."""
    y_train_log = np.log1p(y_train)

    best_model: Pipeline | None = None
    best_result: dict[str, Any] | None = None
    results: list[dict[str, Any]] = []

    for name, params in CANDIDATES:
        print(f"  [random_forest_v2] training {name}...")
        model = _make_pipeline(X_train, params)
        model.fit(X_train, y_train_log)

        val_pred = np.expm1(model.predict(X_val))
        val_pred = np.maximum(val_pred, 1.0)
        val_mape = _mape(y_val, val_pred)
        oob_r2 = float(getattr(model.named_steps["model"], "oob_score_", float("nan")))

        result = {
            "name": name,
            "params": params,
            "val_mape": val_mape,
            "oob_r2": oob_r2,  # על log1p(y) — להשוואה בין candidates בלבד.
        }
        results.append(result)
        print(
            f"  [random_forest_v2] {name} val_mape={val_mape:.4f}  oob_r2={oob_r2:.4f}"
        )

        if best_result is None or val_mape < best_result["val_mape"]:
            best_model = model
            best_result = result

    if best_model is None or best_result is None:
        raise RuntimeError("No Random Forest candidates were trained.")

    importances_df = _feature_importances_df(best_model)

    best_model.candidate_results_ = results
    best_model.best_candidate_ = best_result
    best_model.feature_importances_df_ = importances_df

    # Side files — run.py לא יודע עליהם, אבל הוא בדיוק כותב לאותו תיקייה
    # (ARTIFACTS / person / model_name) אז זה לא מתנגש איתו.
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    (ARTIFACTS_DIR / "candidate_results.json").write_text(
        json.dumps(results, indent=2)
    )
    importances_df.to_csv(ARTIFACTS_DIR / "feature_importances.csv", index=False)

    print(
        "  [random_forest_v2] best="
        f"{best_result['name']} val_mape={best_result['val_mape']:.4f}  "
        f"oob_r2={best_result['oob_r2']:.4f}"
    )
    return best_model


def predict(model: Any, X: pd.DataFrame) -> np.ndarray:
    """החזרה ל-real_price (clamp ≥ 1.0 כמו ב-v1)."""
    return np.maximum(np.expm1(model.predict(X)), 1.0)
