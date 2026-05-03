"""5-seed CV harness for ``udi/xgboost_v3`` and ``udi/blend_v1``.

Mirrors the moses-side ``cv_validate.py`` but for udi's v2-loader champions.
Stage B.2 of the cv-and-align plan: replaces single-seed leaderboard rows
(0.1985 / 0.1972) with ``mape_mean ± mape_std`` over 5 seeds + a
**paired** noise-band decision (see :mod:`paired diff`).

Flow:
    1. Build the v2 dataset once (~30s of CSV + Mongo cache + OSM).
    2. For every (model, seed) pair: ``data_v2.split(df, seed=seed)`` →
       ``mod.train(..., seed=seed)`` → ``mod.predict(...)`` → metrics.
    3. **Checkpoint** ``artifacts/cv_validate_udi.json`` after every
       (model, seed) so a crash mid-loop preserves partial progress.
    4. Print per-model summary + paired-diff verdict.

Bypasses ``leaderboard.add_result`` on purpose — the harness must not
flood the leaderboard with 10 near-duplicate rows.

Run with::

    python3 scripts/cv_validate_udi.py

Runtime budget: ~3h on CPU (xgboost_v3 ~5min × 5 seeds + blend_v1 ~20min
× 5 seeds; blend re-trains xgboost_v3 + nn_v3 inline). Recommend tmux
or overnight. Re-runs that already have a checkpoint resume from the
last completed (model, seed); pass ``--fresh`` to clobber the checkpoint.
"""
from __future__ import annotations

import argparse
import importlib
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from common.data_v2 import build_dataset, split as data_split  # noqa: E402
from common.evaluate import compute_metrics  # noqa: E402

SEEDS: list[int] = [42, 43, 44, 45, 46]
MODELS: list[str] = ["udi/xgboost_v3", "udi/blend_v1"]

ARTIFACTS = ROOT / "artifacts"
OUT_PATH = ARTIFACTS / "cv_validate_udi.json"


def _load_model_module(submission: str):
    person, name = submission.split("/")
    return importlib.import_module(f"models.{person}.{name}")


def _empty_summary() -> dict[str, Any]:
    return {
        "seeds": list(SEEDS),
        "models": {m: {"runs": []} for m in MODELS},
        "paired_diff": {
            "blend_minus_xgb_mape": [],
            "mean": None,
            "std": None,
        },
    }


def _completed_keys(summary: dict[str, Any]) -> set[tuple[str, int]]:
    """Return the (model, seed) pairs already in the checkpoint."""
    done: set[tuple[str, int]] = set()
    for model_name, payload in summary["models"].items():
        for run in payload.get("runs", []):
            done.add((model_name, int(run["seed"])))
    return done


def _aggregate_per_model(runs: list[dict[str, Any]]) -> dict[str, float]:
    """mean/std/min/max for each metric across the per-seed runs."""
    if not runs:
        return {}
    out: dict[str, float] = {}
    for k in ("mape", "mae", "rmse", "r2"):
        vals = np.array([r[k] for r in runs], dtype=float)
        out[f"{k}_mean"] = float(vals.mean())
        out[f"{k}_std"] = float(vals.std(ddof=0))
        out[f"{k}_min"] = float(vals.min())
        out[f"{k}_max"] = float(vals.max())
    return out


def _aggregate_paired(summary: dict[str, Any]) -> dict[str, Any]:
    """Build per-seed (blend MAPE − xgb MAPE) diff list + mean/std."""
    xgb_runs = {
        int(r["seed"]): r for r in summary["models"]["udi/xgboost_v3"]["runs"]
    }
    blend_runs = {
        int(r["seed"]): r for r in summary["models"]["udi/blend_v1"]["runs"]
    }
    shared = sorted(set(xgb_runs) & set(blend_runs))
    diffs: list[dict[str, float]] = []
    for s in shared:
        diff = float(blend_runs[s]["mape"] - xgb_runs[s]["mape"])
        diffs.append(
            {
                "seed": s,
                "blend_mape": float(blend_runs[s]["mape"]),
                "xgb_mape": float(xgb_runs[s]["mape"]),
                "diff": diff,
            }
        )
    if diffs:
        arr = np.array([d["diff"] for d in diffs], dtype=float)
        return {
            "blend_minus_xgb_mape": diffs,
            "mean": float(arr.mean()),
            "std": float(arr.std(ddof=0)),
        }
    return {"blend_minus_xgb_mape": [], "mean": None, "std": None}


def _write_checkpoint(summary: dict[str, Any]) -> None:
    """Recompute aggregates + paired diff, then atomically write the JSON."""
    for model_name in MODELS:
        runs = summary["models"][model_name].get("runs", [])
        summary["models"][model_name].update(_aggregate_per_model(runs))
    summary["paired_diff"] = _aggregate_paired(summary)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(summary, indent=2))
    tmp.replace(OUT_PATH)


def _load_or_init() -> dict[str, Any]:
    """Resume from ``cv_validate_udi.json`` if present and parseable."""
    if not OUT_PATH.exists():
        return _empty_summary()
    try:
        existing = json.loads(OUT_PATH.read_text())
        # If schema drifted (e.g. SEEDS or MODELS list changed), bail out
        # rather than silently mixing old + new partial results.
        if existing.get("seeds") != SEEDS:
            print(
                f"⚠️ checkpoint SEEDS mismatch ({existing.get('seeds')} vs "
                f"{SEEDS}) → starting fresh."
            )
            return _empty_summary()
        if set(existing.get("models", {})) != set(MODELS):
            print(
                f"⚠️ checkpoint MODELS mismatch → starting fresh."
            )
            return _empty_summary()
        return existing
    except (json.JSONDecodeError, OSError) as e:
        print(f"⚠️ failed to read checkpoint ({e}); starting fresh.")
        return _empty_summary()


