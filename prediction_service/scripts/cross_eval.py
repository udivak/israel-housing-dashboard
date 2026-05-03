"""Cross-loader canonical evaluation: rank moses/* and udi/* on identical rows.

Stage C of the cv-and-align plan. Today's leaderboard scores
``moses/stacked_v1`` (n=5,625, CPI-adjusted) against ``udi/blend_v1``
(n=5,945, **nominal price** because of the ``data_v2.clean()``
``real_price`` fallback bug) on different rows with different targets —
apples to oranges. This script intersects ``df_v1._id`` ∩ ``df_v2._id``,
draws a deterministic canonical test slice (seed=999), trains each model
on its native loader's ``not-canonical`` rows, predicts on the canonical
slice, **CPI-converts udi predictions to real-price scale via the
per-row factor `df_v1.real_price / df_v1.price`**, and scores all
models against the same v1 ``real_price`` ground truth.

Output: ``artifacts/cross_eval.json`` (ranking by ``mape_real``) +
``artifacts/cross_eval_residuals.parquet`` (per-(model, _id) residuals
for dashboard maps).

Run with::

    python3 scripts/cross_eval.py
"""
from __future__ import annotations

import importlib
import json
import sys
import time
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from common import data as data_v1  # noqa: E402
from common import data_v2  # noqa: E402
from common.evaluate import compute_metrics  # noqa: E402

ARTIFACTS = ROOT / "artifacts"
JSON_OUT = ARTIFACTS / "cross_eval.json"
RESIDUALS_OUT = ARTIFACTS / "cross_eval_residuals.parquet"

CANONICAL_SEED = 999
CANONICAL_FRAC = 0.10
CANONICAL_MIN_ROWS = 1000  # bump to 0.20 if 10% < 1000 rows
SHARED_COVERAGE_WARN = 0.80  # warn if intersection < 80% of either set
TRAIN_SPLIT_SEED = 0
VAL_FRAC = 0.20
CPI_DROP_WARN_FRAC = 0.02  # warn if > 2% canonical rows have unusable cpi_factor

MODELS: list[str] = [
    "moses/stacked_v1",
    "udi/xgboost_v3",
    "udi/blend_v1",
]


# ---------------------------------------------------------------------------
# Helpers — kept inside cross_eval.py per Stage C plan (no loader edits)
# ---------------------------------------------------------------------------
def _is_udi(model_name: str) -> bool:
    return model_name.startswith("udi/")


def _load_model_module(submission: str):
    person, name = submission.split("/")
    return importlib.import_module(f"models.{person}.{name}")


def _select_features_fn(model_name: str) -> Callable[[pd.DataFrame], pd.DataFrame]:
    """Return the loader's ``select_features`` for the model's native loader."""
    return data_v2.select_features if _is_udi(model_name) else data_v1.select_features


def _target_col(model_name: str) -> str:
    """udi → ``real_price`` (which is *nominal* per data_v2 bug)
    moses → ``real_price`` (CPI-adjusted)."""
    return data_v2.TARGET if _is_udi(model_name) else data_v1.TARGET


def train_no_test_split(
    df: pd.DataFrame,
    select_features_fn: Callable[[pd.DataFrame], pd.DataFrame],
    target_col: str,
    val_frac: float = VAL_FRAC,
    seed: int = TRAIN_SPLIT_SEED,
) -> tuple[pd.DataFrame, np.ndarray, pd.DataFrame, np.ndarray]:
    """Random permutation 80/20 train/val (no test). Cross-eval is single-shot."""
    rng = np.random.default_rng(seed)
    idx = rng.permutation(len(df))
    n_val = int(val_frac * len(df))
    val_idx = idx[:n_val]
    train_idx = idx[n_val:]

    train_sub = df.iloc[train_idx]
    val_sub = df.iloc[val_idx]
    X_train = select_features_fn(train_sub)
    y_train = train_sub[target_col].values.astype(float)
    X_val = select_features_fn(val_sub)
    y_val = val_sub[target_col].values.astype(float)
    return X_train, y_train, X_val, y_val


def id_aligned_predict_frame(
    df: pd.DataFrame,
    canonical_ids: list[str],
    select_features_fn: Callable[[pd.DataFrame], pd.DataFrame],
) -> tuple[pd.DataFrame, np.ndarray]:
    """Filter ``df`` to ``_id ∈ canonical_ids``, drop ``_id`` via select_features,
    return ``(X, ids_array)`` so caller can align preds back to ``_id``."""
    sub = df[df["_id"].isin(canonical_ids)].copy()
    ids = sub["_id"].astype(str).to_numpy()
    X = select_features_fn(sub)
    return X, ids


