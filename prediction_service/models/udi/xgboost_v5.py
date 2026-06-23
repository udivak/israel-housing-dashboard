"""XGBoost v5 — Optuna sweep + 5-fold CV. נבנה על v3 (לא v4, כי v4 רגרס).

Pipeline:
    1. אותו pipeline פיצ'רים של v3: native categorical, KMeans-64 geo_cluster,
       engineered scalars (area_per_room/log_area_sqm/floor_ratio/age_x_area),
       GeoKNN OOF + KnnFeatureBuilder. אין TargetEncoding.
    2. Optuna 60 trials, TPESampler(seed=42), MedianPruner על fold-level.
    3. כל trial = 5-fold CV על train+val (90% מהדאטה). KMeans/KNN/cat-alignment
       נבנים *בתוך* כל fold כדי שלא תהיה דליפה.
    4. Final fit: best params על full train+val, n_estimators = median של
       best_iter על 5 folds של ה-trial הזוכה. Test 10% נשאר נפרד → השוואה
       הוגנת ל-leaderboard.

כדי להפעיל:
    python run.py udi/xgboost_v5 --data v2

הערה: ה-budget הוא ~30-60 דק על מכונה רגילה. timeout=3600.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans  # pyright: ignore[reportMissingImports]
from sklearn.model_selection import KFold  # pyright: ignore[reportMissingImports]
from sklearn.neighbors import BallTree  # pyright: ignore[reportMissingImports]
from xgboost import XGBRegressor  # pyright: ignore[reportMissingImports]
from xgboost.callback import EarlyStopping  # pyright: ignore[reportMissingImports]

RANDOM_STATE = 42

ARTIFACTS_DIR = (
    Path(__file__).resolve().parents[2] / "artifacts" / "udi" / "xgboost_v5"
)

CAT_COLS: tuple[str, ...] = ("city", "neighborhood", "deal_nature")

DEAD_COLS: tuple[str, ...] = (
    "is_old",
    "is_new",
    "is_new_project",
    "real_price_imputed",
)

N_CLUSTERS = 64
K_NEAR = 5
K_MID = 10
N_KNN_FOLDS = 5
EARTH_RADIUS_M = 6_371_000.0

# Optuna budget — ~30-60 min על מכונה רגילה.
N_TRIALS = 60
N_CV_FOLDS = 5
OPTUNA_TIMEOUT_S = 3600
EARLY_STOPPING_ROUNDS = 150
N_ESTIMATORS_TUNE = 5000

COMMON_TUNE: dict[str, Any] = {
    "n_estimators": N_ESTIMATORS_TUNE,
    "tree_method": "hist",
    "enable_categorical": True,
    "n_jobs": -1,
    "random_state": RANDOM_STATE,
    "objective": "reg:squarederror",
}


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------
def _mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    mask = y_true > 0
    return float(np.mean(np.abs(y_pred[mask] - y_true[mask]) / y_true[mask]))


def mape_real_scale(y_true_log: np.ndarray, y_pred_log: np.ndarray) -> float:
    y_true = np.expm1(y_true_log)
    y_pred = np.maximum(np.expm1(y_pred_log), 1.0)
    mask = y_true > 0
    if not mask.any():
        return float("nan")
    return float(np.mean(np.abs(y_pred[mask] - y_true[mask]) / y_true[mask]))


# ---------------------------------------------------------------------------
# Categorical alignment (per-fold)
# ---------------------------------------------------------------------------
def _align_categories(
    X_train: pd.DataFrame, X_val: pd.DataFrame, X_test: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, pd.Index]]:
    X_train = X_train.copy()
    X_val = X_val.copy()
    X_test = X_test.copy()

    cat_categories: dict[str, pd.Index] = {}
    for c in CAT_COLS:
        if c not in X_train.columns:
            continue
        cats = X_train[c].astype("category").cat.categories
        cat_categories[c] = cats
        X_train[c] = pd.Categorical(X_train[c], categories=cats)
        if c in X_val.columns:
            X_val[c] = pd.Categorical(X_val[c], categories=cats)
        if c in X_test.columns:
            X_test[c] = pd.Categorical(X_test[c], categories=cats)
    return X_train, X_val, X_test, cat_categories


# ---------------------------------------------------------------------------
# Engineered + KMeans
# ---------------------------------------------------------------------------
def _add_engineered(X: pd.DataFrame, kmeans: KMeans | None) -> pd.DataFrame:
    X = X.copy()

    if "area_sqm" in X.columns and "rooms" in X.columns:
        rooms = X["rooms"].astype(float)
        X["area_per_room"] = np.where(
            rooms > 0, X["area_sqm"].astype(float) / rooms.replace(0, np.nan), np.nan
        )

    if "area_sqm" in X.columns:
        X["log_area_sqm"] = np.log1p(X["area_sqm"].astype(float))

    if "floor" in X.columns and "building_floors" in X.columns:
        bf = X["building_floors"].astype(float)
        X["floor_ratio"] = np.where(
            bf > 0, X["floor"].astype(float) / bf.replace(0, np.nan), np.nan
        )

    if "property_age" in X.columns and "area_sqm" in X.columns:
        X["age_x_area"] = X["property_age"].astype(float) * X["area_sqm"].astype(float)

    if kmeans is not None and "lat" in X.columns and "lon" in X.columns:
        coords = X[["lat", "lon"]].astype(float).values
        valid = ~np.isnan(coords).any(axis=1)
        labels = np.full(len(X), -1, dtype=int)
        if valid.any():
            labels[valid] = kmeans.predict(coords[valid])
        X["geo_cluster"] = pd.Categorical(
            labels, categories=list(range(-1, N_CLUSTERS))
        )

    return X


def _fit_kmeans(X_train: pd.DataFrame) -> KMeans | None:
    if "lat" not in X_train.columns or "lon" not in X_train.columns:
        return None
    coords = X_train[["lat", "lon"]].astype(float).values
    valid = ~np.isnan(coords).any(axis=1)
    if valid.sum() < N_CLUSTERS:
        return None
    km = KMeans(n_clusters=N_CLUSTERS, n_init="auto", random_state=RANDOM_STATE)
    km.fit(coords[valid])
    return km


# ---------------------------------------------------------------------------
# GeoKNN
# ---------------------------------------------------------------------------
def _has_coords(X: pd.DataFrame) -> np.ndarray:
    if "lat" not in X.columns or "lon" not in X.columns:
        return np.zeros(len(X), dtype=bool)
    return (X["lat"].notna() & X["lon"].notna()).values


def _compute_pps(price: np.ndarray, area: np.ndarray) -> np.ndarray:
    pps = np.full_like(price, np.nan, dtype=float)
    valid = (area > 0) & ~np.isnan(area) & ~np.isnan(price)
    pps[valid] = price[valid] / area[valid]
    return pps


def _build_tree(lat: np.ndarray, lon: np.ndarray) -> BallTree:
    coords = np.column_stack([np.radians(lat), np.radians(lon)])
    return BallTree(coords, metric="haversine")


def _query_features(
    tree: BallTree,
    ref_pps: np.ndarray,
    ref_price: np.ndarray,
    lat_q: np.ndarray,
    lon_q: np.ndarray,
    skip_self: bool = False,
) -> dict[str, np.ndarray]:
    coords_q = np.column_stack([np.radians(lat_q), np.radians(lon_q)])
    k_max = max(K_NEAR, K_MID) + (1 if skip_self else 0)
    dist_rad, idx = tree.query(coords_q, k=k_max)
    dist_m = dist_rad * EARTH_RADIUS_M

    if skip_self:
        idx = idx[:, 1:]
        dist_m = dist_m[:, 1:]

    pps_near = ref_pps[idx[:, :K_NEAR]]
    knn5_mean_pps = np.nanmean(pps_near, axis=1)

    pps_mid = ref_pps[idx[:, :K_MID]]
    knn10_median_pps = np.nanmedian(pps_mid, axis=1)

    price_near = ref_price[idx[:, :K_NEAR]]
    weights = 1.0 / (dist_m[:, :K_NEAR] + 1.0)
    weights = weights / weights.sum(axis=1, keepdims=True)
    knn5_dw_price = np.nansum(price_near * weights, axis=1)

    return {
        "knn5_mean_price_per_sqm": knn5_mean_pps,
        "knn10_median_price_per_sqm": knn10_median_pps,
        "knn5_dist_weighted_price": knn5_dw_price,
    }


def _empty_knn_features(n: int) -> dict[str, np.ndarray]:
    return {
        "knn5_mean_price_per_sqm": np.full(n, np.nan),
        "knn10_median_price_per_sqm": np.full(n, np.nan),
        "knn5_dist_weighted_price": np.full(n, np.nan),
    }


def _oof_train_knn(X: pd.DataFrame, y: np.ndarray) -> pd.DataFrame:
    n = len(X)
    feats = _empty_knn_features(n)
    has = _has_coords(X)
    if has.sum() == 0:
        return pd.DataFrame(feats, index=X.index)

    lat = X["lat"].values
    lon = X["lon"].values
    area = X["area_sqm"].values
    pps_full = _compute_pps(y.astype(float), area.astype(float))
    y_float = y.astype(float)

    has_idx = np.where(has)[0]
    kf = KFold(n_splits=N_KNN_FOLDS, shuffle=True, random_state=RANDOM_STATE)
    for ref_local, qry_local in kf.split(has_idx):
        ref_idx = has_idx[ref_local]
        qry_idx = has_idx[qry_local]
        tree = _build_tree(lat[ref_idx], lon[ref_idx])
        out = _query_features(
            tree,
            pps_full[ref_idx],
            y_float[ref_idx],
            lat[qry_idx],
            lon[qry_idx],
            skip_self=False,
        )
        for k, v in out.items():
            feats[k][qry_idx] = v

    return pd.DataFrame(feats, index=X.index)


class KnnFeatureBuilder:
    def __init__(self) -> None:
        self.tree: BallTree | None = None
        self.ref_pps: np.ndarray | None = None
        self.ref_price: np.ndarray | None = None

    def fit(self, X_train: pd.DataFrame, y_train: np.ndarray) -> None:
        has = _has_coords(X_train)
        if has.sum() == 0:
            return
        lat = X_train["lat"].values[has]
        lon = X_train["lon"].values[has]
        area = X_train["area_sqm"].values[has].astype(float)
        price = y_train[has].astype(float)
        self.tree = _build_tree(lat, lon)
        self.ref_pps = _compute_pps(price, area)
        self.ref_price = price

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        n = len(X)
        feats = _empty_knn_features(n)
        if self.tree is None:
            return pd.DataFrame(feats, index=X.index)
        has = _has_coords(X)
        if has.sum() == 0:
            return pd.DataFrame(feats, index=X.index)
        lat = X["lat"].values
        lon = X["lon"].values
        out = _query_features(
            self.tree,
            self.ref_pps,
            self.ref_price,
            lat[has],
            lon[has],
            skip_self=False,
        )
        for k, v in out.items():
            feats[k][np.where(has)[0]] = v
        return pd.DataFrame(feats, index=X.index)


def _drop_dead(X: pd.DataFrame, dropped_cols: list[str]) -> pd.DataFrame:
    return X.drop(columns=[c for c in dropped_cols if c in X.columns])


# ---------------------------------------------------------------------------
# Per-fold pipeline build — חייב לרוץ בתוך CV loop כדי שלא תהיה דליפה
# ---------------------------------------------------------------------------
def _build_fold_features(
    X_tr_raw: pd.DataFrame,
    y_tr: np.ndarray,
    X_va_raw: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """
    מקבל train/val raw של ה-fold הנוכחי. מחזיר train/val עם כל הפיצ'רים
    (cat-aligned, engineered, KNN-OOF for train + KNN-fit-on-train for val,
    dropped DEAD_COLS). KMeans/KNN-builder נבנים רק על train של ה-fold.
    """
    X_tr, X_va, _, _ = _align_categories(X_tr_raw, X_va_raw, X_va_raw.iloc[:0])

    kmeans = _fit_kmeans(X_tr)
    X_tr = _add_engineered(X_tr, kmeans)
    X_va = _add_engineered(X_va, kmeans)

    train_knn = _oof_train_knn(X_tr, y_tr)
    knn_builder = KnnFeatureBuilder()
    knn_builder.fit(X_tr, y_tr)
    val_knn = knn_builder.transform(X_va)

    X_tr = pd.concat([X_tr, train_knn], axis=1)
    X_va = pd.concat([X_va, val_knn], axis=1)

    dropped_cols = [c for c in DEAD_COLS if c in X_tr.columns]
    X_tr = _drop_dead(X_tr, dropped_cols)
    X_va = _drop_dead(X_va, dropped_cols)
    return X_tr, X_va, dropped_cols


# ---------------------------------------------------------------------------
# Optuna objective
# ---------------------------------------------------------------------------
def _make_objective(X_combined: pd.DataFrame, y_combined: np.ndarray):
    """Closure שמחזיק את הדאטה — נמסר ל-study.optimize."""

    def objective(trial: optuna.trial.Trial) -> float:
        params = {
            "max_depth": trial.suggest_int("max_depth", 6, 12),
            "learning_rate": trial.suggest_float(
                "learning_rate", 0.01, 0.07, log=True
            ),
            "min_child_weight": trial.suggest_int("min_child_weight", 1, 15),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
            "reg_lambda": trial.suggest_float("reg_lambda", 0.1, 10.0, log=True),
            "reg_alpha": trial.suggest_float("reg_alpha", 0.001, 1.0, log=True),
            "gamma": trial.suggest_float("gamma", 0.001, 1.0, log=True),
        }

        kf = KFold(n_splits=N_CV_FOLDS, shuffle=True, random_state=RANDOM_STATE)
        fold_mapes: list[float] = []
        fold_iters: list[int] = []
        running_sum = 0.0
        n_done = 0

        for fold_idx, (tr_idx, va_idx) in enumerate(kf.split(X_combined)):
            X_tr_raw = X_combined.iloc[tr_idx]
            X_va_raw = X_combined.iloc[va_idx]
            y_tr = y_combined[tr_idx]
            y_va = y_combined[va_idx]

            X_tr, X_va, _ = _build_fold_features(X_tr_raw, y_tr, X_va_raw)

            booster = XGBRegressor(
                **COMMON_TUNE,
                eval_metric=mape_real_scale,
                callbacks=[
                    EarlyStopping(rounds=EARLY_STOPPING_ROUNDS, maximize=False)
                ],
                **params,
            )
            booster.fit(
                X_tr,
                np.log1p(y_tr),
                eval_set=[(X_va, np.log1p(y_va))],
                verbose=False,
            )

            val_pred = np.maximum(np.expm1(booster.predict(X_va)), 1.0)
            mape = _mape(y_va, val_pred)
            fold_mapes.append(mape)
            fold_iters.append(
                int(getattr(booster, "best_iteration", booster.n_estimators))
            )
            running_sum += mape
            n_done += 1

            # ---- pruning ברמת fold (פשוט יותר מ-XGBoostPruningCallback ב-CV).
            trial.report(running_sum / n_done, step=fold_idx)
            if trial.should_prune():
                # שומרים user_attr כדי שנוכל להציץ אחר-כך אם רוצים.
                trial.set_user_attr("fold_mapes", fold_mapes)
                trial.set_user_attr("fold_iters", fold_iters)
                raise optuna.TrialPruned()

        trial.set_user_attr("fold_mapes", fold_mapes)
        trial.set_user_attr("fold_iters", fold_iters)
        return float(np.mean(fold_mapes))

    return objective


# ---------------------------------------------------------------------------
# Train (entry-point ל-runner)
# ---------------------------------------------------------------------------
def train(
    X_train: pd.DataFrame,
    y_train: np.ndarray,
    X_val: pd.DataFrame,
    y_val: np.ndarray,
) -> dict[str, Any]:
    """Optuna sweep על train+val (90%), ואז refit על אותם 90%; test 10%
    נשאר נפרד וה-runner קורא ל-predict עליו אחרי שהפונקציה מסתיימת.
    """
    import optuna  # training-only dep; kept out of module scope so serve-time import works

    # 1. מאחדים train+val ל-objective (val כבר 10% מתוך 90% של המסד).
    X_combined = pd.concat([X_train, X_val], axis=0).reset_index(drop=True)
    y_combined = np.concatenate([y_train, y_val]).astype(float)
    print(
        f"  [xgboost_v5] Optuna sweep on train+val (n={len(X_combined):,})  "
        f"with {N_TRIALS} trials × {N_CV_FOLDS}-fold CV (timeout={OPTUNA_TIMEOUT_S}s)"
    )

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    sampler = optuna.samplers.TPESampler(seed=RANDOM_STATE)
    pruner = optuna.pruners.MedianPruner(n_startup_trials=10, n_warmup_steps=2)
    study = optuna.create_study(direction="minimize", sampler=sampler, pruner=pruner)

    t0 = time.time()
    study.optimize(
        _make_objective(X_combined, y_combined),
        n_trials=N_TRIALS,
        timeout=OPTUNA_TIMEOUT_S,
        show_progress_bar=False,
    )
    elapsed = time.time() - t0
    n_complete = sum(
        1 for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE
    )
    n_pruned = sum(
        1 for t in study.trials if t.state == optuna.trial.TrialState.PRUNED
    )
    print(
        f"  [xgboost_v5] Optuna done in {elapsed/60:.1f}min  "
        f"(complete={n_complete}, pruned={n_pruned})"
    )
    print(
        f"  [xgboost_v5] best CV MAPE={study.best_value:.4f}  "
        f"params={study.best_params}"
    )

    # 2. פיצ'רים סופיים: KMeans/KNN על full train+val (זה מה שגם test יקבל).
    X_all_a, _, _, cat_categories = _align_categories(
        X_combined, X_combined.iloc[:0], X_combined.iloc[:0]
    )
    kmeans = _fit_kmeans(X_all_a)
    X_all_a = _add_engineered(X_all_a, kmeans)

    knn_builder = KnnFeatureBuilder()
    knn_builder.fit(X_all_a, y_combined)
    # ל-train הסופי ה-OOF KNN של full train+val הוא הקיבולת הכי קרובה ל-
    # מה שיקרה ב-inference (עם BallTree של full-train) — נסכים על OOF כדי
    # שלא תהיה דליפה.
    train_knn = _oof_train_knn(X_all_a, y_combined)
    X_all_a = pd.concat([X_all_a, train_knn], axis=1)

    dropped_cols = [c for c in DEAD_COLS if c in X_all_a.columns]
    X_all_a = _drop_dead(X_all_a, dropped_cols)

    # 3. n_estimators סופי = median של best_iter על folds של ה-trial הזוכה.
    best_trial = study.best_trial
    best_iters = best_trial.user_attrs.get("fold_iters") or []
    if best_iters:
        n_estimators_final = max(int(np.median(best_iters)), 100)
    else:
        n_estimators_final = 1000
    print(
        f"  [xgboost_v5] final fit on {len(X_all_a):,} rows × "
        f"{X_all_a.shape[1]} feats with n_estimators={n_estimators_final}"
    )

    final_params = dict(study.best_params)
    final_booster = XGBRegressor(
        n_estimators=n_estimators_final,
        tree_method="hist",
        enable_categorical=True,
        n_jobs=-1,
        random_state=RANDOM_STATE,
        objective="reg:squarederror",
        **final_params,
    )
    # אין eval_set/early_stopping ב-final fit — הסטופ-פוינט נקבע מ-CV.
    final_booster.fit(X_all_a, np.log1p(y_combined), verbose=False)

    feature_names = list(X_all_a.columns)
    importances_df = (
        pd.DataFrame(
            {"column": feature_names, "importance": final_booster.feature_importances_}
        )
        .sort_values("importance", ascending=False)
        .reset_index(drop=True)
    )

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    importances_df.to_csv(ARTIFACTS_DIR / "feature_importances.csv", index=False)

    # שמירה: ה-best_trial + 10 הראשונים לפי MAPE (להקל על forensics).
    sorted_trials = sorted(
        (t for t in study.trials if t.value is not None),
        key=lambda t: t.value,  # type: ignore[return-value]
    )
    trials_summary = [
        {
            "number": t.number,
            "state": str(t.state),
            "value": t.value,
            "params": t.params,
            "fold_mapes": t.user_attrs.get("fold_mapes"),
            "fold_iters": t.user_attrs.get("fold_iters"),
        }
        for t in sorted_trials[:10]
    ]
    (ARTIFACTS_DIR / "optuna_top_trials.json").write_text(
        json.dumps(
            {
                "n_trials_total": len(study.trials),
                "n_complete": n_complete,
                "n_pruned": n_pruned,
                "elapsed_minutes": elapsed / 60,
                "best_value": study.best_value,
                "best_params": study.best_params,
                "n_estimators_final": n_estimators_final,
                "best_iters_per_fold": best_iters,
                "top10": trials_summary,
            },
            indent=2,
        )
    )

    return {
        "model": final_booster,
        "dropped_cols": dropped_cols,
        "cat_categories": cat_categories,
        "kmeans": kmeans,
        "knn_builder": knn_builder,
        "best_params": study.best_params,
        "n_estimators_final": n_estimators_final,
        "cv_mape": study.best_value,
    }


def predict(model: dict[str, Any], X: pd.DataFrame) -> np.ndarray:
    X = X.copy()
    for c, cats in model["cat_categories"].items():
        if c in X.columns:
            X[c] = pd.Categorical(X[c], categories=cats)

    X = _add_engineered(X, model.get("kmeans"))
    knn = model["knn_builder"].transform(X)
    X = pd.concat([X, knn], axis=1)
    X = X.drop(columns=[c for c in model["dropped_cols"] if c in X.columns])
    return np.maximum(np.expm1(model["model"].predict(X)), 1.0)
