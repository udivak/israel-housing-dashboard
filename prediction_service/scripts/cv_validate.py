"""
5-seed CV — מאמת שה-MAPE של stacked_v1 יציב בין seeds שונים.

זרימה:
    1. טוען דאטה פעם אחת (yקר — 38 שניות).
    2. לכל seed: split אחר → אימון מלא של stacked_v1 → metrics על test.
    3. מדפיס mean ± std של כל מטריקה.

ריצה: python3 scripts/cv_validate.py
"""
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import lightgbm as lgb
from catboost import CatBoostRegressor

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from common.data import build_dataset, split as data_split
from common.evaluate import compute_metrics

SEEDS = [42, 43, 44, 45, 46]
CAT_FEATURES = ["city", "deal_nature"]


def _prep_for_catboost(X: pd.DataFrame) -> pd.DataFrame:
    X = X.copy()
    for c in CAT_FEATURES:
        if c in X.columns:
            X[c] = X[c].astype(str).fillna("NA")
    return X


def run_one(df: pd.DataFrame, seed: int) -> dict:
    print(f"\n──── seed={seed} ────")
    t0 = time.time()
    X_train, y_train, X_val, y_val, X_test, y_test = data_split(df, seed=seed)
    yt = np.log1p(y_train)
    yv = np.log1p(y_val)

    print("  training LightGBM...")
    lgbm = lgb.LGBMRegressor(
        n_estimators=10000, learning_rate=0.01, num_leaves=511,
        min_child_samples=5, subsample=0.8, colsample_bytree=0.8,
        reg_alpha=0.01, reg_lambda=0.01,
        random_state=seed, n_jobs=-1, verbose=-1,
    )
    lgbm.fit(X_train, yt, eval_set=[(X_val, yv)],
             eval_metric="mape",
             callbacks=[lgb.early_stopping(150, verbose=False)])

    print("  training CatBoost...")
    X_train_cb = _prep_for_catboost(X_train)
    X_val_cb = _prep_for_catboost(X_val)
    cat = [c for c in CAT_FEATURES if c in X_train_cb.columns]
    cb = CatBoostRegressor(
        iterations=5000, depth=10, learning_rate=0.02,
        loss_function="RMSE", cat_features=cat,
        random_seed=seed, od_type="Iter", od_wait=150, verbose=False,
    )
    cb.fit(X_train_cb, yt, eval_set=(X_val_cb, yv), use_best_model=True)

    p_lgb_val = np.expm1(lgbm.predict(X_val))
    p_cat_val = np.expm1(cb.predict(X_val_cb))
    best_w, best_mape = None, np.inf
    for w in np.linspace(0, 1, 21):
        blend = w * p_lgb_val + (1 - w) * p_cat_val
        mape = np.mean(np.abs(blend - y_val) / y_val)
        if mape < best_mape:
            best_mape = mape
            best_w = w
    print(f"  best w_lgb={best_w:.2f} (val_mape={best_mape:.4f})")

    p_lgb_test = np.expm1(lgbm.predict(X_test))
    p_cat_test = np.expm1(cb.predict(_prep_for_catboost(X_test)))
    y_pred = best_w * p_lgb_test + (1 - best_w) * p_cat_test

    m = compute_metrics(y_test, y_pred)
    m["seed"] = seed
    m["w_lgb"] = best_w
    m["seconds"] = round(time.time() - t0, 1)
    print(f"  test mape={m['mape']:.4f}  mae={m['mae']:,.0f}  r2={m['r2']:.3f}  ({m['seconds']}s)")
    return m


def main():
    print("=" * 60)
    print("5-seed CV on stacked_v1")
    print("=" * 60)

    df = build_dataset()
    print(f"\ndataset: {len(df):,} rows")

    results = []
    for seed in SEEDS:
        results.append(run_one(df, seed))

    print("\n" + "=" * 60)
    print("SUMMARY (n=5 seeds)")
    print("=" * 60)
    print(f"\n{'seed':>5} {'mape':>8} {'mae':>10} {'rmse':>10} {'r2':>7} {'w_lgb':>6}")
    print("-" * 55)
    for r in results:
        print(f"{r['seed']:>5} {r['mape']:>8.4f} {r['mae']:>10,.0f} {r['rmse']:>10,.0f} "
              f"{r['r2']:>7.3f} {r['w_lgb']:>6.2f}")

    metrics = ["mape", "mae", "rmse", "r2"]
    print(f"\n{'metric':>8} {'mean':>12} {'std':>10} {'min':>12} {'max':>12}")
    print("-" * 60)
    for k in metrics:
        vals = np.array([r[k] for r in results])
        print(f"{k:>8} {vals.mean():>12.4f} {vals.std():>10.4f} "
              f"{vals.min():>12.4f} {vals.max():>12.4f}")

    # שמירה לקובץ
    out = ROOT / "artifacts" / "cv_validate.json"
    out.parent.mkdir(exist_ok=True)
    import json
    summary = {
        "seeds": SEEDS,
        "runs": results,
        "mape_mean": float(np.mean([r["mape"] for r in results])),
        "mape_std": float(np.std([r["mape"] for r in results])),
        "mae_mean": float(np.mean([r["mae"] for r in results])),
        "r2_mean": float(np.mean([r["r2"] for r in results])),
    }
    out.write_text(json.dumps(summary, indent=2))
    print(f"\n✅ saved to {out}")


if __name__ == "__main__":
    main()
