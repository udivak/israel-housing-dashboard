"""מטריקות — המקור היחיד לדירוג. אין להעתיק את הלוגיקה לקבצי מודל."""

from __future__ import annotations

import numpy as np


def compute_metrics(y_true, y_pred) -> dict:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    err = y_pred - y_true
    mae = float(np.mean(np.abs(err)))
    rmse = float(np.sqrt(np.mean(err ** 2)))

    mask = y_true > 0
    mape = float(np.mean(np.abs(err[mask] / y_true[mask]))) if mask.any() else float("nan")

    ss_res = float(np.sum(err ** 2))
    ss_tot = float(np.sum((y_true - np.mean(y_true)) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")

    return {"mae": mae, "rmse": rmse, "mape": mape, "r2": r2, "n": int(len(y_true))}


def compute_segmented(y_true, y_pred, groups) -> dict:
    """מטריקות לפי קבוצה (למשל לפי עיר). groups הוא Series/ndarray באותו אורך."""
    import pandas as pd
    df = pd.DataFrame({"y": y_true, "p": y_pred, "g": groups})
    out = {}
    for key, sub in df.groupby("g"):
        if len(sub) < 20:  # קבוצות קטנות מדי → רעש
            continue
        out[str(key)] = compute_metrics(sub["y"], sub["p"])
    return out
