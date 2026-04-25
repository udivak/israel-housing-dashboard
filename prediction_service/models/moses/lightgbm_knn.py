"""
LightGBM + KNN geographic features.

הוספת פיצ'רים של "מה מחיר העסקאות הקרובות גיאוגרפית":
    - knn5_mean_price_per_sqm     ממוצע מחיר למ"ר של 5 השכנים הקרובים
    - knn10_median_price_per_sqm  חציון מחיר למ"ר של 10 שכנים
    - knn5_dist_weighted_price    ממוצע משוקלל-מרחק (קרובים יותר → משקל גדול יותר)

טיפול ב-data leakage:
    - לרשומות val/test: השכנים נלקחים מ-train בלבד (אין leakage).
    - לרשומות train (בזמן fit): out-of-fold עם 5 folds — אף שורה לא רואה את עצמה.

ה-BallTree הסופי מאומן על כל ה-train ונשמר עם המודל. ב-predict() הוא משמש
לחשב את הפיצ'רים עבור כל קלט חדש.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.neighbors import BallTree
from sklearn.model_selection import KFold

K_NEAR = 5
K_MID = 10
N_FOLDS = 5
EARTH_RADIUS_M = 6_371_000.0


# ---------------------------------------------------------------------------
# KNN feature engineering — לפי lat/lon אמיתיים מ-raw_records
# ---------------------------------------------------------------------------
def _build_tree(lat: np.ndarray, lon: np.ndarray) -> BallTree:
    """BallTree עם haversine distance. ערכים ברדיאנים."""
    coords = np.column_stack([np.radians(lat), np.radians(lon)])
    return BallTree(coords, metric="haversine")


def _query_features(tree: BallTree, ref_pps: np.ndarray, ref_price: np.ndarray,
                    lat_q: np.ndarray, lon_q: np.ndarray, skip_self: bool = False
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


def _empty_features(n: int) -> dict[str, np.ndarray]:
    return {
        "knn5_mean_price_per_sqm": np.full(n, np.nan),
        "knn10_median_price_per_sqm": np.full(n, np.nan),
        "knn5_dist_weighted_price": np.full(n, np.nan),
    }


def _has_coords(X: pd.DataFrame) -> np.ndarray:
    """mask של רשומות עם lat/lon תקינים."""
    if "lat" not in X.columns or "lon" not in X.columns:
        return np.zeros(len(X), dtype=bool)
    return (X["lat"].notna() & X["lon"].notna()).values


def _compute_pps(price: np.ndarray, area: np.ndarray) -> np.ndarray:
    """price_per_sqm. למקרה של area חסר/אפס — NaN."""
    pps = np.full_like(price, np.nan, dtype=float)
    valid = (area > 0) & ~np.isnan(area) & ~np.isnan(price)
    pps[valid] = price[valid] / area[valid]
    return pps


# ---------------------------------------------------------------------------
# Out-of-fold train features
# ---------------------------------------------------------------------------
def _oof_train_features(X: pd.DataFrame, y: np.ndarray) -> pd.DataFrame:
    """
    מחשב KNN features ל-train ב-out-of-fold כדי שלא תהיה דליפה.
    """
    n = len(X)
    feats = _empty_features(n)
    has = _has_coords(X)
    if has.sum() == 0:
        return pd.DataFrame(feats, index=X.index)

    lat = X["lat"].values
    lon = X["lon"].values
    area = X["area_sqm"].values
    pps_full = _compute_pps(y, area)

    has_idx = np.where(has)[0]
    kf = KFold(n_splits=N_FOLDS, shuffle=True, random_state=42)
    for fold, (ref_local, qry_local) in enumerate(kf.split(has_idx)):
        ref_idx = has_idx[ref_local]
        qry_idx = has_idx[qry_local]
        tree = _build_tree(lat[ref_idx], lon[ref_idx])
        out = _query_features(tree, pps_full[ref_idx], y[ref_idx].astype(float),
                              lat[qry_idx], lon[qry_idx], skip_self=False)
        for k, v in out.items():
            feats[k][qry_idx] = v

    return pd.DataFrame(feats, index=X.index)


# ---------------------------------------------------------------------------
# KnnFeatureBuilder — נשמר בתוך המודל לשימוש ב-predict
# ---------------------------------------------------------------------------
class KnnFeatureBuilder:
    """BallTree של train + מחירים. שימוש ב-predict על קלט חדש."""

    def __init__(self):
        self.tree = None
        self.ref_pps = None
        self.ref_price = None

    def fit(self, X_train: pd.DataFrame, y_train: np.ndarray) -> None:
        has = _has_coords(X_train)
        if has.sum() == 0:
            return
        lat = X_train["lat"].values[has]
        lon = X_train["lon"].values[has]
        area = X_train["area_sqm"].values[has]
        price = y_train[has].astype(float)
        self.tree = _build_tree(lat, lon)
        self.ref_pps = _compute_pps(price, area)
        self.ref_price = price

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        n = len(X)
        feats = _empty_features(n)
        if self.tree is None:
            return pd.DataFrame(feats, index=X.index)
        has = _has_coords(X)
        if has.sum() == 0:
            return pd.DataFrame(feats, index=X.index)
        lat = X["lat"].values
        lon = X["lon"].values
        out = _query_features(self.tree, self.ref_pps, self.ref_price,
                              lat[has], lon[has], skip_self=False)
        for k, v in out.items():
            feats[k][np.where(has)[0]] = v
        return pd.DataFrame(feats, index=X.index)


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------
LGB_PARAMS = dict(
    n_estimators=10000, learning_rate=0.01, num_leaves=511,
    min_child_samples=5, subsample=0.8, colsample_bytree=0.8,
    reg_alpha=0.01, reg_lambda=0.01,
    random_state=42, n_jobs=-1, verbose=-1,
)


def train(X_train, y_train, X_val, y_val):
    print("  [knn] computing OOF features for train...")
    train_knn = _oof_train_features(X_train, y_train)
    X_train_aug = pd.concat([X_train, train_knn], axis=1)

    print("  [knn] fitting BallTree on full train + transforming val...")
    builder = KnnFeatureBuilder()
    builder.fit(X_train, y_train)
    val_knn = builder.transform(X_val)
    X_val_aug = pd.concat([X_val, val_knn], axis=1)

    nan_train = train_knn.isna().mean().mean()
    nan_val = val_knn.isna().mean().mean()
    print(f"  [knn] knn features NaN rate: train={nan_train:.1%}  val={nan_val:.1%}")

    print("  [knn] training LightGBM with KNN features...")
    model = lgb.LGBMRegressor(**LGB_PARAMS)
    model.fit(
        X_train_aug, np.log1p(y_train),
        eval_set=[(X_val_aug, np.log1p(y_val))],
        eval_metric="mape",
        callbacks=[lgb.early_stopping(150), lgb.log_evaluation(200)],
    )

    return {"lgbm": model, "builder": builder}


def predict(model, X):
    knn = model["builder"].transform(X)
    X_aug = pd.concat([X, knn], axis=1)
    return np.expm1(model["lgbm"].predict(X_aug))