# ---------------------------------------------------------------------------
# Datasets + canonical slice
# ---------------------------------------------------------------------------
def _build_loaders() -> tuple[pd.DataFrame, pd.DataFrame]:
    print("=" * 72)
    print("[cross_eval] building both loaders (v1 + v2)...")
    print("=" * 72)

    print("\n--- v1 (moses) ---")
    t0 = time.time()
    df_v1 = data_v1.build_dataset()
    df_v1["_id"] = df_v1["_id"].astype(str)
    print(f"  v1: {len(df_v1):,} rows  ({time.time()-t0:.1f}s)")
    if "real_price" not in df_v1.columns or "price" not in df_v1.columns:
        raise RuntimeError(
            "v1 frame is missing real_price or price — cannot compute CPI factor."
        )

    print("\n--- v2 (udi) ---")
    t0 = time.time()
    df_v2 = data_v2.build_dataset()
    df_v2["_id"] = df_v2["_id"].astype(str)
    print(f"  v2: {len(df_v2):,} rows  ({time.time()-t0:.1f}s)")
    return df_v1, df_v2


def _draw_canonical_ids(df_v1: pd.DataFrame, df_v2: pd.DataFrame) -> list[str]:
    v1_ids = set(df_v1["_id"])
    v2_ids = set(df_v2["_id"])
    shared = sorted(v1_ids & v2_ids)
    cov_v1 = len(shared) / len(v1_ids) if v1_ids else 0.0
    cov_v2 = len(shared) / len(v2_ids) if v2_ids else 0.0

    print()
    print(
        f"  shared _id coverage:  v1={cov_v1:.1%}  v2={cov_v2:.1%}  "
        f"(intersection size = {len(shared):,})"
    )
    if cov_v1 < SHARED_COVERAGE_WARN or cov_v2 < SHARED_COVERAGE_WARN:
        print(
            f"  ⚠️ shared coverage below {SHARED_COVERAGE_WARN:.0%} on at least "
            "one loader — the canonical slice may not represent either loader's "
            "native distribution."
        )

    frac = CANONICAL_FRAC
    n_canonical = int(round(frac * len(shared)))
    if n_canonical < CANONICAL_MIN_ROWS and len(shared) >= CANONICAL_MIN_ROWS:
        frac = 0.20
        n_canonical = int(round(frac * len(shared)))
        print(
            f"  10% slice ({int(0.10 * len(shared)):,}) below floor "
            f"{CANONICAL_MIN_ROWS} → bumping to 20% ({n_canonical:,})"
        )
    elif n_canonical < CANONICAL_MIN_ROWS:
        print(
            f"  ⚠️ shared intersection too small "
            f"({len(shared):,} < {CANONICAL_MIN_ROWS}) — "
            "using all shared ids as canonical (degenerate, no train rows)."
        )
        n_canonical = len(shared)

    rng = np.random.default_rng(CANONICAL_SEED)
    chosen = rng.choice(np.array(shared), size=n_canonical, replace=False)
    canonical_ids = sorted(chosen.tolist())
    print(
        f"  canonical_test slice: {len(canonical_ids):,} rows  "
        f"(seed={CANONICAL_SEED}, frac={frac:.0%})"
    )
    return canonical_ids


def _build_cpi_factor(
    df_v1: pd.DataFrame, canonical_ids: list[str]
) -> tuple[dict[str, float], dict[str, float]]:
    """Per-row CPI deflator from v1's ``real_price / price`` on canonical rows.

    Returns:
        (cpi_factor_by_id, y_real_by_id) — both keyed on _id.

    Drops rows where ``cpi_factor`` is NaN/inf/0 from the scoring set
    (warn loud if > 2% drop, signals an upstream price-quality issue).
    """
    indexed = df_v1.set_index("_id")
    valid_ids = [i for i in canonical_ids if i in indexed.index]
    sub = indexed.loc[valid_ids, ["real_price", "price"]].copy()
    sub["cpi_factor"] = sub["real_price"].astype(float) / sub["price"].astype(float)

    bad = (
        sub["cpi_factor"].isna()
        | np.isinf(sub["cpi_factor"])
        | (sub["price"].astype(float) <= 0)
    )
    n_bad = int(bad.sum())
    n_total = len(sub)
    drop_frac = (n_bad / n_total) if n_total > 0 else 0.0
    if drop_frac > CPI_DROP_WARN_FRAC:
        print(
            f"  ⚠️ dropping {n_bad:,}/{n_total:,} canonical rows with "
            f"unusable cpi_factor ({drop_frac:.1%} > {CPI_DROP_WARN_FRAC:.0%}) — "
            "investigate v1.price quality on these _ids."
        )
    elif n_bad > 0:
        print(
            f"  dropped {n_bad:,}/{n_total:,} canonical rows with "
            f"unusable cpi_factor ({drop_frac:.2%})"
        )

    sub_ok = sub[~bad]
    cpi_factor_by_id = sub_ok["cpi_factor"].astype(float).to_dict()
    y_real_by_id = sub_ok["real_price"].astype(float).to_dict()
    return cpi_factor_by_id, y_real_by_id


