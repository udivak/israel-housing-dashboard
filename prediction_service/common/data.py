"""
טעינה והכנת דאטה לאימון מודלים.

שכבות:
    1. load_temporal()  → העסקאות + macro + CBS (מ-temporal_features.xlsx)
    2. load_osm()       → פיצ'רים מרחביים (מ-features_osm.csv)
    3. build_dataset()  → join + ניקוי + בחירת פיצ'רים → (X, y)
    4. split()          → split כרונולוגי → train/val/test

למי ששם לב — load_data() הוא הקיצור שמריץ הכל ומחזיר 6 DataFrames מוכנים.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd


def _log(msg: str) -> None:
    """לוג קצר לקונסול + flush כדי שנראה אותו בזמן אמת."""
    print(f"[data] {msg}", flush=True)

# ---------------------------------------------------------------------------
# Paths — נחפש את הדאטה במספר מקומות; אפשר לדרוס ב-env vars.
# ---------------------------------------------------------------------------
_CANDIDATES = [
    Path(__file__).resolve().parent.parent.parent,                         # israel-housing-dashboard/
    Path(__file__).resolve().parent.parent.parent.parent / "data_istrael_housing",
]


def _find(filename: str, env_var: str) -> Path:
    override = os.getenv(env_var)
    if override:
        return Path(override)
    for base in _CANDIDATES:
        p = base / filename
        if p.exists():
            return p
    return _CANDIDATES[0] / filename  # default — ייכשל בטעינה עם הודעה ברורה


TEMPORAL_XLSX = _find("temporal_features.xlsx", "TEMPORAL_XLSX")
OSM_CSV = _find("features_osm.csv", "OSM_CSV")
COORDS_CSV = _find("features_coords.csv", "COORDS_CSV")

# ---------------------------------------------------------------------------
# Target + feature lists
# ---------------------------------------------------------------------------
TARGET = "real_price"

# עמודות שאסור להכניס למודל (מכילות/נגזרות מה-target → leakage, או זיהוי)
LEAKAGE_COLS = {
    "price",
    "price_per_sqm",
    "real_price",
    "real_price_per_sqm",
    "real_price_factor",
    "log_price",
    "log_price_per_sqm",
    "log_real_price",
}
ID_COLS = {"_id", "source_name", "neighborhood", "street",
           "project_name", "transaction_date"}

# רק פיצ'רים שבאמת חסרי ערך (קבועים). שאר הבינארים נשמרים — בדיקה הראתה
# שהסרתם פוגעת ב-MAPE למרות importance נמוך, כי הם אגרגציה של context.
LOW_VALUE_COLS = {
    "is_new_project",   # 100% קבוע
}

CATEGORICAL_COLS = ["deal_nature", "city"]

# מקורות שלא יכנסו לאימון. odata_il_nadlan נשמר מחוץ — הוא מחירים גבוהים-באופן-שיטתי
# (פרויקטים חדשים) ואין לו area_sqm; ניסיתי להחזיר אותו עם imputation, MAPE קפץ
# ל-0.235. ראה ניסיון 15 ב-EXPERIMENTS.md.
EXCLUDED_SOURCES = {"odata_il_nadlan"}

# ---------------------------------------------------------------------------
# Split boundaries (כרונולוגי)
# ---------------------------------------------------------------------------
TRAIN_END = pd.Timestamp("2024-01-01")
VAL_END = pd.Timestamp("2025-01-01")

# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------
MIN_DATE = pd.Timestamp("2015-01-01")
MIN_AREA = 15
MAX_AREA = 500
WINSOR_LOW = 0.01
WINSOR_HIGH = 0.99


# ---------------------------------------------------------------------------
# Loading layers
# ---------------------------------------------------------------------------
def load_temporal(path: Path = TEMPORAL_XLSX) -> pd.DataFrame:
    """טוען את temporal_features.xlsx (sheet 'transactions')."""
    _log(f"loading temporal xlsx ({path.name}, {path.stat().st_size/1e6:.1f}MB)...")
    t0 = time.time()
    df = pd.read_excel(path, sheet_name="transactions")
    df["_id"] = df["_id"].astype(str)
    df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
    _log(f"  → {len(df):,} rows × {df.shape[1]} cols  ({time.time()-t0:.1f}s)")
    return df


def load_osm(path: Path = OSM_CSV) -> pd.DataFrame:
    """טוען את features_osm.csv."""
    _log(f"loading osm csv ({path.name}, {path.stat().st_size/1e6:.1f}MB)...")
    t0 = time.time()
    df = pd.read_csv(path)
    df["_id"] = df["_id"].astype(str)
    df = df.drop(columns=[c for c in ("feature_source", "feature_version") if c in df.columns])
    _log(f"  → {len(df):,} rows × {df.shape[1]} cols  ({time.time()-t0:.1f}s)")
    return df


def load_coords(path: Path = COORDS_CSV) -> pd.DataFrame:
    """טוען _id, lat, lon מקובץ שהופק מ-raw_records.geometry."""
    if not path.exists():
        _log(f"⚠️ coords file not found at {path} — מודלים עם KNN יראו NaN")
        return pd.DataFrame(columns=["_id", "lat", "lon"])
    _log(f"loading coords ({path.name}, {path.stat().st_size/1e6:.1f}MB)...")
    t0 = time.time()
    df = pd.read_csv(path)
    df["_id"] = df["_id"].astype(str)
    _log(f"  → {len(df):,} rows  ({time.time()-t0:.1f}s)")
    return df


def join_layers(temporal: pd.DataFrame, osm: pd.DataFrame,
                coords: pd.DataFrame | None = None) -> pd.DataFrame:
    """left join: כל עסקה + פיצ'רי OSM + lat/lon (אופציונלי)."""
    _log(f"joining temporal ⨝ osm on _id...")
    t0 = time.time()
    merged = temporal.merge(osm, on="_id", how="left", suffixes=("", "_osm"))
    first_osm_col = next((c for c in osm.columns if c != "_id"), None)
    coverage = merged[first_osm_col].notna().mean() if first_osm_col else 0
    _log(f"  → {len(merged):,} rows  |  OSM coverage: {coverage:.1%}  ({time.time()-t0:.1f}s)")

    if coords is not None and len(coords) > 0:
        merged = merged.merge(coords, on="_id", how="left")
        cov = merged["lat"].notna().mean()
        _log(f"  + coords merged  |  lat/lon coverage: {cov:.1%}")

    return merged


