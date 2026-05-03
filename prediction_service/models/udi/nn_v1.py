"""udi/nn_v1 — numeric-only MLP baseline.

Plan 1 of the NN ladder. This is the *baseline* — no categorical
embeddings, no engineered features, no GeoKNN. Its job is to land the
runner-contract surface (joblib bundle schema, MODEL_REGISTRY round-trip,
MPS device handling) so Plans 2-4 can extend a known-working scaffold.

Reference baselines (no need to beat in this plan):
    * udi/xgboost_v3   MAPE 0.1985
    * moses/stacked_v1 MAPE 0.1869
Realistic v1 MAPE: 0.22-0.25.

Run with:
    python3 run.py udi/nn_v1 --data v2
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from torch import nn

from models.udi._nn_common import (
    PyTorchTrainer,
    TabularPreprocessor,
    _safe_device_with_fallback,
    drop_dead_cols,
    load_bundle,
    register_model,
    save_bundle,
    set_global_seeds,
)

CAT_COLS: tuple[str, ...] = ("city", "neighborhood", "deal_nature")

ARTIFACT_DIR = (
    Path(__file__).resolve().parents[2] / "artifacts" / "udi" / "nn_v1"
)

HIDDEN_DIMS: tuple[int, ...] = (256, 128, 64)
DROPOUT = 0.3
N_EPOCHS = 100
BATCH_SIZE = 1024
LR = 1e-3
WEIGHT_DECAY = 1e-4
PATIENCE = 15
SEED = 42

PREDICT_CHUNK = 8192


# ---------------------------------------------------------------------------
# MLP
# ---------------------------------------------------------------------------
@register_model
class MLP(nn.Module):
    """4-layer MLP regressor — Linear→BN→ReLU→Dropout × 3 + Linear(→1)."""

    def __init__(
        self,
        in_dim: int,
        hidden_dims: tuple[int, ...] = HIDDEN_DIMS,
        dropout: float = DROPOUT,
    ) -> None:
        super().__init__()
        self.in_dim = int(in_dim)
        self.hidden_dims = tuple(int(h) for h in hidden_dims)
        self.dropout = float(dropout)

        layers: list[nn.Module] = []
        prev = self.in_dim
        for h in self.hidden_dims:
            layers.append(nn.Linear(prev, h))
            layers.append(nn.BatchNorm1d(h))
            layers.append(nn.ReLU(inplace=True))
            layers.append(nn.Dropout(self.dropout))
            prev = h
        layers.append(nn.Linear(prev, 1))
        self.net = nn.Sequential(*layers)

    def forward(self, x_num: torch.Tensor) -> torch.Tensor:
        return self.net(x_num)


# ---------------------------------------------------------------------------
# Train
# ---------------------------------------------------------------------------
def train(
    X_train: pd.DataFrame,
    y_train: np.ndarray,
    X_val: pd.DataFrame,
    y_val: np.ndarray,
) -> dict[str, Any]:
    """Train the MLP baseline and return a joblib-able bundle dict."""
    gen = set_global_seeds(SEED)

    y_train_log = np.log1p(np.asarray(y_train, dtype=float))
    y_val_log = np.log1p(np.asarray(y_val, dtype=float))

    # 1. Drop the 3 raw categoricals — numeric-only baseline.
    X_train_no_cat = X_train.drop(columns=list(CAT_COLS), errors="ignore")
    X_val_no_cat = X_val.drop(columns=list(CAT_COLS), errors="ignore")

    # 2. Drop dead columns. Mirror the train drop set on val (do NOT
    #    re-derive on val: a column may be present on val but not on train
    #    and we want predict-set consistency to come from train).
    X_train_trim, dropped = drop_dead_cols(X_train_no_cat)
    X_val_trim = X_val_no_cat.drop(columns=dropped, errors="ignore")

    # 3. Numeric-only preprocessor (frozen column order + reindex on transform).
    pre = TabularPreprocessor(include_categorical=False)
    pre.fit(X_train_trim)
    X_num_train, _, _ = pre.transform(X_train_trim)
    X_num_val, _, _ = pre.transform(X_val_trim)

    print(
        f"  [nn_v1] in_dim={X_num_train.shape[1]} "
        f"(numeric={len(pre._numeric_cols)} + nan_indicators={len(pre._nan_indicator_cols)})"
    )

    # 4. Build model, probe device with the BN-safe fallback.
    #    Probe batch matches the real training batch size — the BN1d-on-MPS
    #    bug only manifests at realistic batch sizes; a small probe (e.g.
    #    8 rows) silently passes and then training silently NaNs out.
    model = MLP(in_dim=X_num_train.shape[1])
    probe_n = min(BATCH_SIZE, X_num_train.shape[0])
    sample_batch = torch.from_numpy(X_num_train[:probe_n].astype(np.float32))
    device = _safe_device_with_fallback(model, sample_batch, n_probe_steps=20)
    print(f"  [nn_v1] training on device: {device}")

    # 5. Trainer — artifact_dir is mkdir-ed by PyTorchTrainer.__init__,
    #    *before* run.py mkdirs `out_dir` (which only happens after train()
    #    returns).
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
        None,
        y_train_log,
        X_num_val,
        None,
        y_val_log,
    )

    final_val = history[-1]["val_mape"] if history else float("nan")
    best_val = (
        min(h["val_mape"] for h in history) if history else float("nan")
    )
    print(
        f"  [nn_v1] training done: epochs_run={len(history)} "
        f"final_val_mape={final_val:.4f} best_val_mape={best_val:.4f}"
    )

    # 6. Build the bundle. Notice: the live `trained` module is consumed
    #    only to read state_dict + class name; the bundle stores those,
    #    not the module instance. dropped_cols = raw categoricals + dead.
    model_kwargs = {
        "in_dim": X_num_train.shape[1],
        "hidden_dims": HIDDEN_DIMS,
        "dropout": DROPOUT,
    }
    bundle = save_bundle(
        model=trained,
        model_kwargs=model_kwargs,
        preprocessor=pre,
        dropped_cols=[*CAT_COLS, *dropped],
        kmeans=None,
        knn_builder=None,
        y_log_mean=y_log_mean,
        y_log_std=y_log_std,
        feature_columns=pre.feature_columns,
        cat_cardinalities=[],
        candidate_results=[],
        best_candidate={},
        history=history,
    )
    return bundle


# ---------------------------------------------------------------------------
# Predict
# ---------------------------------------------------------------------------
def predict(bundle: dict[str, Any], X: pd.DataFrame) -> np.ndarray:
    """Score X with a trained nn_v1 bundle. CPU-only inference."""
    X_trim = X.drop(columns=bundle["dropped_cols"], errors="ignore")
    X_num, _, _ = bundle["preprocessor"].transform(X_trim)

    model = load_bundle(bundle, device=torch.device("cpu"))

    # Importing this module is what populated MODEL_REGISTRY['MLP']; if a
    # caller reaches predict(), they've already imported nn_v1 so we're fine.
    x_t = torch.from_numpy(np.asarray(X_num, dtype=np.float32))
    preds_std: list[np.ndarray] = []
    with torch.no_grad():
        for start in range(0, x_t.size(0), PREDICT_CHUNK):
            chunk = x_t[start : start + PREDICT_CHUNK]
            out = model(chunk).squeeze(-1)
            preds_std.append(out.detach().cpu().numpy())

    pred_std_arr = (
        np.concatenate(preds_std, axis=0)
        if preds_std
        else np.empty((0,), dtype=np.float32)
    )
    pred_log = pred_std_arr * bundle["y_log_std"] + bundle["y_log_mean"]
    pred = np.clip(np.expm1(pred_log), a_min=1.0, a_max=None)
    return pred.astype(float)
