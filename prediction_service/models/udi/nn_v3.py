"""udi/nn_v3 — ResNet-tabular (Gorishniy et al. 2021) + LR warmup.

Plan 3 of the NN ladder. Architectural lift over ``udi/nn_v2``:

    1. **ResNet-tabular block stack** per Gorishniy et al. 2021,
       "Revisiting Deep Learning Models for Tabular Data". Replaces
       ``EmbedMLP``'s 4-layer stack with: ``Linear(in→d=256)`` →
       ``4 × ResidualBlock(d=256)`` → ``BN+Linear(d→1)`` head, where each
       ResidualBlock is ``BN → Linear(d,2d) → ReLU → Dropout(0.1) →
       Linear(2d,d) → Dropout(0.1) → +skip``. The skip connections + the
       BN-front-of-block ordering are the two ingredients Gorishniy
       reports as decisive.
    2. **LR warmup**: ``SequentialLR(LinearLR(0.1·lr → lr, 5 ep) →
       CosineAnnealingLR(195 ep))`` via the new ``PyTorchTrainer.warmup_epochs``
       kwarg landed alongside this plan in ``_nn_common.py``.

Everything else — the 4 categorical embeddings, engineered scalars,
KMeans-64 ``geo_cluster``, GeoKNN OOF features, slot-0-unknown encoding,
the joblib bundle schema, the cold-load registry contract — is reused
from Plan 2. The only train()-pipeline differences vs ``nn_v2.train``
are the model class, the trainer kwargs (200 ep, wd=1e-5, warmup=5,
patience=20), and the ARTIFACT_DIR.

Reference baselines:
    * ``udi/nn_v1``       MAPE 0.2772
    * ``udi/nn_v2``       MAPE 0.2250
    * ``udi/xgboost_v3``  MAPE 0.1985
    * ``moses/stacked_v1`` MAPE 0.1869

Realistic ``nn_v3`` MAPE: 0.19-0.21 — should close most of the v2→v3
gap; tying ``udi/xgboost_v3`` 0.1985 is the stretch goal.

Run with::

    python3 run.py udi/nn_v3 --data v2
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F  # noqa: N812 — torch convention
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
# codebook ``[-1..63]`` by build_engineered_features). Duplicated verbatim
# from ``models/udi/nn_v2.py`` — Plan 3 stays scoped to architecture +
# scheduling and intentionally avoids refactoring v2; a future cleanup
# could promote LOADER_CAT_COLS + _align_train_val_categories to
# ``_nn_common.py``.
LOADER_CAT_COLS: tuple[str, ...] = ("city", "neighborhood", "deal_nature")

ARTIFACT_DIR = (
    Path(__file__).resolve().parents[2] / "artifacts" / "udi" / "nn_v3"
)

# ResNet-tabular hyperparams (Gorishniy 2021 §"Model 3" defaults).
D_HIDDEN = 256
N_BLOCKS = 4
DROPOUT = 0.1

# Optimizer + scheduler.
N_EPOCHS = 200
BATCH_SIZE = 1024
LR = 1e-3
WEIGHT_DECAY = 1e-5
WARMUP_EPOCHS = 5
PATIENCE = 20
SEED = 42

PREDICT_CHUNK = 8192


# ---------------------------------------------------------------------------
# ResidualBlock (Gorishniy 2021 §"Model 3"):
#   BN → Linear(d, 2d) → ReLU → Dropout → Linear(2d, d) → Dropout → +skip
#
# Note: not @register_model — only ``ResNetTabular`` is reconstructed from
# the bundle directly; ``ResidualBlock`` is an internal building block.
# ---------------------------------------------------------------------------
class ResidualBlock(nn.Module):
    """Pre-norm residual block: BN → Linear(d,2d) → ReLU → Dropout → Linear(2d,d) → Dropout → +x."""

    def __init__(self, d: int, dropout: float = DROPOUT) -> None:
        super().__init__()
        self.bn = nn.BatchNorm1d(d)
        self.fc1 = nn.Linear(d, 2 * d)
        self.fc2 = nn.Linear(2 * d, d)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = self.bn(x)
        h = F.relu(self.fc1(h))
        h = self.dropout(h)
        h = self.fc2(h)
        h = self.dropout(h)
        return x + h


# ---------------------------------------------------------------------------
# ResNetTabular
# ---------------------------------------------------------------------------
@register_model
class ResNetTabular(nn.Module):
    """ResNet-tabular: per-cat embeddings → input projection → N residual blocks → BN+Linear→1.

    Embedding dim heuristic identical to ``EmbedMLP`` from Plan 2:
    ``dim = min(50, (card+1)//2)``. Slot 0 of each ``nn.Embedding`` is
    reserved for the unknown/NaN level (see ``TabularPreprocessor`` cat
    path), so each embedding is sized ``num_embeddings = card + 1``.
    """

    def __init__(
        self,
        num_in_dim: int,
        cat_cardinalities: list[int],
        d: int = D_HIDDEN,
        n_blocks: int = N_BLOCKS,
        dropout: float = DROPOUT,
    ) -> None:
        super().__init__()
        # Cast int(card) per-element so a numpy-int list survives the
        # joblib round-trip (mirrors ``EmbedMLP.__init__`` Plan 2).
        self.num_in_dim = int(num_in_dim)
        self.cat_cardinalities = [int(c) for c in cat_cardinalities]
        self.d = int(d)
        self.n_blocks = int(n_blocks)
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
        self.input_proj = nn.Linear(in_dim, self.d)
        self.blocks = nn.ModuleList(
            [ResidualBlock(self.d, self.dropout) for _ in range(self.n_blocks)]
        )
        self.head_bn = nn.BatchNorm1d(self.d)
        self.head = nn.Linear(self.d, 1)

    def forward(
        self, x_num: torch.Tensor, x_cat: torch.Tensor
    ) -> torch.Tensor:
        embedded = [
            self.embeddings[i](x_cat[:, i]) for i in range(len(self.embeddings))
        ]
        x = torch.cat([x_num] + embedded, dim=-1)
        x = self.input_proj(x)
        for blk in self.blocks:
            x = blk(x)
        return self.head(self.head_bn(x))


# ---------------------------------------------------------------------------
# Categorical alignment helper (duplicated verbatim from
# ``models/udi/nn_v2.py`` — see LOADER_CAT_COLS comment above for why).
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
    """Train ``ResNetTabular`` over the v2 feature pipeline + return a joblib-able bundle."""
    gen = set_global_seeds(SEED)

    y_train_arr = np.asarray(y_train, dtype=float)
    y_val_arr = np.asarray(y_val, dtype=float)
    y_train_log = np.log1p(y_train_arr)
    y_val_log = np.log1p(y_val_arr)

    # 1. Align loader categoricals on train→val (geo_cluster is added in
    #    step 3 by build_engineered_features and uses a fixed codebook).
    X_train_a, X_val_a = _align_train_val_categories(X_train, X_val)

    # 2. KMeans on train coords only — geo_cluster is required by the
    #    preprocessor's cat path.
    kmeans = fit_kmeans(X_train_a)
    if kmeans is None:
        raise RuntimeError(
            "nn_v3 requires geo_cluster — fit_kmeans returned None "
            "(insufficient lat/lon coverage)"
        )

    # 3. Engineered features on both slices.
    X_train_eng = build_engineered_features(X_train_a, kmeans)
    X_val_eng = build_engineered_features(X_val_a, kmeans)

    # 4. GeoKNN: 5-fold OOF for train, BallTree on full-train for val.
    print("  [nn_v3] computing OOF GeoKNN features for train...")
    train_knn = oof_train_knn(X_train_eng, y_train_arr)
    print("  [nn_v3] fitting KNN BallTree on full train + transforming val...")
    knn_builder = KnnFeatureBuilder()
    knn_builder.fit(X_train_eng, y_train_arr)
    val_knn = knn_builder.transform(X_val_eng)

    nan_train = float(train_knn.isna().mean().mean())
    nan_val = float(val_knn.isna().mean().mean())
    print(
        f"  [nn_v3] KNN-feature NaN rate: train={nan_train:.1%}  val={nan_val:.1%}"
    )

    X_train_full_pre = pd.concat([X_train_eng, train_knn], axis=1)
    X_val_full_pre = pd.concat([X_val_eng, val_knn], axis=1)

    # 5. Drop dead cols on train; mirror exactly on val.
    X_train_full, dropped = drop_dead_cols(X_train_full_pre)
    X_val_full = X_val_full_pre.drop(columns=dropped, errors="ignore")
    if dropped:
        print(f"  [nn_v3] dropped dead columns: {dropped}")

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
        f"  [nn_v3] num_in_dim={X_num_train.shape[1]} "
        f"(numeric={len(pre._numeric_cols)} + nan_indicators={len(pre._nan_indicator_cols)})  "
        f"cat_cardinalities={cards}"
    )

    # 7. Build model + probe device. ResNetTabular contains BatchNorm1d
    #    (one per ResidualBlock + the head BN), so the helper short-circuits
    #    MPS→CPU before any forward pass — same path v1's MLP and v2's
    #    EmbedMLP exercise. v3 trains on CPU.
    #
    #    Note on the helper signature: ``_safe_device_with_fallback`` passes
    #    ``sample_batch`` (single tensor) into ``model(sample)`` if the
    #    BN1d short-circuit doesn't fire first. ResNetTabular.forward takes
    #    ``(x_num, x_cat)`` so the probe-time call would crash on a CUDA
    #    box; on the dev machine the BN1d short-circuit pins to CPU before
    #    the probe runs. Latent issue inherited from v2; left for a
    #    LayerNorm-only architecture to surface.
    model = ResNetTabular(
        num_in_dim=X_num_train.shape[1],
        cat_cardinalities=list(cards),
        d=D_HIDDEN,
        n_blocks=N_BLOCKS,
        dropout=DROPOUT,
    )
    probe_n = min(BATCH_SIZE, X_num_train.shape[0])
    sample_batch = torch.from_numpy(X_num_train[:probe_n].astype(np.float32))
    device = _safe_device_with_fallback(model, sample_batch, n_probe_steps=20)
    print(f"  [nn_v3] training on device: {device}")

    # 8. Trainer with the new warmup branch (Plan 3 trainer extension).
    trainer = PyTorchTrainer(
        device=device,
        generator=gen,
        n_epochs=N_EPOCHS,
        batch_size=BATCH_SIZE,
        lr=LR,
        weight_decay=WEIGHT_DECAY,
        patience=PATIENCE,
        warmup_epochs=WARMUP_EPOCHS,
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
        f"  [nn_v3] training done: epochs_run={len(history)} "
        f"final_val_mape={final_val:.4f} best_val_mape={best_val:.4f}"
    )

    # 9. Build the bundle. dropped_cols = ONLY dead cols (the 3 raw cats
    #    are NOT dropped — they're embedded; geo_cluster is added by
    #    build_engineered_features in predict()). model_class_name is
    #    auto-derived inside save_bundle from type(trained).__name__.
    model_kwargs = {
        "num_in_dim": int(X_num_train.shape[1]),
        "cat_cardinalities": list(cards),
        "d": D_HIDDEN,
        "n_blocks": N_BLOCKS,
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
    """Score ``X`` with a trained nn_v3 bundle. CPU-only inference.

    Body byte-identical to ``nn_v2.predict`` — the model class is
    resolved automatically through ``bundle["model_class_name"]`` →
    ``MODEL_REGISTRY``. Importing this module (which the runner does
    before calling ``predict``) is what populates
    ``MODEL_REGISTRY["ResNetTabular"]``.
    """
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
            "produced by nn_v3.train?"
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