# ---------------------------------------------------------------------------
# Cleaning
# ---------------------------------------------------------------------------
def impute_area_sqm(df: pd.DataFrame) -> pd.DataFrame:
    """
    משלים area_sqm חסר על-בסיס rooms × ממוצע area-per-room ב-(city, year).
    מוסיף עמודה area_imputed (0/1) כדי שהמודל ידע אילו רשומות הוערכו.

    הסיבה: רוב רשומות odata_il_nadlan חסרות area_sqm. כדי להחזיר אותן ל-train
    בלי להוסיף רעש, נחשב area משוער מ-rooms (שכן קיים) על-בסיס ערכי median
    ידועים מאותה עיר ושנה.
    """
    df = df.copy()
    df["area_imputed"] = df["area_sqm"].isna().astype(int)

    # ממוצע area-per-room לכל (city, year) — רק מרשומות שיש להן את שניהם
    valid = df["area_sqm"].notna() & df["rooms"].notna() & (df["rooms"] > 0)
    df_v = df.loc[valid].copy()
    df_v["apr"] = df_v["area_sqm"] / df_v["rooms"]

    # ירידה: city+year, אחר כך city בלבד, אחר כך גלובלי
    apr_city_year = df_v.groupby(["city", "year"])["apr"].median()
    apr_city = df_v.groupby("city")["apr"].median()
    apr_global = float(df_v["apr"].median())

    _log(f"impute_area_sqm: median area_per_room global={apr_global:.1f}")

    missing = df["area_sqm"].isna() & df["rooms"].notna() & (df["rooms"] > 0)
    n_missing = int(missing.sum())
    if n_missing == 0:
        return df

    def lookup(row):
        key = (row["city"], row["year"])
        if key in apr_city_year.index and not np.isnan(apr_city_year[key]):
            return apr_city_year[key]
        if row["city"] in apr_city.index and not np.isnan(apr_city[row["city"]]):
            return apr_city[row["city"]]
        return apr_global

    apr_filled = df.loc[missing].apply(lookup, axis=1)
    df.loc[missing, "area_sqm"] = df.loc[missing, "rooms"] * apr_filled.values
    if "log_area_sqm" in df.columns:
        df.loc[missing, "log_area_sqm"] = np.log1p(df.loc[missing, "area_sqm"])

    _log(f"impute_area_sqm: filled {n_missing:,} rows")
    return df


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """
    מפילים רשומה רק אם ה-target חסר או שה-date חסר.
    פיצ'רים חסרים (area_sqm, year_built וכו') — LightGBM מטפל ב-NaN מובנה,
    אז משאירים. outliers ב-area_sqm מסננים רק אם יש ערך.
    """
    _log("cleaning...")
    n0 = len(df)
    df = df.copy()

    df = df[~df["source_name"].isin(EXCLUDED_SOURCES)]
    _log(f"  after source filter:     {len(df):>8,}  (dropped {n0-len(df):,})")
    n = len(df)

    df = df[df[TARGET].notna()]
    _log(f"  after target not-null:   {len(df):>8,}  (dropped {n-len(df):,})")
    n = len(df)

    df = df[df["transaction_date"].notna() & (df["transaction_date"] >= MIN_DATE)]
    _log(f"  after date >= {MIN_DATE.date()}: {len(df):>8,}  (dropped {n-len(df):,})")
    n = len(df)

    area_ok = df["area_sqm"].isna() | df["area_sqm"].between(MIN_AREA, MAX_AREA)
    df = df[area_ok]
    _log(f"  after area_sqm range:    {len(df):>8,}  (dropped {n-len(df):,})")
    n = len(df)

    lo, hi = df[TARGET].quantile([WINSOR_LOW, WINSOR_HIGH])
    df = df[df[TARGET].between(lo, hi)]
    _log(f"  after winsorize target:  {len(df):>8,}  (dropped {n-len(df):,})")

    _log(f"  kept {len(df):,} / {n0:,} ({len(df)/n0:.1%})")
    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Feature selection
