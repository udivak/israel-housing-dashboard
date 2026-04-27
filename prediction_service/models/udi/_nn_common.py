"""Shared neural-network helpers for udi/* models.

Plan 1 (slim) skeleton — categorical/embedding/engineered/KNN paths are
deferred to Plan 2; SequentialLR + warmup is deferred to Plan 3. Markers
of the form ``# TODO(plan-2)`` / ``# TODO(plan-3)`` flag the integration
points the next sub-plans will edit.

Cold-load contract — IMPORTANT
------------------------------
``MODEL_REGISTRY`` is populated as an *import-time side-effect* of the
``@register_model`` decorator on each NN class (e.g. ``MLP`` in
``models/udi/nn_v1.py``). A fresh Python process that calls
``joblib.load(...)`` followed by ``load_bundle(...)`` without first
importing the model module will hit ``KeyError: <ClassName>``.

Therefore any cold-load caller — round-trip script, future ``serve.py``
wrapper, notebook — MUST do::

    import models.udi.nn_v1   # populates _nn_common.MODEL_REGISTRY['MLP']
    bundle = joblib.load("artifacts/udi/nn_v1/model.joblib")
    model = _nn_common.load_bundle(bundle)

The bundle stores ``state_dict`` (CPU tensors) + ``model_class_name`` +
``model_kwargs`` — never the live ``nn.Module`` instance — so the
roundtrip is device-portable and survives the registered class being
redefined between train and predict.
"""

from __future__ import annotations

import copy
import json
import random
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from sklearn.impute import SimpleImputer  # pyright: ignore[reportMissingImports]
from sklearn.preprocessing import QuantileTransformer  # pyright: ignore[reportMissingImports]
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------
DEAD_COLS: tuple[str, ...] = (
    "is_old",
    "is_new",
    "is_new_project",
    "real_price_imputed",
)

NAN_INDICATOR_THRESHOLD = 0.01  # > 1% NaN on train → emit a `<col>_nan` indicator


# ---------------------------------------------------------------------------
# Device helpers
# ---------------------------------------------------------------------------
def _pick_device() -> torch.device:
    """Best available torch device — MPS > CUDA > CPU."""
    if torch.backends.mps.is_available() and torch.backends.mps.is_built():
        return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def _safe_device_with_fallback(
    model: nn.Module, sample_batch: torch.Tensor, n_probe_steps: int = 5
) -> torch.device:
    """Probe ``_pick_device()`` with a few train-mode steps; fall back to CPU on non-finite.

    Mitigates the BatchNorm1d-on-MPS bug — that bug only manifests during
    *training* (backward + BN running-stat updates), so an eval-mode
    ``no_grad`` forward isn't enough to catch it. Strategy:

    1. Pick the best available device (``_pick_device()``).
    2. Snapshot the model's full ``state_dict`` so probe-time perturbations
       to BN running stats / weights / num_batches_tracked can be undone.
    3. Run ``n_probe_steps`` train-mode forward+backward+AdamW steps on
       ``sample_batch`` against a zero target; if any output, loss, grad,
       or parameter goes non-finite, fall back to CPU.
    4. Restore the snapshotted state_dict so caller's training starts
       from the freshly-initialized weights (BN running stats reset).

    Caller contract — after this returns ``device``:

    * The model is **already on** ``device``.
    * BN running stats are restored to their post-construction defaults
      (clean training start).
    * The model's ``training`` flag is restored to its on-entry value.
    """
    picked = _pick_device()
    was_training = model.training

    # CPU never blows up on BN1d — skip the probe entirely.
    if picked.type == "cpu":
        return picked

    # MPS + BatchNorm1d is fundamentally unstable across torch builds
    # (the bug surfaces during training as exploding/NaN loss after
    # several hundred shuffled minibatches; a short probe can't reliably
    # reproduce it). Fail fast: if the model has any BN1d layer, pin to
    # CPU. Plans 2-4 add LayerNorm-only architectures that can re-enable
    # MPS later.
    if picked.type == "mps" and any(
        isinstance(m, nn.BatchNorm1d) for m in model.modules()
    ):
        print(
            "  [_nn_common] picked=mps but model has BatchNorm1d → CPU fallback "
            "(BN1d-on-MPS instability)."
        )
        cpu = torch.device("cpu")
        model.to(cpu)
        model.train(was_training)
        return cpu

    state_snapshot = {k: v.detach().clone() for k, v in model.state_dict().items()}

    def _restore(target_device: torch.device) -> None:
        model.to(target_device)
        model.load_state_dict(
            {k: v.to(target_device) for k, v in state_snapshot.items()}
        )
        model.train(was_training)

    try:
        model.to(picked)
        sample_on_device = sample_batch.to(picked)
        target = torch.zeros(sample_on_device.size(0), 1, device=picked)

        opt = torch.optim.AdamW(model.parameters(), lr=1e-3)
        loss_fn = nn.MSELoss()

        model.train()
        for step in range(n_probe_steps):
            opt.zero_grad(set_to_none=True)
            out = model(sample_on_device)
            if out.dim() == 1:
                out = out.unsqueeze(-1)
            loss = loss_fn(out, target)
            if not torch.isfinite(loss):
                raise RuntimeError(f"non-finite loss at probe step {step}")
            loss.backward()
            for p in model.parameters():
                if p.grad is not None and not torch.isfinite(p.grad).all():
                    raise RuntimeError(f"non-finite grad at probe step {step}")
            opt.step()
            for p in model.parameters():
                if not torch.isfinite(p).all():
                    raise RuntimeError(
                        f"non-finite parameter at probe step {step}"
                    )

        _restore(picked)
        return picked
    except Exception as exc:  # noqa: BLE001 — MPS surfaces RuntimeError + others
        print(f"  [_nn_common] device probe on {picked} failed → CPU. ({exc})")
        cpu = torch.device("cpu")
        _restore(cpu)
        return cpu


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------
def set_global_seeds(seed: int = 42) -> torch.Generator:
    """Seed Python/NumPy/Torch (CPU/CUDA/MPS) and return a seeded ``torch.Generator``.

    Used as ``DataLoader(generator=...)`` so shuffling is reproducible.

    Note: ``torch.use_deterministic_algorithms(False)`` is left as-is — full
    determinism on CUDA/MPS would force off several speed paths; we accept
    the ±0.001 noise band on per-epoch metrics.
    """
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    if torch.backends.mps.is_available() and hasattr(torch, "mps"):
        try:
            torch.mps.manual_seed(seed)  # newer torch builds only
        except AttributeError:
            pass
    gen = torch.Generator()
    gen.manual_seed(seed)
    return gen


