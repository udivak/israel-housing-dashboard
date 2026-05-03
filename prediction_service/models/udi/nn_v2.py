"""udi/nn_v2 — embeddings + engineered + GeoKNN MLP.

Plan 2 of the NN ladder. Builds on the v1 numeric-only baseline by:
    1. Embedding the four categorical columns
       (``city`` / ``neighborhood`` / ``deal_nature`` / ``geo_cluster``)
       with per-column ``nn.Embedding(card+1, dim)`` where
       ``dim = min(50, (card+1)//2)`` and slot 0 is reserved for unseen /
       NaN values via the preprocessor's slot-0 encoding.
    2. Re-using the engineered scalars + ``geo_cluster`` from
       ``udi/xgboost_v3`` (``area_per_room``, ``log_area_sqm``,
       ``floor_ratio``, ``age_x_area``).
    3. The same GeoKNN OOF features that lifted ``xgboost_v3`` from
       ``xgboost_v2``'s 0.2023 → 0.1985.

Reference baselines:
    * ``udi/nn_v1``       MAPE 0.2772
    * ``udi/xgboost_v3``  MAPE 0.1985
    * ``moses/stacked_v1`` MAPE 0.1869

Realistic ``nn_v2`` MAPE: 0.21-0.24 — embeddings + GeoKNN should beat
the numeric-only v1 by a wide margin once geography enters via embeddings
+ KNN price features.

Run with::

    python3 run.py udi/nn_v2 --data v2
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from torch import nn

from models.udi._nn_common import (
    KnnFeatureBuilder,
    PyTorchTrainer,
    TabularPreprocessor,
    _safe_device_with_fallback,
    build_engineered_features,
    drop_dead_cols,
    fit_kmeans,
    load_bundle,
    oof_train_knn,
    register_model,
    save_bundle,
    set_global_seeds,
)

# Categoricals from the loader that need train→val→test alignment *before*
# build_engineered_features adds ``geo_cluster``. ``geo_cluster`` itself
# is aligned implicitly (it's deterministically produced from a fixed
# codebook ``[-1..63]`` by build_engineered_features).
LOADER_CAT_COLS: tuple[str, ...] = ("city", "neighborhood", "deal_nature")

ARTIFACT_DIR = (
    Path(__file__).resolve().parents[2] / "artifacts" / "udi" / "nn_v2"
)

HIDDEN_DIMS: tuple[int, ...] = (512, 256, 128)
DROPOUT = 0.4
N_EPOCHS = 100
BATCH_SIZE = 1024
LR = 1e-3
WEIGHT_DECAY = 1e-4
PATIENCE = 15
SEED = 42

PREDICT_CHUNK = 8192


# ---------------------------------------------------------------------------
# EmbedMLP
# ---------------------------------------------------------------------------
@register_model
class EmbedMLP(nn.Module):
    """4-layer MLP with per-categorical embeddings concatenated to the numeric features.

    Per-column embedding dim follows the standard fastai-style heuristic
    ``dim = min(50, (card+1)//2)`` where ``card`` is the **train-vocab
    size only** (slot 0 in the input ints is the unknown/NaN slot — see
    ``TabularPreprocessor`` cat path), so ``num_embeddings = card + 1``.
    """

    def __init__(
        self,
        num_in_dim: int,
        cat_cardinalities: list[int],
        hidden_dims: tuple[int, ...] = HIDDEN_DIMS,
        dropout: float = DROPOUT,
    ) -> None:
        super().__init__()
        self.num_in_dim = int(num_in_dim)
        self.cat_cardinalities = [int(c) for c in cat_cardinalities]
        self.hidden_dims = tuple(int(h) for h in hidden_dims)
        self.dropout = float(dropout)

        embed_dims = [min(50, (card + 1) // 2) for card in self.cat_cardinalities]
        self.embed_dims = embed_dims
        self.embeddings = nn.ModuleList(
            [
                nn.Embedding(card + 1, dim)
                for card, dim in zip(self.cat_cardinalities, embed_dims)
            ]
        )

        in_dim = self.num_in_dim + sum(embed_dims)
        layers: list[nn.Module] = []
        prev = in_dim
        for h in self.hidden_dims:
            layers.append(nn.Linear(prev, h))
            layers.append(nn.BatchNorm1d(h))
            layers.append(nn.ReLU(inplace=True))
            layers.append(nn.Dropout(self.dropout))
            prev = h
        layers.append(nn.Linear(prev, 1))
        self.net = nn.Sequential(*layers)

    def forward(
        self, x_num: torch.Tensor, x_cat: torch.Tensor
    ) -> torch.Tensor:
        embedded = [
            self.embeddings[i](x_cat[:, i]) for i in range(len(self.embeddings))
        ]
        x = torch.cat([x_num] + embedded, dim=-1)
        return self.net(x)


# ---------------------------------------------------------------------------
# Categorical alignment helper (mirror of xgboost_v3._align_categories,
# scoped to train/val only — predict re-aligns from the bundle's snapshot).
# ---------------------------------------------------------------------------
def _align_train_val_categories(
    X_train: pd.DataFrame, X_val: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    X_train = X_train.copy()
    X_val = X_val.copy()
    for c in LOADER_CAT_COLS:
        if c not in X_train.columns:
            continue
        cats = X_train[c].astype("category").cat.categories
        X_train[c] = pd.Categorical(X_train[c], categories=cats)
        if c in X_val.columns:
            X_val[c] = pd.Categorical(X_val[c], categories=cats)
    return X_train, X_val


# ---------------------------------------------------------------------------
# Train
# ---------------------------------------------------------------------------
def train(
    X_train: pd.DataFrame,
    y_train: np.ndarray,
    X_val: pd.DataFrame,
    y_val: np.ndarray,
) -> dict[str, Any]:
    """Train ``EmbedMLP`` over the v3 feature pipeline + return a joblib-able bundle."""
    gen = set_global_seeds(SEED)

    y_train_arr = np.asarray(y_train, dtype=float)
    y_val_arr = np.asarray(y_val, dtype=float)
    y_train_log = np.log1p(y_train_arr)
    y_val_log = np.log1p(y_val_arr)

    # 1. Align loader categoricals on train→val (geo_cluster is added in
    #    step 3 by build_engineered_features and uses a fixed codebook).
    X_train_a, X_val_a = _align_train_val_categories(X_train, X_val)

    # 2. KMeans on train coords only — geo_cluster is required by the
    #    preprocessor's cat path. Hard fail-fast if coverage degrades to
    #    the point KMeans can't fit (would silently break the cardinality
    #    list and the embedding layer dimensions).
    kmeans = fit_kmeans(X_train_a)
    if kmeans is None:
        raise RuntimeError(
            "nn_v2 requires geo_cluster — fit_kmeans returned None "
            "(insufficient lat/lon coverage)"
        )

    # 3. Engineered features on both slices.
    X_train_eng = build_engineered_features(X_train_a, kmeans)
    X_val_eng = build_engineered_features(X_val_a, kmeans)

    # 4. GeoKNN: 5-fold OOF for train, BallTree on full-train for val.
    print("  [nn_v2] computing OOF GeoKNN features for train...")
    train_knn = oof_train_knn(X_train_eng, y_train_arr)
    print("  [nn_v2] fitting KNN BallTree on full train + transforming val...")
    knn_builder = KnnFeatureBuilder()
    knn_builder.fit(X_train_eng, y_train_arr)
    val_knn = knn_builder.transform(X_val_eng)

    nan_train = float(train_knn.isna().mean().mean())
    nan_val = float(val_knn.isna().mean().mean())
    print(
        f"  [nn_v2] KNN-feature NaN rate: train={nan_train:.1%}  val={nan_val:.1%}"
    )

    X_train_full_pre = pd.concat([X_train_eng, train_knn], axis=1)
    X_val_full_pre = pd.concat([X_val_eng, val_knn], axis=1)

    # 5. Drop dead cols on train; mirror exactly on val.
    X_train_full, dropped = drop_dead_cols(X_train_full_pre)
    X_val_full = X_val_full_pre.drop(columns=dropped, errors="ignore")
    if dropped:
        print(f"  [nn_v2] dropped dead columns: {dropped}")

    # 6. Preprocessor with cat path: snapshots cat_categories +
    #    cat_cardinalities for each of the 4 cat cols and the slot-0
    #    unknown encoding kicks in on transform.
    pre = TabularPreprocessor(include_categorical=True)
    pre.fit(X_train_full)
    X_num_train, X_cat_train, cards = pre.transform(X_train_full)
    X_num_val, X_cat_val, _ = pre.transform(X_val_full)

    if X_cat_train is None or X_cat_val is None:
        raise RuntimeError(
            "TabularPreprocessor returned X_cat=None despite "
            "include_categorical=True — preprocessor refused to find any "
            "of the 4 cat cols on the train frame; check loader output."
        )

    print(
        f"  [nn_v2] num_in_dim={X_num_train.shape[1]} "
        f"(numeric={len(pre._numeric_cols)} + nan_indicators={len(pre._nan_indicator_cols)})  "
        f"cat_cardinalities={cards}"
    )

    # 7. Build model + probe device. EmbedMLP contains BatchNorm1d so the
    #    helper short-circuits MPS→CPU before any forward pass; the
    #    sample_batch is the numeric tensor only (helper signature is a
    #    single Tensor, not a tuple — see ``_nn_common`` docstring).
    model = EmbedMLP(
        num_in_dim=X_num_train.shape[1],
        cat_cardinalities=list(cards),
        hidden_dims=HIDDEN_DIMS,
        dropout=DROPOUT,
    )
    probe_n = min(BATCH_SIZE, X_num_train.shape[0])
    sample_batch = torch.from_numpy(X_num_train[:probe_n].astype(np.float32))
    device = _safe_device_with_fallback(model, sample_batch, n_probe_steps=20)
    print(f"  [nn_v2] training on device: {device}")

    # 8. Trainer fits the cat path because X_cat_train is not None.
    trainer = PyTorchTrainer(
        device=device,
        generator=gen,
        n_epochs=N_EPOCHS,
        batch_size=BATCH_SIZE,
        lr=LR,
        weight_decay=WEIGHT_DECAY,
        patience=PATIENCE,
        artifact_dir=ARTIFACT_DIR,
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

    final_val = history[-1]["val_mape"] if history else float("nan")
    best_val = (
        min(h["val_mape"] for h in history) if history else float("nan")
    )
    print(
        f"  [nn_v2] training done: epochs_run={len(history)} "
        f"final_val_mape={final_val:.4f} best_val_mape={best_val:.4f}"
    )

    # 9. Build the bundle. dropped_cols = ONLY dead cols (the 3 raw cats
    #    are NOT dropped — they're embedded; geo_cluster is added by
    #    build_engineered_features in predict()). model_class_name is
    #    auto-derived inside save_bundle from type(trained).__name__.
    model_kwargs = {
        "num_in_dim": int(X_num_train.shape[1]),
        "cat_cardinalities": list(cards),
        "hidden_dims": HIDDEN_DIMS,
        "dropout": DROPOUT,
    }
    bundle = save_bundle(
        model=trained,
        model_kwargs=model_kwargs,
        preprocessor=pre,
        dropped_cols=list(dropped),
        kmeans=kmeans,
        knn_builder=knn_builder,
        y_log_mean=y_log_mean,
        y_log_std=y_log_std,
        feature_columns=pre.feature_columns,
        cat_cardinalities=list(cards),
        candidate_results=[],
        best_candidate={},
        history=history,
    )
    return bundle


# ---------------------------------------------------------------------------
# Predict
# ---------------------------------------------------------------------------
def predict(bundle: dict[str, Any], X: pd.DataFrame) -> np.ndarray:
    """Score ``X`` with a trained nn_v2 bundle. CPU-only inference."""
    pre: TabularPreprocessor = bundle["preprocessor"]

    # 1. Re-align loader categoricals to the train snapshot. geo_cluster
    #    is regenerated below via build_engineered_features and uses the
    #    same fixed codebook on every call — no separate alignment needed.
    X = X.copy()
    for col in LOADER_CAT_COLS:
        if col in X.columns and col in pre.cat_categories:
            X[col] = pd.Categorical(
                X[col].to_numpy(), categories=pre.cat_categories[col]
            )

    # 2. Engineered features (including geo_cluster).
    X_eng = build_engineered_features(X, bundle["kmeans"])

    # 3. KNN features from the full-train BallTree.
    X_full_pre = pd.concat([X_eng, bundle["knn_builder"].transform(X_eng)], axis=1)

    # 4. Drop the same dead cols dropped on train.
    X_full = X_full_pre.drop(
        columns=[c for c in bundle["dropped_cols"] if c in X_full_pre.columns],
        errors="ignore",
    )

    # 5. Preprocessor splits into (X_num, X_cat, _) using the same
    #    slot-0-unknown encoding as train.
    X_num, X_cat, _ = pre.transform(X_full)

    if X_cat is None:
        raise RuntimeError(
            "Preprocessor returned X_cat=None during predict — bundle was "
            "saved without the categorical path; was this bundle actually "
            "produced by nn_v2.train?"
        )

    # 6. Reconstruct the model on CPU and forward in chunks.
    model = load_bundle(bundle, device=torch.device("cpu"))

    x_num_t = torch.from_numpy(np.asarray(X_num, dtype=np.float32))
    x_cat_t = torch.from_numpy(np.asarray(X_cat, dtype=np.int64))

    preds_std: list[np.ndarray] = []
    with torch.no_grad():
        for start in range(0, x_num_t.size(0), PREDICT_CHUNK):
            num_chunk = x_num_t[start : start + PREDICT_CHUNK]
            cat_chunk = x_cat_t[start : start + PREDICT_CHUNK]
            out = model(num_chunk, cat_chunk).squeeze(-1)
            preds_std.append(out.detach().cpu().numpy())

    pred_std_arr = (
        np.concatenate(preds_std, axis=0)
        if preds_std
        else np.empty((0,), dtype=np.float32)
    )
    pred_log = pred_std_arr * bundle["y_log_std"] + bundle["y_log_mean"]
    pred = np.clip(np.expm1(pred_log), a_min=1.0, a_max=None)
    return pred.astype(float)
