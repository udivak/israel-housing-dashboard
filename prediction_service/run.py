"""
הריצה הרשמית של submission.

    python run.py moses/lightgbm_v1

מה זה עושה:
    1. טוען דאטה דרך common.data.load_data()
    2. מייבא את המודל הנבחר (הקובץ models/{person}/{name}.py)
    3. קורא ל-train(X_train, y_train, X_val, y_val) → model
    4. predict(model, X_test) → y_pred
    5. מחשב metrics דרך common.evaluate
    6. שומר artifact + מעדכן leaderboard
"""

from __future__ import annotations

import argparse
import importlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib

from common import evaluate as eval_mod
from common import leaderboard

ROOT = Path(__file__).resolve().parent
ARTIFACTS = ROOT / "artifacts"


def _git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        return "unknown"


def run(submission: str, seed: int = 42, data_version: str = "v1") -> None:
    # submission = "moses/lightgbm_v1"
    person, model_name = submission.split("/")
    module_path = f"models.{person}.{model_name}"

    data_module_name = "common.data_v2" if data_version == "v2" else "common.data"
    print(f"▶ Loading data ({data_module_name})...")
    data_mod = importlib.import_module(data_module_name)
    X_train, y_train, X_val, y_val, X_test, y_test = data_mod.load_data()
    print(f"   train={len(X_train):,}   val={len(X_val):,}   test={len(X_test):,}")

    print(f"▶ Importing {module_path}...")
    mod = importlib.import_module(module_path)

    print(f"▶ Training...")
    model = mod.train(X_train, y_train, X_val, y_val)

    print(f"▶ Predicting on test...")
    y_pred = mod.predict(model, X_test)

    print(f"▶ Evaluating...")
    metrics = eval_mod.compute_metrics(y_test, y_pred)
    print(json.dumps(metrics, indent=2))

    # ניהול artifacts
    out_dir = ARTIFACTS / person / model_name
    out_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, out_dir / "model.joblib")
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2))

    metadata = {
        "submission": submission,
        "seed": seed,
        "data_version": data_version,
        "git_sha": _git_sha(),
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "n_train": len(X_train),
        "n_val": len(X_val),
        "n_test": len(X_test),
        "n_features": X_train.shape[1],
    }
    (out_dir / "run_metadata.json").write_text(json.dumps(metadata, indent=2))

    leaderboard.add_result(submission, metrics, metadata)
    print(f"✅ Saved to {out_dir}")
    print(f"✅ Updated leaderboard.json + leaderboard.md")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("submission", help="e.g. moses/lightgbm_v1")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--data",
        choices=["v1", "v2"],
        default="v1",
        help="גרסת ה-loader (v1 = data.py הקיים; v2 = data_v2.py עם 3 שכבות).",
    )
    args = parser.parse_args()

    sys.path.insert(0, str(ROOT))
    run(args.submission, seed=args.seed, data_version=args.data)