# ---------------------------------------------------------------------------
# Dead-column drop
# ---------------------------------------------------------------------------
def drop_dead_cols(X: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Drop the locally-defined ``DEAD_COLS`` that are actually present.

    Returns the trimmed frame **and** the list of columns it actually
    dropped, so callers can mirror the same drop set on val/test/serving
    without re-deriving it from the raw column list.
    """
    dropped = [c for c in DEAD_COLS if c in X.columns]
    if dropped:
        return X.drop(columns=dropped), dropped
    return X, []


# ---------------------------------------------------------------------------
# Tabular preprocessor — numeric-only path (Plan 1)
# ---------------------------------------------------------------------------
class TabularPreprocessor:
    """Freeze a numeric column order on ``fit``; reindex + transform on ``transform``.

    Plan 1 implements only the ``include_categorical=False`` path. The
    categorical path will be filled in by Plan 2 (slot-0 unknown encoding,
    cardinalities, etc.).
    """

    def __init__(self, include_categorical: bool = True) -> None:
        self.include_categorical = include_categorical
        self._numeric_cols: list[str] = []
        self._nan_indicator_cols: list[str] = []
        self._imputer: SimpleImputer | None = None
        self._quantile: QuantileTransformer | None = None
        self.feature_columns: list[str] = []
        # TODO(plan-2): add categorical state
        #   self._cat_cols: list[str] = []
        #   self._cat_categories: dict[str, pd.Index] = {}
        #   self._cat_cardinalities: list[int] = []

    def fit(self, X: pd.DataFrame) -> "TabularPreprocessor":
        if self.include_categorical:
            # TODO(plan-2): implement categorical path
            raise NotImplementedError(
                "include_categorical=True is reserved for Plan 2"
            )

        # Drop columns that are entirely-NaN on train: SimpleImputer
        # skips them (UserWarning + values stay NaN), QuantileTransformer
        # then propagates NaN into the network and the loss explodes to
        # inf. They carry zero signal anyway, so freeze them out of the
        # canonical column order.
        all_nan_mask = X.isna().all()
        all_nan_cols = [c for c in X.columns if bool(all_nan_mask.get(c, False))]
        if all_nan_cols:
            print(
                f"  [TabularPreprocessor] dropping {len(all_nan_cols)} all-NaN cols "
                f"on train: {all_nan_cols}"
            )
        self._numeric_cols = [c for c in X.columns if c not in all_nan_cols]

        nan_rate = X[self._numeric_cols].isna().mean()
        self._nan_indicator_cols = [
            c
            for c in self._numeric_cols
            if float(nan_rate.get(c, 0.0)) > NAN_INDICATOR_THRESHOLD
        ]

        self._imputer = SimpleImputer(strategy="median")
        X_num = X[self._numeric_cols].astype(float)
        imputed = self._imputer.fit_transform(X_num)

        self._quantile = QuantileTransformer(
            output_distribution="normal", n_quantiles=1000, random_state=42
        )
        self._quantile.fit(imputed)

        self.feature_columns = list(self._numeric_cols) + [
            f"{c}_nan" for c in self._nan_indicator_cols
        ]
        return self

    def transform(
        self, X: pd.DataFrame
    ) -> tuple[np.ndarray, np.ndarray | None, list[int]]:
        if self._imputer is None or self._quantile is None:
            raise RuntimeError("TabularPreprocessor.transform called before fit")

        # Reindex to the frozen training column order. Missing columns
        # become all-NaN (imputer fills with train median); extras are
        # silently dropped. Makes predict() robust against slight column
        # drift between train and serving.
        X_aligned = X.reindex(columns=self._numeric_cols)

        # Indicator columns are computed on the reindexed frame *before*
        # imputation so they capture real missingness, not post-fill medians.
        if self._nan_indicator_cols:
            indicators = np.column_stack(
                [
                    X_aligned[c].isna().to_numpy().astype(np.float32)
                    for c in self._nan_indicator_cols
                ]
            )
        else:
            indicators = np.zeros((len(X_aligned), 0), dtype=np.float32)

        X_num_float = X_aligned.astype(float)
        imputed = self._imputer.transform(X_num_float)
        transformed = self._quantile.transform(imputed).astype(np.float32)

        if indicators.shape[1] > 0:
            X_num = np.concatenate([transformed, indicators], axis=1).astype(
                np.float32
            )
        else:
            X_num = transformed

        # Defensive sanitize: residual NaN/±inf would silently poison
        # BatchNorm and the MSE loss. Should be rare after the all-NaN
        # drop in fit() + the median imputer, but a serving frame may
        # legitimately introduce a column whose value imputed to inf
        # under odd dtypes.
        X_num = np.nan_to_num(X_num, nan=0.0, posinf=0.0, neginf=0.0).astype(
            np.float32
        )

        # X_cat / cat_cardinalities reserved for Plan 2.
        return X_num, None, []


# ---------------------------------------------------------------------------
# PyTorch trainer (no warmup yet — Plan 3 adds SequentialLR + LinearLR)
# ---------------------------------------------------------------------------
def _mape_real_scale(
    y_true: np.ndarray, y_pred: np.ndarray
) -> float:
    """Real-scale MAPE — y already exp-ed and clamped."""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    mask = y_true > 0
    if not mask.any():
        return float("nan")
    return float(np.mean(np.abs(y_pred[mask] - y_true[mask]) / y_true[mask]))


class PyTorchTrainer:
    """Trains a regression nn.Module on a standardized ``log1p(y)`` target.

    Caller contract (see ``_safe_device_with_fallback`` docstring):
        * ``device`` is required and must be the device the model already
          lives on. The trainer moves only batches; it never calls
          ``.to(device)`` on the model.
        * ``generator`` is required; the seeded ``torch.Generator``
          returned by ``set_global_seeds``. Used for ``DataLoader``
          shuffling reproducibility.

    Returns from ``fit``:
        ``(trained_module, history_list, y_log_mean, y_log_std)``.
        The trained module is moved to CPU before return so the caller's
        ``state_dict`` going into ``save_bundle`` is CPU-resident
        regardless of training device.
    """

    def __init__(
        self,
        device: torch.device,
        generator: torch.Generator,
        n_epochs: int = 100,
        batch_size: int = 1024,
        lr: float = 1e-3,
        weight_decay: float = 1e-4,
        patience: int = 15,
        artifact_dir: Path | None = None,
    ) -> None:
        self.device = device
        self.generator = generator
        self.n_epochs = n_epochs
        self.batch_size = batch_size
        self.lr = lr
        self.weight_decay = weight_decay
        self.patience = patience
        self.artifact_dir = artifact_dir
        if artifact_dir is not None:
            artifact_dir.mkdir(parents=True, exist_ok=True)
        self.y_log_mean: float = 0.0
        self.y_log_std: float = 1.0
        # TODO(plan-3): add ``warmup_epochs`` ctor arg + SequentialLR(LinearLR + Cosine)

    def fit(
        self,
        model: nn.Module,
        X_num_train: np.ndarray,
        X_cat_train: np.ndarray | None,
        y_train_log: np.ndarray,
        X_num_val: np.ndarray,
        X_cat_val: np.ndarray | None,
        y_val_log: np.ndarray,
    ) -> tuple[nn.Module, list[dict[str, float]], float, float]:
        # 1. Standardize the log1p target on train; store mean/std on self.
        self.y_log_mean = float(np.mean(y_train_log))
        self.y_log_std = float(np.std(y_train_log) + 1e-8)
        y_train_std = (y_train_log - self.y_log_mean) / self.y_log_std
        y_val_std = (y_val_log - self.y_log_mean) / self.y_log_std

        # 2. Build train/val tensors. Numeric-only path for now — cat
        #    will be wired in by Plan 2 by switching on `X_cat_train is None`.
        x_train_t = torch.from_numpy(np.asarray(X_num_train, dtype=np.float32))
        y_train_t = torch.from_numpy(y_train_std.astype(np.float32))
        x_val_t = torch.from_numpy(np.asarray(X_num_val, dtype=np.float32))
        y_val_t = torch.from_numpy(y_val_std.astype(np.float32))

        # TODO(plan-2): when X_cat_train is not None, build a (x_num, x_cat, y) TensorDataset
        train_ds = TensorDataset(x_train_t, y_train_t)
        train_loader = DataLoader(
            train_ds,
            batch_size=self.batch_size,
            shuffle=True,
            drop_last=False,
            generator=self.generator,
        )

        # 3. Optimizer + cosine LR schedule (no warmup in Plan 1).
        optimizer = torch.optim.AdamW(
            model.parameters(), lr=self.lr, weight_decay=self.weight_decay
        )
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer, T_max=self.n_epochs
        )
        loss_fn = nn.MSELoss()

        # 4. Bookkeeping for early stopping.
        best_val_mape = float("inf")
        best_state: dict[str, torch.Tensor] | None = None
        best_epoch = -1
        epochs_without_improve = 0
        history: list[dict[str, float]] = []

        y_val_real = np.expm1(y_val_log)

        for epoch in range(1, self.n_epochs + 1):
            model.train()
            running_loss = 0.0
            n_seen = 0
            for x_b, y_b in train_loader:
                x_b = x_b.to(self.device, non_blocking=True)
                y_b = y_b.to(self.device, non_blocking=True)
                optimizer.zero_grad()
                pred = model(x_b).squeeze(-1)
                loss = loss_fn(pred, y_b)
                loss.backward()
                optimizer.step()
                running_loss += float(loss.item()) * x_b.size(0)
                n_seen += x_b.size(0)
            train_loss = running_loss / max(n_seen, 1)

            # Val pass: chunked, no shuffle.
            model.eval()
            chunk = self.batch_size * 4
            preds_std: list[np.ndarray] = []
            with torch.no_grad():
                for start in range(0, x_val_t.size(0), chunk):
                    xb = x_val_t[start : start + chunk].to(self.device)
                    out = model(xb).squeeze(-1)
                    preds_std.append(out.detach().cpu().numpy())
            pred_std_arr = np.concatenate(preds_std, axis=0)
            pred_log = pred_std_arr * self.y_log_std + self.y_log_mean
            pred_real = np.clip(np.expm1(pred_log), a_min=1.0, a_max=None)
            val_mape = _mape_real_scale(y_val_real, pred_real)

            current_lr = float(optimizer.param_groups[0]["lr"])
            history.append(
                {
                    "epoch": int(epoch),
                    "train_loss": float(train_loss),
                    "val_mape": float(val_mape),
                    "lr": current_lr,
                }
            )

            improved = val_mape < best_val_mape - 1e-6
            if improved:
                best_val_mape = val_mape
                best_state = {
                    k: v.detach().cpu().clone() for k, v in model.state_dict().items()
                }
                best_epoch = epoch
                epochs_without_improve = 0
            else:
                epochs_without_improve += 1

            scheduler.step()

            if self.artifact_dir is not None and epoch % 10 == 0:
                print(
                    f"  [trainer] epoch={epoch:3d} train_loss={train_loss:.4f} "
                    f"val_mape={val_mape:.4f} lr={current_lr:.2e} "
                    f"best={best_val_mape:.4f}@{best_epoch}"
                )

            if epochs_without_improve >= self.patience:
                print(
                    f"  [trainer] early-stopping at epoch={epoch} "
                    f"(no improvement for {self.patience} epochs); "
                    f"best val_mape={best_val_mape:.4f}@{best_epoch}"
                )
                break

        # Restore the best snapshot, then move to CPU for portable bundling.
        if best_state is not None:
            model.load_state_dict(best_state)
        model.to(torch.device("cpu"))

        if self.artifact_dir is not None:
            (self.artifact_dir / "training_history.json").write_text(
                json.dumps(history, indent=2)
            )

        return model, history, self.y_log_mean, self.y_log_std


# ---------------------------------------------------------------------------
# Class registry + bundle helpers
# ---------------------------------------------------------------------------
MODEL_REGISTRY: dict[str, type[nn.Module]] = {}


def register_model(cls: type[nn.Module]) -> type[nn.Module]:
    """Decorator: register ``cls`` under its class name so ``load_bundle`` can find it."""
    MODEL_REGISTRY[cls.__name__] = cls
    return cls


def save_bundle(
    model: nn.Module,
    model_kwargs: dict[str, Any],
    preprocessor: TabularPreprocessor,
    dropped_cols: list[str],
    kmeans: Any | None,
    knn_builder: Any | None,
    y_log_mean: float,
    y_log_std: float,
    feature_columns: list[str],
    cat_cardinalities: list[int],
    candidate_results: list[dict[str, Any]],
    best_candidate: dict[str, Any],
    history: list[dict[str, float]],
) -> dict[str, Any]:
    """Build the joblib-able bundle dict.

    Critically: stores ``state_dict`` (CPU clones) + ``model_class_name``
    (str) + ``model_kwargs`` (dict) — **not** the live ``nn.Module``
    instance. This keeps the joblib payload device-portable and survives
    the registered class being redefined between train and predict.

    In Plan 1 ``kmeans`` and ``knn_builder`` are always ``None`` and
    ``cat_cardinalities`` is ``[]``; the keys still exist in the schema
    so Plans 2-4 won't have to migrate.
    """
    state_dict_cpu = {
        k: v.detach().cpu().clone() for k, v in model.state_dict().items()
    }
    return {
        "model_class_name": type(model).__name__,
        "model_kwargs": dict(model_kwargs),
        "state_dict": state_dict_cpu,
        "preprocessor": preprocessor,
        "dropped_cols": list(dropped_cols),
        "kmeans": kmeans,
        "knn_builder": knn_builder,
        "y_log_mean": float(y_log_mean),
        "y_log_std": float(y_log_std),
        "feature_columns": list(feature_columns),
        "cat_cardinalities": list(cat_cardinalities),
        "candidate_results": list(candidate_results),
        "best_candidate": dict(best_candidate),
        "history": list(history),
    }


def load_bundle(
    bundle: dict[str, Any], device: torch.device | None = None
) -> nn.Module:
    """Reconstruct ``nn.Module`` from a bundle. Default ``device=CPU`` (always safe).

    See module docstring for the cold-load registry contract — the caller
    must have imported the model module before this call so
    ``MODEL_REGISTRY`` is populated.
    """
    target_device = device if device is not None else torch.device("cpu")
    cls_name = bundle["model_class_name"]
    if cls_name not in MODEL_REGISTRY:
        raise KeyError(
            f"Class {cls_name!r} not in MODEL_REGISTRY. "
            "Did you forget to import the model module before load_bundle? "
            "See _nn_common.py module docstring for the cold-load contract."
        )
    cls = MODEL_REGISTRY[cls_name]
    model = cls(**bundle["model_kwargs"])
    model.load_state_dict(bundle["state_dict"])
    model.eval()
    model.to(target_device)
    return model