def _print_year_distribution(df_v1: pd.DataFrame, canonical_ids: list[str]) -> None:
    """Sanity check — canonical slice may over-represent recent years (Mongo cache bias)."""
    sub = df_v1[df_v1["_id"].isin(canonical_ids)]
    if "transaction_date" not in sub.columns:
        return
    dates = pd.to_datetime(sub["transaction_date"], errors="coerce")
    if dates.notna().any():
        years = dates.dt.year.value_counts().sort_index()
        print("  canonical year distribution:")
        for y, n in years.items():
            print(f"    {int(y)}: {int(n):,}")


# ---------------------------------------------------------------------------
# Main per-model pipeline
# ---------------------------------------------------------------------------
def _train_predict_one_model(
    model_name: str,
    df_v1: pd.DataFrame,
    df_v2: pd.DataFrame,
    canonical_ids: list[str],
) -> dict[str, np.ndarray]:
    """Train on native-non-canonical, predict on native-canonical.

    Returns a dict ``{"_id": ids, "pred_native": pred_native_scale}`` —
    CPI conversion applied later in :func:`_score_against_v1_real`.
    """
    df_native = df_v2 if _is_udi(model_name) else df_v1
    select_fn = _select_features_fn(model_name)
    target_col = _target_col(model_name)

    df_train = df_native[~df_native["_id"].isin(canonical_ids)].copy()
    print(
        f"  [{model_name}] native loader = "
        f"{'v2 (udi)' if _is_udi(model_name) else 'v1 (moses)'}  "
        f"train_rows={len(df_train):,}  canonical_rows="
        f"{int(df_native['_id'].isin(canonical_ids).sum()):,}"
    )

    X_train, y_train, X_val, y_val = train_no_test_split(
        df_train, select_fn, target_col, val_frac=VAL_FRAC, seed=TRAIN_SPLIT_SEED
    )

    print(f"  [{model_name}] training on train={len(X_train):,} val={len(X_val):,}")
    t0 = time.time()
    mod = _load_model_module(model_name)
    bundle = mod.train(X_train, y_train, X_val, y_val)
    print(f"  [{model_name}] trained in {time.time()-t0:.1f}s")

    X_canonical, ids_canonical = id_aligned_predict_frame(
        df_native, canonical_ids, select_fn
    )
    print(f"  [{model_name}] predicting on canonical rows = {len(X_canonical):,}")
    pred_native = mod.predict(bundle, X_canonical)
    return {"_id": ids_canonical, "pred_native": np.asarray(pred_native, dtype=float)}


