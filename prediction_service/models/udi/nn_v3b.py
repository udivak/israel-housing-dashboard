"""udi/nn_v3b — 5-candidate sweep over (dropout, weight_decay, d) on the nn_v3 ResNet.

Plan 3 follow-up addressing ``udi/nn_v3``'s overfit signal (Run 9 val→test
gap +0.0124 — wider than v2's +0.0066; train loss kept dropping past
best-val @ epoch 77). Sweeps 5 candidates around the v3 baseline
``(d=256, n_blocks=4, dropout=0.1, weight_decay=1e-5)`` along the two
regularisation levers (dropout, weight_decay) plus the capacity axis (d):

    baseline      d=256, dropout=0.1, weight_decay=1e-5  (== nn_v3, sanity check)
    dropout_high  d=256, dropout=0.2, weight_decay=1e-5
    wd_high       d=256, dropout=0.1, weight_decay=1e-4   (matches v1/v2 wd)
    d_small       d=192, dropout=0.1, weight_decay=1e-5
    d_large       d=384, dropout=0.1, weight_decay=1e-5

Constants held across all candidates: ``n_blocks=4, n_epochs=200,
batch_size=1024, lr=1e-3, warmup_epochs=5, patience=20, seed=42``.

The expensive feature pipeline (KMeans + GeoKNN OOF + preprocessor fit
+ train→val cat alignment) is deterministic given ``(X_train, y_train,
X_val)`` so it's computed **once** before the candidate loop. Total
wall-clock: ~1 min preprocessing + 5 × ~2 min training ≈ 11 min.

Cold-load contract: importing this module triggers
``from models.udi.nn_v3 import ...`` which in turn populates
``_nn_common.MODEL_REGISTRY['ResNetTabular']`` (because importing
``nn_v3`` runs the ``@register_model`` decorator). ``predict`` is
re-exported from ``nn_v3`` — bundle schema is identical.

Run with::

    python3 run.py udi/nn_v3b --data v2
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch

from models.udi._nn_common import (
    KnnFeatureBuilder,
    PyTorchTrainer,
    TabularPreprocessor,
    _safe_device_with_fallback,
    build_engineered_features,
    drop_dead_cols,
    fit_kmeans,
    oof_train_knn,
    save_bundle,
    set_global_seeds,
)
from models.udi.nn_v3 import (
    LOADER_CAT_COLS,
    ResNetTabular,
    _align_train_val_categories,
    predict,  # noqa: F401  re-exported as nn_v3b.predict (bundle schema is identical)
)

ARTIFACT_DIR = (
    Path(__file__).resolve().parents[2] / "artifacts" / "udi" / "nn_v3b"
)

N_BLOCKS = 4
N_EPOCHS = 200
BATCH_SIZE = 1024
LR = 1e-3
WARMUP_EPOCHS = 5
PATIENCE = 20
SEED = 42

CANDIDATES: tuple[tuple[str, dict[str, Any]], ...] = (
    ("baseline",     {"d": 256, "dropout": 0.1, "weight_decay": 1e-5}),
    ("dropout_high", {"d": 256, "dropout": 0.2, "weight_decay": 1e-5}),
    ("wd_high",      {"d": 256, "dropout": 0.1, "weight_decay": 1e-4}),
    ("d_small",      {"d": 192, "dropout": 0.1, "weight_decay": 1e-5}),
    ("d_large",      {"d": 384, "dropout": 0.1, "weight_decay": 1e-5}),
)


def train(
    X_train: pd.DataFrame,
    y_train: np.ndarray,
    X_val: pd.DataFrame,
    y_val: np.ndarray,
) -> dict[str, Any]:
    """Run the v3 preprocessing once, then train each candidate; return bundle for the val winner."""
    y_train_arr = np.asarray(y_train, dtype=float)
    y_val_arr = np.asarray(y_val, dtype=float)
    y_train_log = np.log1p(y_train_arr)
    y_val_log = np.log1p(y_val_arr)

    # 1. Align loader categoricals on train→val.
    X_train_a, X_val_a = _align_train_val_categories(X_train, X_val)

    # 2. KMeans on train coords only.
    kmeans = fit_kmeans(X_train_a)
    if kmeans is None:
        raise RuntimeError(
            "nn_v3b requires geo_cluster — fit_kmeans returned None "
            "(insufficient lat/lon coverage)"
        )

    # 3. Engineered features on both slices.
    X_train_eng = build_engineered_features(X_train_a, kmeans)
    X_val_eng = build_engineered_features(X_val_a, kmeans)

    # 4. GeoKNN: 5-fold OOF for train, BallTree on full-train for val.
    print("  [nn_v3b] computing OOF GeoKNN features for train...")
    train_knn = oof_train_knn(X_train_eng, y_train_arr)
    print("  [nn_v3b] fitting KNN BallTree on full train + transforming val...")
    knn_builder = KnnFeatureBuilder()
    knn_builder.fit(X_train_eng, y_train_arr)
    val_knn = knn_builder.transform(X_val_eng)

    nan_train = float(train_knn.isna().mean().mean())
    nan_val = float(val_knn.isna().mean().mean())
    print(
        f"  [nn_v3b] KNN-feature NaN rate: train={nan_train:.1%}  "
        f"val={nan_val:.1%}"
    )

    X_train_full_pre = pd.concat([X_train_eng, train_knn], axis=1)
    X_val_full_pre = pd.concat([X_val_eng, val_knn], axis=1)

    # 5. Drop dead cols on train; mirror exactly on val.
    X_train_full, dropped = drop_dead_cols(X_train_full_pre)
    X_val_full = X_val_full_pre.drop(columns=dropped, errors="ignore")
    if dropped:
        print(f"  [nn_v3b] dropped dead columns: {dropped}")

    # 6. Preprocessor (cat path).
    pre = TabularPreprocessor(include_categorical=True)
    pre.fit(X_train_full)
    X_num_train, X_cat_train, cards = pre.transform(X_train_full)
    X_num_val, X_cat_val, _ = pre.transform(X_val_full)

    if X_cat_train is None or X_cat_val is None:
        raise RuntimeError(
            "TabularPreprocessor returned X_cat=None despite "
            "include_categorical=True"
        )

    print(
        f"  [nn_v3b] num_in_dim={X_num_train.shape[1]} "
        f"(numeric={len(pre._numeric_cols)} + nan_indicators={len(pre._nan_indicator_cols)})  "
        f"cat_cardinalities={cards}"
    )

    # 7. Probe sample (every candidate has BN1d → MPS short-circuits to CPU).
    probe_n = min(BATCH_SIZE, X_num_train.shape[0])
    sample_batch = torch.from_numpy(X_num_train[:probe_n].astype(np.float32))

    candidate_results: list[dict[str, Any]] = []
    best: dict[str, Any] | None = None
    for name, params in CANDIDATES:
        print(
            f"  [nn_v3b] training candidate '{name}': d={params['d']}  "
            f"dropout={params['dropout']}  weight_decay={params['weight_decay']}"
        )
        gen = set_global_seeds(SEED)
        model = ResNetTabular(
            num_in_dim=X_num_train.shape[1],
            cat_cardinalities=list(cards),
            d=params["d"],
            n_blocks=N_BLOCKS,
            dropout=params["dropout"],
        )
        device = _safe_device_with_fallback(model, sample_batch, n_probe_steps=20)
        trainer = PyTorchTrainer(
            device=device,
            generator=gen,
            n_epochs=N_EPOCHS,
            batch_size=BATCH_SIZE,
            lr=LR,
            weight_decay=params["weight_decay"],
            patience=PATIENCE,
            warmup_epochs=WARMUP_EPOCHS,
            artifact_dir=ARTIFACT_DIR / "candidates" / name,
        )
        trained, history, y_log_mean, y_log_std = trainer.fit(
            model,
            X_num_train,
            X_cat_train,
            y_train_log,
            X_num_val,
            X_cat_val,
            y_val_log,
        )

        best_h = min(history, key=lambda h: h["val_mape"])
        result = {
            "name": name,
            "params": dict(params),
            "val_mape": float(best_h["val_mape"]),
            "epoch_at_best": int(best_h["epoch"]),
            "epochs_run": len(history),
        }
        candidate_results.append(result)
        print(
            f"  [nn_v3b] {name}: val_mape={result['val_mape']:.4f}  "
            f"epoch_at_best={result['epoch_at_best']}  "
            f"epochs_run={result['epochs_run']}"
        )

        if best is None or result["val_mape"] < best["val_mape"]:
            best = {
                **result,
                "trained": trained,
                "history": history,
                "y_log_mean": y_log_mean,
                "y_log_std": y_log_std,
            }

    if best is None:
        raise RuntimeError("nn_v3b candidate loop produced no winner")

    print(
        f"  [nn_v3b] winner='{best['name']}'  val_mape={best['val_mape']:.4f}  "
        f"epoch_at_best={best['epoch_at_best']}"
    )

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    (ARTIFACT_DIR / "candidate_results.json").write_text(
        json.dumps(candidate_results, indent=2)
    )
    (ARTIFACT_DIR / "training_history.json").write_text(
        json.dumps(best["history"], indent=2)
    )

    model_kwargs = {
        "num_in_dim": int(X_num_train.shape[1]),
        "cat_cardinalities": list(cards),
        "d": int(best["params"]["d"]),
        "n_blocks": N_BLOCKS,
        "dropout": float(best["params"]["dropout"]),
    }
    best_candidate_meta = {
        "name": best["name"],
        **best["params"],
        "val_mape": float(best["val_mape"]),
        "epoch_at_best": int(best["epoch_at_best"]),
        "epochs_run": int(best["epochs_run"]),
    }
    bundle = save_bundle(
        model=best["trained"],
        model_kwargs=model_kwargs,
        preprocessor=pre,
        dropped_cols=list(dropped),
        kmeans=kmeans,
        knn_builder=knn_builder,
        y_log_mean=best["y_log_mean"],
        y_log_std=best["y_log_std"],
        feature_columns=pre.feature_columns,
        cat_cardinalities=list(cards),
        candidate_results=candidate_results,
        best_candidate=best_candidate_meta,
        history=best["history"],
    )
    return bundle
