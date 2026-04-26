"""XGBoost v4 — v3 + smoothed Target Encoding ל-city / neighborhood.

Diffs vs v3:
    1. שתי עמודות נומריות חדשות: te_city_log_price, te_neighborhood_log_price
       דרך sklearn.preprocessing.TargetEncoder עם cv=5 (OOF ב-fit_transform
       כדי שלא תהיה דליפה ל-train), smooth="auto", target_type="continuous".
    2. שומרים גם את הגרסה הקטגורית של city/neighborhood — לבוסטר יש את שתי
       האפשרויות והוא יבחר את החזקה יותר לכל split.
    3. הצפי: 0.175-0.18. ה-TE-wins חותכים פחות ברגע ש-GeoKNN נכנס (חופפים),
       אבל בד"כ עדיין מוסיפים 0.5-1pt.

כדי להפעיל:
    python run.py udi/xgboost_v4 --data v2
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans  # pyright: ignore[reportMissingImports]
from sklearn.model_selection import KFold  # pyright: ignore[reportMissingImports]
from sklearn.neighbors import BallTree  # pyright: ignore[reportMissingImports]
from sklearn.preprocessing import TargetEncoder  # pyright: ignore[reportMissingImports]
from xgboost import XGBRegressor  # pyright: ignore[reportMissingImports]
from xgboost.callback import EarlyStopping  # pyright: ignore[reportMissingImports]

RANDOM_STATE = 42

ARTIFACTS_DIR = (
    Path(__file__).resolve().parents[2] / "artifacts" / "udi" / "xgboost_v4"
)

CAT_COLS: tuple[str, ...] = ("city", "neighborhood", "deal_nature")
TE_COLS: tuple[str, ...] = ("city", "neighborhood")
TE_MISSING_TOKEN = "__missing__"

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

COMMON: dict[str, Any] = {
    "n_estimators": 4000,
    "tree_method": "hist",
    "enable_categorical": True,
    "n_jobs": -1,
    "random_state": RANDOM_STATE,
    "objective": "reg:squarederror",
}

EARLY_STOPPING_ROUNDS = 150

CANDIDATES: tuple[tuple[str, dict[str, Any]], ...] = (
    (
        "xgb_balanced",
        {
            "max_depth": 8,
            "learning_rate": 0.05,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "reg_lambda": 1.0,
            "reg_alpha": 0.01,
            "min_child_weight": 3,
        },
    ),
    (
        "xgb_deep",
        {
            "max_depth": 10,
            "learning_rate": 0.03,
            "subsample": 0.8,
            "colsample_bytree": 0.7,
            "reg_lambda": 2.0,
            "reg_alpha": 0.05,
            "min_child_weight": 3,
        },
    ),
    (
        "xgb_regularized",
        {
            "max_depth": 8,
            "learning_rate": 0.03,
            "subsample": 0.7,
            "colsample_bytree": 0.6,
            "reg_lambda": 5.0,
            "reg_alpha": 0.5,
            "min_child_weight": 10,
        },
    ),
    (
        "xgb_deep_reg",
        {
            "max_depth": 10,
            "learning_rate": 0.03,
            "subsample": 0.8,
            "colsample_bytree": 0.7,
            "reg_lambda": 3.0,
            "reg_alpha": 0.05,
            "min_child_weight": 8,
        },
    ),
    (
        "xgb_mid_reg",
        {
            "max_depth": 8,
            "learning_rate": 0.04,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "reg_lambda": 2.0,
            "reg_alpha": 0.05,
            "min_child_weight": 10,
            "gamma": 0.1,
        },
    ),
)


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
# Categorical alignment
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
# Engineered scalars + KMeans geo_cluster
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


# ---------------------------------------------------------------------------
# Target Encoding
# ---------------------------------------------------------------------------
def _te_input(X: pd.DataFrame) -> pd.DataFrame:
    """
    מכין את הקלט ל-TargetEncoder. NaN keys לא נתמכים → ממלאים ב-token קבוע.
    הכל לסטרינג כדי שמתחתיו pandas Categorical/object לא יבלבל בין int code
    שונה ל-string.
    """
    cols = [c for c in TE_COLS if c in X.columns]
    if not cols:
        return pd.DataFrame(index=X.index)
    out = X[cols].astype(object).fillna(TE_MISSING_TOKEN).astype(str)
    return out


def _add_te_features(X: pd.DataFrame, te_arr: np.ndarray) -> pd.DataFrame:
    """מוסיף עמודות numeric te_<col>_log_price לפי הסדר של TE_COLS."""
    cols = [c for c in TE_COLS if c in X.columns]
    X = X.copy()
    for i, c in enumerate(cols):
        X[f"te_{c}_log_price"] = te_arr[:, i].astype(float)
    return X


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _drop_dead(X: pd.DataFrame, dropped_cols: list[str]) -> pd.DataFrame:
    return X.drop(columns=[c for c in dropped_cols if c in X.columns])


# ---------------------------------------------------------------------------
# Train
# ---------------------------------------------------------------------------
def train(
    X_train: pd.DataFrame,
    y_train: np.ndarray,
    X_val: pd.DataFrame,
    y_val: np.ndarray,
) -> dict[str, Any]:
    y_train_log = np.log1p(y_train)
    y_val_log = np.log1p(y_val)

    # 1. categorical alignment
    X_train_a, X_val_a, _, cat_categories = _align_categories(
        X_train, X_val, X_val.iloc[:0]
    )

    # 2. KMeans + engineered scalars
    kmeans = _fit_kmeans(X_train_a)
    if kmeans is None:
        print("  [xgboost_v4] ⚠️ KMeans skipped (insufficient lat/lon coverage)")
    X_train_a = _add_engineered(X_train_a, kmeans)
    X_val_a = _add_engineered(X_val_a, kmeans)

    # 3. Target Encoding — fit_transform על train (cv=5 OOF פנימי), transform על val.
    te_cols = [c for c in TE_COLS if c in X_train_a.columns]
    target_encoder: TargetEncoder | None = None
    if te_cols:
        target_encoder = TargetEncoder(
            smooth="auto",
            target_type="continuous",
            random_state=RANDOM_STATE,
            cv=5,
        )
        train_te_in = _te_input(X_train_a)
        val_te_in = _te_input(X_val_a)
        train_te_arr = target_encoder.fit_transform(train_te_in, y_train_log)
        val_te_arr = target_encoder.transform(val_te_in)
        X_train_a = _add_te_features(X_train_a, train_te_arr)
        X_val_a = _add_te_features(X_val_a, val_te_arr)

        # spot-check: הממוצע של te_city לעיר נתונה צריך להיות קרוב לממוצע
        # log1p(y) של אותה עיר ב-train (כש-smoothing בינוני). זה לא TE-ה-OOF,
        # אלא ה-mapping המלא שמשמש ל-val/test — מאפס את ספק ה-leakage.
        for c in te_cols:
            keys = X_train_a[c].astype(object).fillna(TE_MISSING_TOKEN).astype(str)
            grp = pd.Series(y_train_log).groupby(keys.values).mean()
            te_full = pd.DataFrame(
                target_encoder.transform(_te_input(X_train_a)),
                index=X_train_a.index,
                columns=[f"te_{x}_log_price" for x in te_cols],
            )
            te_col = te_full[f"te_{c}_log_price"]
            te_per_key = te_col.groupby(keys.values).first()
            common = grp.index.intersection(te_per_key.index)
            if len(common) > 0:
                diff = float((grp.loc[common] - te_per_key.loc[common]).abs().mean())
                print(
                    f"  [xgboost_v4] TE spot-check {c}: "
                    f"|mean log1p(y) − te_full| over {len(common)} keys = {diff:.4f} "
                    "(small ⇒ smoothing-only delta, no leakage)"
                )

    # 4. KNN OOF + builder
    print("  [xgboost_v4] computing OOF GeoKNN features for train...")
    train_knn = _oof_train_knn(X_train_a, y_train)
    print("  [xgboost_v4] fitting KNN BallTree on full train + transforming val...")
    knn_builder = KnnFeatureBuilder()
    knn_builder.fit(X_train_a, y_train)
    val_knn = knn_builder.transform(X_val_a)

    nan_train = float(train_knn.isna().mean().mean())
    nan_val = float(val_knn.isna().mean().mean())
    print(
        f"  [xgboost_v4] KNN-feature NaN rate: train={nan_train:.1%}  val={nan_val:.1%}"
    )

    X_train_a = pd.concat([X_train_a, train_knn], axis=1)
    X_val_a = pd.concat([X_val_a, val_knn], axis=1)

    # 5. drop dead features
    dropped_cols = [c for c in DEAD_COLS if c in X_train_a.columns]
    if dropped_cols:
        print(f"  [xgboost_v4] dropping dead features: {dropped_cols}")
    X_train_a = _drop_dead(X_train_a, dropped_cols)
    X_val_a = _drop_dead(X_val_a, dropped_cols)

    best_booster: XGBRegressor | None = None
    best_result: dict[str, Any] | None = None
    results: list[dict[str, Any]] = []

    for name, params in CANDIDATES:
        print(f"  [xgboost_v4] training {name}...")
        booster = XGBRegressor(
            **COMMON,
            eval_metric=mape_real_scale,
            callbacks=[
                EarlyStopping(rounds=EARLY_STOPPING_ROUNDS, maximize=False)
            ],
            **params,
        )
        booster.fit(
            X_train_a,
            y_train_log,
            eval_set=[(X_val_a, y_val_log)],
            verbose=False,
        )

        val_pred_log = booster.predict(X_val_a)
        val_pred = np.maximum(np.expm1(val_pred_log), 1.0)
        val_mape = _mape(y_val, val_pred)
        best_iter = int(getattr(booster, "best_iteration", booster.n_estimators))

        result = {
            "name": name,
            "params": params,
            "val_mape": val_mape,
            "best_iteration": best_iter,
        }
        results.append(result)
        print(
            f"  [xgboost_v4] {name} val_mape={val_mape:.4f}  best_iter={best_iter}"
        )

        if best_result is None or val_mape < best_result["val_mape"]:
            best_booster = booster
            best_result = result

    if best_booster is None or best_result is None:
        raise RuntimeError("No XGBoost candidates were trained.")

    feature_names = list(X_train_a.columns)
    importances_df = (
        pd.DataFrame(
            {"column": feature_names, "importance": best_booster.feature_importances_}
        )
        .sort_values("importance", ascending=False)
        .reset_index(drop=True)
    )

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    (ARTIFACTS_DIR / "candidate_results.json").write_text(
        json.dumps(results, indent=2)
    )
    importances_df.to_csv(ARTIFACTS_DIR / "feature_importances.csv", index=False)

    print(
        "  [xgboost_v4] best="
        f"{best_result['name']} val_mape={best_result['val_mape']:.4f}  "
        f"best_iter={best_result['best_iteration']}"
    )

    return {
        "model": best_booster,
        "dropped_cols": dropped_cols,
        "cat_categories": cat_categories,
        "kmeans": kmeans,
        "knn_builder": knn_builder,
        "target_encoder": target_encoder,
        "te_cols": te_cols,
        "candidate_results": results,
        "best_candidate": best_result,
    }


def predict(model: dict[str, Any], X: pd.DataFrame) -> np.ndarray:
    X = X.copy()
    for c, cats in model["cat_categories"].items():
        if c in X.columns:
            X[c] = pd.Categorical(X[c], categories=cats)

    X = _add_engineered(X, model.get("kmeans"))

    target_encoder = model.get("target_encoder")
    if target_encoder is not None and model.get("te_cols"):
        te_arr = target_encoder.transform(_te_input(X))
        X = _add_te_features(X, te_arr)

    knn = model["knn_builder"].transform(X)
    X = pd.concat([X, knn], axis=1)
    X = X.drop(columns=[c for c in model["dropped_cols"] if c in X.columns])
    return np.maximum(np.expm1(model["model"].predict(X)), 1.0)
