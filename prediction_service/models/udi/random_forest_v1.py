"""Random Forest experiment suite for Udi.

Run with:
    python run.py udi/random_forest_v1
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer  # pyright: ignore[reportMissingImports]
from sklearn.ensemble import RandomForestRegressor  # pyright: ignore[reportMissingImports]
from sklearn.impute import SimpleImputer  # pyright: ignore[reportMissingImports]
from sklearn.pipeline import Pipeline  # pyright: ignore[reportMissingImports]
from sklearn.preprocessing import OneHotEncoder  # pyright: ignore[reportMissingImports]

RANDOM_STATE = 42

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
        "rf_wide",
        {
            "n_estimators": 240,
            "max_depth": None,
            "min_samples_leaf": 1,
            "max_features": 1.0,
        },
    ),
)


def _mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    mask = y_true > 0
    return float(np.mean(np.abs(y_pred[mask] - y_true[mask]) / y_true[mask]))


def _make_preprocessor(X: pd.DataFrame) -> ColumnTransformer:
    categorical_cols = list(X.select_dtypes(include=["category", "object"]).columns)
    numeric_cols = [col for col in X.columns if col not in categorical_cols]

    return ColumnTransformer(
        transformers=[
            (
                "numeric",
                SimpleImputer(strategy="median"),
                numeric_cols,
            ),
            (
                "categorical",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        (
                            "onehot",
                            OneHotEncoder(handle_unknown="ignore", sparse_output=True),
                        ),
                    ]
                ),
                categorical_cols,
            ),
        ],
        sparse_threshold=0.3,
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
                ),
            ),
        ]
    )


def train(
    X_train: pd.DataFrame,
    y_train: np.ndarray,
    X_val: pd.DataFrame,
    y_val: np.ndarray,
) -> Any:
    """Train candidate Random Forests and return the best validation-MAPE pipeline."""
    y_train_log = np.log1p(y_train)

    best_model: Pipeline | None = None
    best_result: dict[str, Any] | None = None
    results: list[dict[str, Any]] = []

    for name, params in CANDIDATES:
        print(f"  [random_forest_v1] training {name}...")
        model = _make_pipeline(X_train, params)
        model.fit(X_train, y_train_log)

        val_pred = np.expm1(model.predict(X_val))
        val_pred = np.maximum(val_pred, 1.0)
        val_mape = _mape(y_val, val_pred)

        result = {"name": name, "params": params, "val_mape": val_mape}
        results.append(result)
        print(f"  [random_forest_v1] {name} val_mape={val_mape:.4f}")

        if best_result is None or val_mape < best_result["val_mape"]:
            best_model = model
            best_result = result

    if best_model is None or best_result is None:
        raise RuntimeError("No Random Forest candidates were trained.")

    best_model.candidate_results_ = results
    best_model.best_candidate_ = best_result
    print(
        "  [random_forest_v1] best="
        f"{best_result['name']} val_mape={best_result['val_mape']:.4f}"
    )
    return best_model


def predict(model: Any, X: pd.DataFrame) -> np.ndarray:
    """Return predicted real_price values for X."""
    return np.maximum(np.expm1(model.predict(X)), 1.0)
