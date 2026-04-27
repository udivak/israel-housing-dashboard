"""udi/blend_v1 — weighted-average ensemble of ``udi/xgboost_v3`` + ``udi/nn_v3``.

Plan 3 follow-up. Picks the blend weight ``alpha`` on val over a 21-point
grid (``np.linspace(0, 1, 21)``, step 0.05 — same precedent as
``moses/stacked_v1`` / ``moses/stacked_v2``):

    blend = alpha * nn_v3 + (1 - alpha) * xgboost_v3

Both base models are trained **inline** inside ``train()`` (the bases'
own runs on the leaderboard are not touched — see "Inline-train side
effect" below). Bundle stores both child bundles + the val-optimal
``alpha`` + the full grid-search trace.

Two cold-load contracts are satisfied by the top-of-file
``from models.udi import nn_v3, xgboost_v3`` import:

    1. ``nn_v3`` import → runs the ``@register_model`` decorator on
       ``ResNetTabular``, populating ``_nn_common.MODEL_REGISTRY``. Without
       this, ``load_bundle(bundle["nn_bundle"])`` would raise
       ``KeyError: 'ResNetTabular'`` per the ``_nn_common`` cold-load
       contract.
    2. ``xgboost_v3`` import → resolves the qualified-class path
       ``models.udi.xgboost_v3.KnnFeatureBuilder`` that joblib stored in
       the inner xgb_bundle (a *different class* from
       ``models.udi._nn_common.KnnFeatureBuilder`` in the inner
       nn_bundle).

``xgboost_v3`` has no ``@register_model`` (XGBoost's ``XGBRegressor``
pickles fully); the import is purely for the qualified-path resolution
above.

Inline-train side effect (non-breaking, worth noting): calling
``xgboost_v3.train()`` and ``nn_v3.train()`` from inside ``blend_v1``
overwrites their internal log writes
(``artifacts/udi/xgboost_v3/{candidate_results,feature_importances}.*``
and ``artifacts/udi/nn_v3/training_history.json``). The ``model.joblib``
/ ``metrics.json`` / ``run_metadata.json`` files for ``udi/xgboost_v3``
and ``udi/nn_v3`` and their leaderboard rows are NOT touched (those are
written only by the outer ``run.py`` invocation, keyed on the outer
submission name).

Run with::

    python3 run.py udi/blend_v1 --data v2
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from models.udi import nn_v3, xgboost_v3

ALPHA_GRID = np.linspace(0.0, 1.0, 21)

ARTIFACT_DIR = (
    Path(__file__).resolve().parents[2] / "artifacts" / "udi" / "blend_v1"
)


def _val_mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    mask = y_true > 0
    return float(np.mean(np.abs(y_pred[mask] - y_true[mask]) / y_true[mask]))


def train(
    X_train: pd.DataFrame,
    y_train: np.ndarray,
    X_val: pd.DataFrame,
    y_val: np.ndarray,
) -> dict[str, Any]:
    """Train both bases inline, grid-search ``alpha`` on val, return bundle."""
    print("  [blend_v1] training xgboost_v3 base...")
    xgb_bundle = xgboost_v3.train(X_train, y_train, X_val, y_val)

    print("  [blend_v1] training nn_v3 base...")
    nn_bundle = nn_v3.train(X_train, y_train, X_val, y_val)

    print("  [blend_v1] scoring bases on val for alpha grid search...")
    p_xgb_val = xgboost_v3.predict(xgb_bundle, X_val)
    p_nn_val = nn_v3.predict(nn_bundle, X_val)
    y_val_arr = np.asarray(y_val, dtype=float)

    p_xgb_val_baseline = _val_mape(y_val_arr, p_xgb_val)
    p_nn_val_baseline = _val_mape(y_val_arr, p_nn_val)
    print(
        f"  [blend_v1] base val MAPE: xgb={p_xgb_val_baseline:.4f}  "
        f"nn={p_nn_val_baseline:.4f}"
    )

    candidate_results: list[dict[str, float]] = []
    best: dict[str, float] = {"alpha": float("nan"), "val_mape": float("inf")}
    for alpha in ALPHA_GRID:
        blend = alpha * p_nn_val + (1.0 - alpha) * p_xgb_val
        mape = _val_mape(y_val_arr, blend)
        candidate_results.append({"alpha": float(alpha), "val_mape": mape})
        if mape < best["val_mape"]:
            best = {"alpha": float(alpha), "val_mape": mape}

    print(
        f"  [blend_v1] best alpha={best['alpha']:.2f}  "
        f"val_mape={best['val_mape']:.4f}"
    )
    if best["alpha"] <= 0.0 + 1e-9 or best["alpha"] >= 1.0 - 1e-9:
        print(
            "  [blend_v1] ⚠️ degenerate alpha — ensemble collapses to a single "
            "base. Shipping anyway so the leaderboard row documents the "
            "negative result; see EXPERIMENTS.md Run 10 Notes."
        )

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    (ARTIFACT_DIR / "candidate_results.json").write_text(
        json.dumps(candidate_results, indent=2)
    )

    return {
        "xgb_bundle": xgb_bundle,
        "nn_bundle": nn_bundle,
        "alpha": best["alpha"],
        "candidate_results": candidate_results,
        "best_candidate": best,
        "p_xgb_val_baseline": p_xgb_val_baseline,
        "p_nn_val_baseline": p_nn_val_baseline,
    }


def predict(bundle: dict[str, Any], X: pd.DataFrame) -> np.ndarray:
    """Weighted-average blend: ``alpha * nn_v3 + (1 - alpha) * xgboost_v3``."""
    p_xgb = xgboost_v3.predict(bundle["xgb_bundle"], X)
    p_nn = nn_v3.predict(bundle["nn_bundle"], X)
    alpha = float(bundle["alpha"])
    return alpha * p_nn + (1.0 - alpha) * p_xgb