# ---------------------------------------------------------------------------
def select_features(df: pd.DataFrame) -> pd.DataFrame:
    """מחזיר רק את העמודות שייכנסו למודל (X)."""
    drop = LEAKAGE_COLS | ID_COLS | LOW_VALUE_COLS | {TARGET}
    X = df.drop(columns=[c for c in drop if c in df.columns])

    # categorical אמיתי — LightGBM יזהה
    for c in CATEGORICAL_COLS:
        if c in X.columns:
            X[c] = X[c].astype("category")

    return X


# ---------------------------------------------------------------------------
# Split
# ---------------------------------------------------------------------------
def split(df: pd.DataFrame, seed: int = 42):
    """
    Random 80/10/10 split. סיבה: כיום הדאטה מוטה לעבר 2024-2025 (רוב nadlan_gov
    הצטבר לאחרונה), כך ש-split כרונולוגי יוצר train קטן וחסר כיסוי.
    ברגע שיצטברו מספיק שנים מרובות — אפשר לעבור ל-split לפי transaction_date.
    """
    rng = np.random.default_rng(seed)
    idx = rng.permutation(len(df))
    n = len(df)
    n_train = int(0.80 * n)
    n_val = int(0.10 * n)
    train_idx = idx[:n_train]
    val_idx = idx[n_train:n_train + n_val]
    test_idx = idx[n_train + n_val:]

    def xy(indices):
        sub = df.iloc[indices]
        return select_features(sub), sub[TARGET].values.astype(float)

    X_train, y_train = xy(train_idx)
    X_val, y_val = xy(val_idx)
    X_test, y_test = xy(test_idx)
    _log(f"split (random 80/10/10) → train={len(X_train):,}  val={len(X_val):,}  "
         f"test={len(X_test):,}  (features={X_train.shape[1]})")
    return X_train, y_train, X_val, y_val, X_test, y_test


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------
def build_dataset() -> pd.DataFrame:
    """טוען + מאחד + מנקה. מחזיר DataFrame מלא (לפני split).

    הערה: lat/lon **לא** עוברים ל-select_features — הם רק כדי ש-KNN יוכל לחשב
    שכנים. ה-GBDT יראה את הקואורדינטות רק דרך הפיצ'ר KNN.
    """
    temporal = load_temporal()
    osm = load_osm()
    coords = load_coords()
    merged = join_layers(temporal, osm, coords)
    cleaned = clean(merged)
    return cleaned


def load_data():
    """
    ה-entry point של ה-runner. מריץ הכל ומחזיר:
        X_train, y_train, X_val, y_val, X_test, y_test
    """
    df = build_dataset()
    return split(df)