def _score_against_v1_real(
    model_name: str,
    pred_payload: dict[str, np.ndarray],
    cpi_factor_by_id: dict[str, float],
    y_real_by_id: dict[str, float],
) -> tuple[dict[str, Any], pd.DataFrame]:
    """Compute mape_real (CPI-converted for udi/*, native for moses/*)
    AND mape_unconverted (no CPI conversion, exposes the loader bug).

    Also produces a per-`_id` residual frame for the dashboard.
    """
    rows: list[dict[str, Any]] = []
    for _id, pred_n in zip(pred_payload["_id"], pred_payload["pred_native"]):
        if _id not in y_real_by_id:
            # Dropped due to bad CPI factor — exclude from scoring.
            continue
        cpi = cpi_factor_by_id[_id]
        y_real = y_real_by_id[_id]
        if _is_udi(model_name):
            pred_real = float(pred_n) * cpi
        else:
            pred_real = float(pred_n)
        rows.append(
            {
                "_id": str(_id),
                "model": model_name,
                "y_real": float(y_real),
                "pred_real": float(pred_real),
                "pred_native_scale": float(pred_n),
                "cpi_factor": float(cpi),
                "abs_pct_err": abs(pred_real - y_real) / y_real
                if y_real > 0
                else float("nan"),
            }
        )

    if not rows:
        return {
            "mape_real": float("nan"),
            "mape_unconverted": float("nan"),
            "mae_real": float("nan"),
            "rmse_real": float("nan"),
            "r2_real": float("nan"),
            "n": 0,
        }, pd.DataFrame(rows)

    df_r = pd.DataFrame(rows)
    metrics_real = compute_metrics(df_r["y_real"].values, df_r["pred_real"].values)
    metrics_uncon = compute_metrics(
        df_r["y_real"].values, df_r["pred_native_scale"].values
    )

    out = {
        "mape_real": float(metrics_real["mape"]),
        "mape_unconverted": float(metrics_uncon["mape"]),
        "mae_real": float(metrics_real["mae"]),
        "rmse_real": float(metrics_real["rmse"]),
        "r2_real": float(metrics_real["r2"]),
        "n": int(metrics_real["n"]),
    }
    return out, df_r


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    df_v1, df_v2 = _build_loaders()
    canonical_ids = _draw_canonical_ids(df_v1, df_v2)
    _print_year_distribution(df_v1, canonical_ids)

    print()
    print("=" * 72)
    print("[cross_eval] building per-_id CPI factor from v1 (real_price / price)")
    print("=" * 72)
    cpi_factor_by_id, y_real_by_id = _build_cpi_factor(df_v1, canonical_ids)
    print(
        f"  {len(y_real_by_id):,} canonical rows with usable cpi_factor "
        f"(real_price + price both > 0)"
    )

    coverage = {
        "v1_pct": float(
            len(set(df_v1["_id"]) & set(df_v2["_id"])) / max(len(set(df_v1["_id"])), 1)
        ),
        "v2_pct": float(
            len(set(df_v1["_id"]) & set(df_v2["_id"])) / max(len(set(df_v2["_id"])), 1)
        ),
    }

    results: dict[str, dict[str, Any]] = {}
    residual_frames: list[pd.DataFrame] = []

    for model_name in MODELS:
        print()
        print("=" * 72)
        print(f"[cross_eval] {model_name}")
        print("=" * 72)
        try:
            pred_payload = _train_predict_one_model(
                model_name, df_v1, df_v2, canonical_ids
            )
        except Exception as exc:  # noqa: BLE001
            print(f"❌ {model_name} failed: {exc}")
            results[model_name] = {"error": str(exc)}
            continue

        scored, residuals_df = _score_against_v1_real(
            model_name, pred_payload, cpi_factor_by_id, y_real_by_id
        )
        results[model_name] = scored
        if not residuals_df.empty:
            residual_frames.append(residuals_df)

        print(
            f"  → {model_name}: mape_real={scored['mape_real']:.4f}  "
            f"mape_unconverted={scored['mape_unconverted']:.4f}  "
            f"mae_real={scored['mae_real']:,.0f}  r2_real={scored['r2_real']:.3f}  "
            f"n={scored['n']:,}"
        )

    valid = [(m, p) for m, p in results.items() if "mape_real" in p]
    valid.sort(key=lambda x: x[1]["mape_real"])
    ranking = [m for m, _ in valid]

    summary = {
        "n_canonical": int(len(y_real_by_id)),
        "shared_id_coverage": coverage,
        "canonical_test_seed": int(CANONICAL_SEED),
        "models": results,
        "ranking_by_mape_real": ranking,
    }

    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(summary, indent=2))
    print(f"\n✅ wrote {JSON_OUT}")

    if residual_frames:
        all_residuals = pd.concat(residual_frames, ignore_index=True)
        all_residuals.to_parquet(RESIDUALS_OUT, index=False)
        print(
            f"✅ wrote {RESIDUALS_OUT}  ({len(all_residuals):,} rows × "
            f"{all_residuals.shape[1]} cols)"
        )
    else:
        print("⚠️ no residuals to dump (all models failed?)")

    print()
    print("=" * 72)
    print("RANKING (by mape_real on identical canonical rows)")
    print("=" * 72)
    print(
        f"{'rank':>4}  {'model':<25} {'mape_real':>10} {'mape_uncon':>11} "
        f"{'mae_real':>11} {'r2':>7} {'n':>6}"
    )
    for rank, (model_name, payload) in enumerate(valid, start=1):
        print(
            f"{rank:>4}  {model_name:<25} {payload['mape_real']:>10.4f} "
            f"{payload['mape_unconverted']:>11.4f} "
            f"{payload['mae_real']:>11,.0f} {payload['r2_real']:>7.3f} "
            f"{payload['n']:>6,}"
        )


if __name__ == "__main__":
    main()