def _print_summary(summary: dict[str, Any]) -> None:
    print()
    print("=" * 72)
    print("SUMMARY (per-model, n=5 seeds)")
    print("=" * 72)
    for model_name in MODELS:
        payload = summary["models"][model_name]
        runs = payload.get("runs", [])
        if not runs:
            print(f"\n{model_name}: no runs")
            continue
        print(f"\n{model_name}  (n_runs={len(runs)})")
        print(
            f"  {'seed':>5} {'mape':>8} {'mae':>10} {'rmse':>10} "
            f"{'r2':>7} {'sec':>6} {'n':>6}"
        )
        for r in sorted(runs, key=lambda x: x["seed"]):
            print(
                f"  {r['seed']:>5} {r['mape']:>8.4f} {r['mae']:>10,.0f} "
                f"{r['rmse']:>10,.0f} {r['r2']:>7.3f} "
                f"{r.get('seconds', 0):>6.1f} {r['n']:>6}"
            )
        for k in ("mape", "mae", "rmse", "r2"):
            if f"{k}_mean" in payload:
                fmt = "{:>10,.0f}" if k in ("mae", "rmse") else "{:>10.4f}"
                print(
                    f"    {k:>6}_mean=" + fmt.format(payload[f'{k}_mean'])
                    + "  std=" + fmt.format(payload[f'{k}_std'])
                    + f"  min=" + fmt.format(payload[f'{k}_min'])
                    + f"  max=" + fmt.format(payload[f'{k}_max'])
                )

    paired = summary.get("paired_diff", {})
    diffs = paired.get("blend_minus_xgb_mape", [])
    if diffs:
        print()
        print("=" * 72)
        print("PAIRED DIFF (blend MAPE − xgb MAPE per seed)")
        print("=" * 72)
        print(f"  {'seed':>5} {'blend':>8} {'xgb':>8} {'diff':>9}")
        for d in diffs:
            print(
                f"  {d['seed']:>5} {d['blend_mape']:>8.4f} "
                f"{d['xgb_mape']:>8.4f} {d['diff']:>+9.4f}"
            )
        mean_d = paired["mean"]
        std_d = paired["std"]
        print(f"\n  mean(diff) = {mean_d:+.4f}   std(diff) = {std_d:.4f}")
        if mean_d is not None and std_d is not None:
            # Paired noise-band rule (Stage B.3): blend is honestly better
            # iff |mean(diff)| > std(diff). Sign matters: a *negative*
            # mean(diff) means blend < xgb (lower MAPE), which is the
            # win condition since lower MAPE is better.
            if mean_d < 0 and abs(mean_d) > std_d:
                verdict = (
                    "blend_v1 wins outside the paired noise band → "
                    "keep blend_v1 as udi/* champion."
                )
            elif mean_d >= 0 and mean_d > std_d:
                verdict = (
                    "xgboost_v3 wins outside the paired noise band → "
                    "recommend xgboost_v3 for serving."
                )
            else:
                verdict = (
                    "diff is inside the paired noise band → "
                    "recommend xgboost_v3 for serving (one fewer moving part)."
                )
            print(f"\n  VERDICT: {verdict}")


def run_one(df, model_name: str, seed: int) -> dict[str, Any]:
    print(f"\n──── {model_name}  seed={seed} ────")
    t0 = time.time()
    X_tr, y_tr, X_va, y_va, X_te, y_te = data_split(df, seed=seed)

    mod = _load_model_module(model_name)
    bundle = mod.train(X_tr, y_tr, X_va, y_va, seed=seed)
    y_pred = mod.predict(bundle, X_te)
    m = compute_metrics(y_te, y_pred)
    m["seed"] = int(seed)
    m["seconds"] = round(time.time() - t0, 1)
    print(
        f"  → {model_name} seed={seed}  test mape={m['mape']:.4f} "
        f"mae={m['mae']:,.0f}  r2={m['r2']:.3f}  ({m['seconds']}s)"
    )
    return m


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="ignore existing checkpoint and start over",
    )
    args = parser.parse_args()

    print("=" * 72)
    print(f"5-seed CV — {MODELS}  (seeds={SEEDS})")
    print("=" * 72)

    if args.fresh and OUT_PATH.exists():
        print(f"[--fresh] removing existing checkpoint at {OUT_PATH}")
        OUT_PATH.unlink()

    summary = _load_or_init()
    done = _completed_keys(summary)
    if done:
        print(f"resuming — {len(done)} (model, seed) pairs already complete:")
        for model_name, seed in sorted(done):
            print(f"  ✓ {model_name}  seed={seed}")

    print("\nbuilding v2 dataset (once)...")
    t0 = time.time()
    df = build_dataset()
    print(f"dataset: {len(df):,} rows  ({time.time()-t0:.1f}s)")

    # Outer loop = model, inner = seed → reduces module-import churn and
    # keeps each model's per-seed runs adjacent in console output.
    for model_name in MODELS:
        for seed in SEEDS:
            if (model_name, seed) in done:
                continue
            try:
                m = run_one(df, model_name, seed)
            except Exception as exc:  # noqa: BLE001
                print(f"❌ {model_name} seed={seed} failed: {exc}")
                raise
            summary["models"][model_name]["runs"].append(m)
            _write_checkpoint(summary)
            print(f"  ✓ checkpointed → {OUT_PATH}")

    _print_summary(summary)
    print(f"\n✅ CV complete. Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
