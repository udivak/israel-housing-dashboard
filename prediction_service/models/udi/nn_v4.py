"""udi/nn_v4 — FT-Transformer (Gorishniy et al. 2021), hand-rolled.

Plan 4 of the NN ladder. Architectural lift over ``udi/nn_v3``:

    1. **Feature tokenization**: every numeric column (incl. ``<col>_nan``
       indicators) and every categorical column becomes a single
       ``d_token``-dim token; numeric tokenization is vectorised via two
       ``nn.Parameter`` tensors (no per-feature ``Linear(1, d_token)``
       loop), categoricals use one ``nn.Embedding(card+1, d_token)`` per
       column reusing the slot-0-unknown convention from Plan 2.
    2. **Pre-norm transformer blocks**: 3 stacked
       ``LayerNorm → MultiheadAttention(d_token, n_heads=8, dropout=0.2)
       → +skip → LayerNorm → FFN(d_token → 2·d_token → d_token, GELU,
       Dropout 0.1) → +skip``.
    3. **[CLS] readout**: a learned ``nn.Parameter(1, 1, d_token)`` token
       is prepended to the token sequence; the final ``LayerNorm + Linear(d_token, 1)``
       head reads only its position. Same pattern as Devlin BERT or
       Dosovitskiy ViT.

Everything else — the 4 categorical embeddings (just re-cast as token
producers now), engineered scalars, KMeans-64 ``geo_cluster``, GeoKNN OOF
features, slot-0-unknown encoding, the joblib bundle schema, the
class registry — is reused from Plan 2/3.

Reference baselines (Run 7-11):
    * ``udi/nn_v1``       MAPE 0.2772 (Run 7)
    * ``udi/nn_v2``       MAPE 0.2250 (Run 8)
    * ``udi/nn_v3``       MAPE 0.2203 (Run 9)
    * ``udi/blend_v1``    MAPE 0.1972 (Run 10) — current udi/* champion
    * ``udi/nn_v3b``      MAPE 0.2172 (Run 11) — latest NN benchmark
    * ``udi/xgboost_v3``  MAPE 0.1985 (Run 4) — reference baseline
    * ``moses/stacked_v1`` MAPE 0.1869 — project champion

Realistic v4 MAPE: 0.18-0.20. Stretch goal: beats ``udi/blend_v1``.

Run with::

    python3 run.py udi/nn_v4 --data v2
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from torch import Tensor, nn

from models.udi._nn_common import (
    KnnFeatureBuilder,
    PyTorchTrainer,
    TabularPreprocessor,
    build_engineered_features,
    drop_dead_cols,
    fit_kmeans,
    load_bundle,
    oof_train_knn,
    register_model,
    save_bundle,
    set_global_seeds,
)
from models.udi.nn_v3 import (
    LOADER_CAT_COLS,
    _align_train_val_categories,
)

ARTIFACT_DIR = (
    Path(__file__).resolve().parents[2] / "artifacts" / "udi" / "nn_v4"
)

# FT-Transformer hyperparams (Gorishniy 2021 §"FT-Transformer" defaults
# scaled to this slice — d_token=192 instead of 256, n_blocks=3 instead of 4
# to keep CPU compute feasible on this slice).
#
# Device note: this implementation FORCES CPU. We initially probed MPS via
# ``_safe_device_with_fallback`` and the probe passed cleanly, but the
# full training loop produced ``train_loss=NaN`` at epoch 10 on every MPS
# attempt — even with ``ATTN_DROPOUT=0`` (the published-PyTorch-#96702
# workaround) and ``GRAD_CLIP=1.0``. Standalone 1000-step probes on MPS
# stayed numerically clean, which points to validation-pass activation
# pressure (val_chunk = batch_size * 4 = 2048 → ~1.5 GB attention
# activation tensor, peak unified-memory footprint ~19.5 GB) silently
# producing NaN under MPS OOM rather than raising. CPU sidesteps the
# issue and is fast enough on Apple Silicon (BF16 matmul accelerator)
# to land in budget.
D_TOKEN = 192
N_HEADS = 8
N_BLOCKS = 3
ATTN_DROPOUT = 0.2
FFN_DROPOUT = 0.1

# Optimizer + scheduler. Transformers are notoriously LR-sensitive — lr=1e-4
# + 10-epoch warmup is the FT-Transformer paper's published recipe.
# ``GRAD_CLIP=1.0`` is the standard transformer recipe for preventing
# gradient explosions during the warmup ramp; routed via the new
# ``PyTorchTrainer.grad_clip`` kwarg (default ``None`` so v1/v2/v3 reruns
# stay bit-identical).
N_EPOCHS = 60
BATCH_SIZE = 512
LR = 1e-4
WEIGHT_DECAY = 1e-5
WARMUP_EPOCHS = 10
PATIENCE = 12
GRAD_CLIP = 1.0
SEED = 42

# Inference-time chunk. Attention activation memory scales O(B · n_heads · T²)
# on the chunk dim too; with ~81 tokens, chunk=8192 (v2/v3 default) would peak
# at ~5 GB during the no-grad forward. chunk=2048 keeps inference peak under
# ~1.5 GB and matches the train val-chunk by coincidence (= batch_size * 4).
PREDICT_CHUNK = 2048


# ---------------------------------------------------------------------------
# Tokenizers (Part A of the plan)
# ---------------------------------------------------------------------------
class NumericTokenizer(nn.Module):
    """Vectorised numeric-feature tokenizer.

    Equivalent to running a ``Linear(1, d_token)`` per numeric column
    but expressed as two ``nn.Parameter`` tensors so the forward pass
    is a single broadcast multiply-add — no per-feature Python loop.
    """

    def __init__(self, n_num: int, d_token: int) -> None:
        super().__init__()
        self.n_num = int(n_num)
        self.d_token = int(d_token)
        self.weight = nn.Parameter(torch.empty(n_num, d_token))
        self.bias = nn.Parameter(torch.empty(n_num, d_token))
        nn.init.kaiming_uniform_(self.weight, a=math.sqrt(5))
        bound = 1.0 / math.sqrt(d_token)
        nn.init.uniform_(self.bias, -bound, bound)

    def forward(self, x_num: Tensor) -> Tensor:
        # x_num: (B, n_num) -> (B, n_num, d_token)
        return x_num.unsqueeze(-1) * self.weight + self.bias


class CategoricalTokenizer(nn.Module):
    """Per-cat ``nn.Embedding(card+1, d_token)`` stack (slot 0 = unknown)."""

    def __init__(self, cat_cardinalities: list[int], d_token: int) -> None:
        super().__init__()
        self.embeds = nn.ModuleList(
            [nn.Embedding(int(card) + 1, d_token) for card in cat_cardinalities]
        )

    def forward(self, x_cat: Tensor) -> Tensor:
        # x_cat: (B, n_cat) -> (B, n_cat, d_token)
        return torch.stack(
            [emb(x_cat[:, i]) for i, emb in enumerate(self.embeds)], dim=1
        )


# ---------------------------------------------------------------------------
# Transformer backbone (Part B of the plan)
# ---------------------------------------------------------------------------
class TransformerBlock(nn.Module):
    """Pre-norm transformer block: LN→MHA→+skip→LN→FFN→+skip."""

    def __init__(
        self,
        d_token: int,
        n_heads: int,
        attn_dropout: float,
        ffn_dropout: float,
    ) -> None:
        super().__init__()
        self.ln1 = nn.LayerNorm(d_token)
        self.attn = nn.MultiheadAttention(
            embed_dim=d_token,
            num_heads=n_heads,
            dropout=attn_dropout,
            batch_first=True,
        )
        self.ln2 = nn.LayerNorm(d_token)
        self.ffn = nn.Sequential(
            nn.Linear(d_token, 2 * d_token),
            nn.GELU(),
            nn.Dropout(ffn_dropout),
            nn.Linear(2 * d_token, d_token),
        )

    def forward(self, tokens: Tensor) -> Tensor:
        h = self.ln1(tokens)
        attn_out, _ = self.attn(h, h, h, need_weights=False)
        tokens = tokens + attn_out
        h = self.ln2(tokens)
        tokens = tokens + self.ffn(h)
        return tokens


@register_model
class FTTransformer(nn.Module):
    """FT-Transformer per Gorishniy 2021: feature tokenization + [CLS] + 3 transformer blocks.

    Token sequence layout: ``[CLS, *num_tokens, *cat_tokens]`` of shape
    ``(B, 1+n_num+n_cat, d_token)``. ``cls`` is a learned
    ``nn.Parameter(1, 1, d_token)``; the head reads ``tokens[:, 0]`` only
    after a final ``LayerNorm`` + ``Linear(d_token, 1)``.
    """

    def __init__(
        self,
        num_in_dim: int,
        cat_cardinalities: list[int],
        d_token: int = D_TOKEN,
        n_heads: int = N_HEADS,
        n_blocks: int = N_BLOCKS,
        attn_dropout: float = ATTN_DROPOUT,
        ffn_dropout: float = FFN_DROPOUT,
    ) -> None:
        super().__init__()
        # Cast int(card) per-element so a numpy-int list survives the
        # joblib round-trip (mirrors ``ResNetTabular.__init__`` Plan 3).
        self.num_in_dim = int(num_in_dim)
        self.cat_cardinalities = [int(c) for c in cat_cardinalities]
        self.d_token = int(d_token)
        self.n_heads = int(n_heads)
        self.n_blocks = int(n_blocks)
        self.attn_dropout = float(attn_dropout)
        self.ffn_dropout = float(ffn_dropout)

        self.num_tok = NumericTokenizer(self.num_in_dim, self.d_token)
        self.cat_tok = CategoricalTokenizer(self.cat_cardinalities, self.d_token)
        self.cls = nn.Parameter(torch.zeros(1, 1, self.d_token))
        nn.init.normal_(self.cls, std=0.02)
        self.blocks = nn.ModuleList(
            [
                TransformerBlock(
                    self.d_token,
                    self.n_heads,
                    self.attn_dropout,
                    self.ffn_dropout,
                )
                for _ in range(self.n_blocks)
            ]
        )
        self.head_ln = nn.LayerNorm(self.d_token)
        self.head = nn.Linear(self.d_token, 1)

    def forward(self, x_num: Tensor, x_cat: Tensor) -> Tensor:
        b = x_num.size(0)
        tokens = torch.cat(
            [
                self.cls.expand(b, -1, -1),
                self.num_tok(x_num),
                self.cat_tok(x_cat),
            ],
            dim=1,
        )
        for block in self.blocks:
            tokens = block(tokens)
        cls_out = tokens[:, 0]
        return self.head(self.head_ln(cls_out)).squeeze(-1)


# ---------------------------------------------------------------------------
# Train (Part C)
# ---------------------------------------------------------------------------
def train(
    X_train: pd.DataFrame,
    y_train: np.ndarray,
    X_val: pd.DataFrame,
    y_val: np.ndarray,
) -> dict[str, Any]:
    """Train ``FTTransformer`` over the v2 feature pipeline + return a joblib-able bundle."""
    gen = set_global_seeds(SEED)

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
            "nn_v4 requires geo_cluster — fit_kmeans returned None "
            "(insufficient lat/lon coverage)"
        )

    # 3. Engineered features on both slices.
    X_train_eng = build_engineered_features(X_train_a, kmeans)
    X_val_eng = build_engineered_features(X_val_a, kmeans)

    # 4. GeoKNN: 5-fold OOF for train, BallTree on full-train for val.
    print("  [nn_v4] computing OOF GeoKNN features for train...")
    train_knn = oof_train_knn(X_train_eng, y_train_arr)
    print("  [nn_v4] fitting KNN BallTree on full train + transforming val...")
    knn_builder = KnnFeatureBuilder()
    knn_builder.fit(X_train_eng, y_train_arr)
    val_knn = knn_builder.transform(X_val_eng)

    nan_train = float(train_knn.isna().mean().mean())
    nan_val = float(val_knn.isna().mean().mean())
    print(
        f"  [nn_v4] KNN-feature NaN rate: train={nan_train:.1%}  val={nan_val:.1%}"
    )

    X_train_full_pre = pd.concat([X_train_eng, train_knn], axis=1)
    X_val_full_pre = pd.concat([X_val_eng, val_knn], axis=1)

    # 5. Drop dead cols on train; mirror exactly on val.
    X_train_full, dropped = drop_dead_cols(X_train_full_pre)
    X_val_full = X_val_full_pre.drop(columns=dropped, errors="ignore")
    if dropped:
        print(f"  [nn_v4] dropped dead columns: {dropped}")

    # 6. Preprocessor (cat path, slot-0-unknown).
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
        f"  [nn_v4] num_in_dim={X_num_train.shape[1]} "
        f"(numeric={len(pre._numeric_cols)} + nan_indicators={len(pre._nan_indicator_cols)})  "
        f"cat_cardinalities={cards}"
    )

    # 7. Build model on CPU. We deliberately skip ``_safe_device_with_fallback``
    #    here (which would otherwise pick MPS since the architecture has no
    #    BatchNorm1d) — empirically the full training loop produces
    #    ``train_loss=NaN`` at epoch 10 on MPS despite the
    #    ``ATTN_DROPOUT=0`` + ``GRAD_CLIP=1.0`` mitigations and despite
    #    standalone 1000-step probes staying clean. See the module-level
    #    docstring "Device note" for the OOM-during-val-chunk hypothesis.
    #    The 2-arg extension to _safe_device_with_fallback added to
    #    _nn_common.py (Plan 4 §C.0) is still kept — it remains a valid
    #    forward-compat hook for future multi-input NN models — but is
    #    not exercised here.
    model = FTTransformer(
        num_in_dim=X_num_train.shape[1],
        cat_cardinalities=list(cards),
        d_token=D_TOKEN,
        n_heads=N_HEADS,
        n_blocks=N_BLOCKS,
        attn_dropout=ATTN_DROPOUT,
        ffn_dropout=FFN_DROPOUT,
    )
    device = torch.device("cpu")
    model.to(device)
    print(f"  [nn_v4] training on device: {device} (forced; see Device note)")

    # 8. Trainer: same as nn_v3's PyTorchTrainer call but with v4-specific
    #    kwargs (lr=1e-4, batch=512, warmup=10, patience=20, n_epochs=150).
    #    PyTorchTrainer.fit hardcodes ``chunk = batch_size * 4`` for the val
    #    pass — with batch_size=512 this evaluates to 2048, which is exactly
    #    the val-chunk the master plan called for (no trainer kwarg needed).
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
        grad_clip=GRAD_CLIP,
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
        f"  [nn_v4] training done: epochs_run={len(history)} "
        f"final_val_mape={final_val:.4f} best_val_mape={best_val:.4f}"
    )

    # 9. Attention rollup on a 2048-row val sample (top-15 features).
    #    Dump to artifacts/udi/nn_v4/attention_rollup.json for EXPERIMENTS.md
    #    Run 12 Notes.
    feature_names = (
        list(pre._numeric_cols)
        + [f"{c}_nan" for c in pre._nan_indicator_cols]
        + list(pre._cat_cols)
    )
    rollup_n = min(2048, X_num_val.shape[0])
    sample_num_t = torch.from_numpy(X_num_val[:rollup_n].astype(np.float32))
    sample_cat_t = torch.from_numpy(X_cat_val[:rollup_n].astype(np.int64))
    try:
        rollup = attention_rollup(
            trained, feature_names, sample_num_t, sample_cat_t, top_k=15
        )
        ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
        (ARTIFACT_DIR / "attention_rollup.json").write_text(
            json.dumps(rollup, indent=2)
        )
        print(
            f"  [nn_v4] attention rollup top-3: "
            f"{[(r['feature_name'], round(r['attention_weight'], 4)) for r in rollup[:3]]}"
        )
    except Exception as exc:  # noqa: BLE001 — diagnostic, must not block the bundle
        print(f"  [nn_v4] attention_rollup failed (non-fatal): {exc}")

    # 10. Build the bundle. dropped_cols = ONLY dead cols (the 4 cats are
    #     embedded; geo_cluster is added by build_engineered_features in
    #     predict()). model_class_name auto-derived inside save_bundle.
    model_kwargs = {
        "num_in_dim": int(X_num_train.shape[1]),
        "cat_cardinalities": list(cards),
        "d_token": D_TOKEN,
        "n_heads": N_HEADS,
        "n_blocks": N_BLOCKS,
        "attn_dropout": ATTN_DROPOUT,
        "ffn_dropout": FFN_DROPOUT,
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
# Predict (Part C.3)
# ---------------------------------------------------------------------------
def predict(bundle: dict[str, Any], X: pd.DataFrame) -> np.ndarray:
    """Score ``X`` with a trained nn_v4 bundle. CPU-only inference.

    Body identical to ``nn_v3.predict`` except for ``PREDICT_CHUNK=2048``
    (vs 8192) — attention activation memory scales O(B · n_heads · T²),
    so a smaller chunk keeps inference peak under ~1.5 GB.
    """
    pre: TabularPreprocessor = bundle["preprocessor"]

    # 1. Re-align loader categoricals to the train snapshot.
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

    # 5. Preprocessor splits into (X_num, X_cat, _).
    X_num, X_cat, _ = pre.transform(X_full)

    if X_cat is None:
        raise RuntimeError(
            "Preprocessor returned X_cat=None during predict — bundle was "
            "saved without the categorical path; was this bundle actually "
            "produced by nn_v4.train?"
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


# ---------------------------------------------------------------------------
# Attention rollup (Part E)
# ---------------------------------------------------------------------------
def attention_rollup(
    model: FTTransformer,
    feature_names: list[str],
    X_num_sample: Tensor,
    X_cat_sample: Tensor,
    top_k: int = 15,
) -> list[dict[str, Any]]:
    """Per-feature [CLS]→token attention summed across the 3 transformer blocks.

    Strategy:
        1. Monkey-patch ``TransformerBlock.forward`` for the duration of
           the rollup pass to plumb ``need_weights=True`` and capture the
           per-block attention matrix into a list.
        2. Run a single no-grad eval-mode forward on the ``(X_num, X_cat)``
           sample.
        3. For each captured attention matrix ``(B, T, T)``, take the
           [CLS] query row (index 0), drop the [CLS]→[CLS] self-attention
           column, average across the batch dim → ``(T-1,)``.
        4. Sum across blocks → aggregated per-feature attention weight.
        5. Sort descending; return top-``k`` ``{feature_name, attention_weight}`` dicts.

    ``feature_names`` MUST be ordered as
    ``pre._numeric_cols + [f"{c}_nan" for c in pre._nan_indicator_cols]
    + pre._cat_cols`` (the token-sequence ordering produced by
    ``NumericTokenizer`` then ``CategoricalTokenizer`` after the [CLS]
    token).
    """
    captured: list[Tensor] = []

    def patched_forward(self: TransformerBlock, tokens: Tensor) -> Tensor:
        h = self.ln1(tokens)
        attn_out, attn_weights = self.attn(
            h, h, h, need_weights=True, average_attn_weights=True
        )
        captured.append(attn_weights.detach())
        tokens = tokens + attn_out
        h = self.ln2(tokens)
        tokens = tokens + self.ffn(h)
        return tokens

    original_forward = TransformerBlock.forward
    TransformerBlock.forward = patched_forward  # type: ignore[method-assign]
    was_training = model.training
    model.eval()
    try:
        with torch.no_grad():
            model(X_num_sample, X_cat_sample)
    finally:
        TransformerBlock.forward = original_forward  # type: ignore[method-assign]
        model.train(was_training)

    if not captured:
        raise RuntimeError(
            "attention_rollup: no attention matrices captured (forward did "
            "not traverse any TransformerBlock — model architecture mismatch?)"
        )

    # Per-block: attn[:, 0, 1:] = [CLS]→{numeric+cat tokens} (drop CLS→CLS).
    per_block: list[np.ndarray] = []
    for w in captured:
        cls_row = w[:, 0, 1:]
        per_block.append(cls_row.mean(dim=0).cpu().numpy())

    aggregated = np.sum(np.stack(per_block, axis=0), axis=0)

    if aggregated.shape[0] != len(feature_names):
        raise RuntimeError(
            f"attention_rollup: feature_names length ({len(feature_names)}) "
            f"!= attention dim ({aggregated.shape[0]}). Token-order contract "
            "was violated."
        )

    order = np.argsort(-aggregated)[:top_k]
    return [
        {
            "feature_name": feature_names[int(i)],
            "attention_weight": float(aggregated[int(i)]),
        }
        for i in order
    ]
