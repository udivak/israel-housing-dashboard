"""Build the input frame each model's ``predict()`` expects.

``serve.py`` dispatches to ``models.<owner>.<name>.predict(artifact, X)``. Every
model was trained on its loader's engineered base frame (``data.py`` ≈89 cols for
``moses/*``; ``data_v2.py`` =77 cols for ``udi/*``), and some models append KNN /
engineer extra features *inside* ``predict()``. The dashboard only sends ~10 raw
fields, so we widen the frame to the columns each model needs (missing → NaN) and
restore categorical dtypes, then hand it to the model's own ``predict()``.

Two cases:
  * Class A — the estimator consumes ``X`` directly: feed its *declared* feature
    list (``feature_name_`` / ``feature_names_in_`` / ``feature_names_`` / bundle
    ``feature_columns``).
  * Class B — ``predict()`` engineers/appends features from a stored builder: feed
    the data-version *base* frame and let ``predict()`` append the rest itself.

ponytail: most features are NaN here, so predictions are low-fidelity — this only
makes every model *run* instead of erroring. Real feature enrichment is a separate,
out-of-scope effort.
"""
from __future__ import annotations

from typing import Any

import pandas as pd


def has_internal_builder(artifact: Any) -> bool:
    """Class B: ``predict()`` derives features from a stored builder/sub-model."""
    if isinstance(artifact, dict):
        if artifact.get("knn_builder") is not None:  # nn_v2/3/4, xgboost_v3/4/5
            return True
        if artifact.get("builder") is not None:  # lightgbm_knn, stacked_v2
            return True
        if "nn_bundle" in artifact:  # blend_v1 fans out to sub-models that do
            return True
    return False


def _declared_columns(artifact: Any) -> list[str] | None:
    """Class A: the exact feature list the artifact's estimator consumes."""
    if isinstance(artifact, dict):
        if "feature_columns" in artifact:  # nn_v1 bundle
            return list(artifact["feature_columns"])
        if artifact.get("lgbm") is not None:  # stacked_v1
            return list(artifact["lgbm"].feature_name_)
        if artifact.get("model") is not None:  # xgboost_v2
            names = artifact["model"].get_booster().feature_names
            return list(names) if names else None
        return None
    for attr in ("feature_name_", "feature_names_in_", "feature_names_"):
        names = getattr(artifact, attr, None)
        if names is not None:
            return list(names)
    return None


def _inner_lgbm(artifact: Any):
    """A LightGBM estimator whose booster ``pandas_categorical`` defines cat cols."""
    if isinstance(artifact, dict):
        return artifact.get("lgbm")
    return artifact if hasattr(artifact, "booster_") else None


def build_serving_frame(
    artifact: Any,
    features: dict[str, Any],
    *,
    base_columns: list[str] | None = None,
) -> pd.DataFrame:
    """One-row frame widened to what ``artifact``'s ``predict()`` expects.

    ``base_columns`` is the data-version base feature list; used only for Class B
    models (those with an internal feature builder).
    """
    cols = base_columns if has_internal_builder(artifact) else _declared_columns(artifact)

    df = pd.DataFrame([features])
    if cols is not None:
        for col in cols:
            if col not in df.columns:
                df[col] = None  # object dtype — load-bearing for the categorical pass below
        df = df[cols]

    # Restore pandas categorical dtypes the LightGBM booster stores; without this,
    # object-dtype categoricals trip "categorical_feature do not match".
    lgbm = _inner_lgbm(artifact)
    if lgbm is not None and hasattr(lgbm, "booster_"):
        cat_iter = iter(lgbm.booster_.dump_model().get("pandas_categorical") or [])
        for col in df.columns:
            if df[col].dtype == object:
                try:
                    df[col] = pd.Categorical(df[col], categories=next(cat_iter))
                except StopIteration:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

    # Coerce remaining object columns (missing numerics filled as None) to float.
    # Models with string categoricals (catboost, xgboost bundles) re-cast internally.
    for col in df.select_dtypes("object").columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df
