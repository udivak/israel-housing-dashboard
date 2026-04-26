"""
Loader v2 — שלוש שכבות במקום שתיים.

שכבות:
    1. load_temporal_csv() → temporal_features.csv (במקום ה-xlsx; הרבה יותר מהיר)
    2. load_normalized()   → MongoDB normalized_records (city / neighborhood /
                              floor / building_floors / deal_nature / project_name /
                              is_new_project / lon / lat). Cache ל-parquet.
    3. load_osm()          → re-export מ-common.data (אותו קובץ).
    4. build_dataset()     → join על _id + clean + select_features.
    5. split / load_data   → זהה ל-v1 (random 80/10/10 + log1p target דרך המודל).

כדי להפעיל:
    python run.py udi/random_forest_v2 --data v2

Env vars:
    MONGODB_NORMALIZED_URI         — חובה (אלא אם ה-cache קיים)
    MONGODB_NORMALIZED_DB_NAME     — ברירת-מחדל "israel_housing"
    MONGODB_NORMALIZED_COLLECTION  — ברירת-מחדל "normalized_records"
    NORMALIZED_PARQUET             — דריסה לנתיב ה-cache
    NORMALIZED_REFRESH=1           — מאלץ refresh מ-Mongo גם אם cache קיים
    TEMPORAL_CSV / OSM_CSV         — דריסה לנתיבי הקבצים
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

from common.data import load_osm  # re-export — שמירה על מקור-אמת יחיד


def _log(msg: str) -> None:
    """לוג קצר לקונסול + flush כדי שנראה אותו בזמן אמת."""
    print(f"[data_v2] {msg}", flush=True)


# ---------------------------------------------------------------------------
# Env — טוענים את .env של פרוייקט-השורש (אין pre_processing/.env בריפו).
# ---------------------------------------------------------------------------
ROOT_REPO = Path(__file__).resolve().parent.parent.parent  # israel-housing-dashboard/
load_dotenv(ROOT_REPO / ".env")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent  # prediction_service/

_CANDIDATES = [
    ROOT_REPO,                                              # israel-housing-dashboard/
    ROOT_REPO.parent / "data_istrael_housing",              # ../data_istrael_housing
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


TEMPORAL_CSV = _find("temporal_features.csv", "TEMPORAL_CSV")
OSM_CSV      = _find("features_osm.csv",      "OSM_CSV")

# Cache: לא עובר דרך _find — חייב לשבת מתחת ל-prediction_service/ ולא ב-repo root.
CACHE_PARQUET = Path(os.getenv("NORMALIZED_PARQUET",
                               ROOT / "cache" / "normalized.parquet"))
CACHE_PARQUET.parent.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Target + feature lists (זהה ל-v1, פרט ל-ID_COLS / LOW_VALUE_COLS / CATEGORICAL_COLS)
# ---------------------------------------------------------------------------
TARGET = "real_price"

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

# שינוי מ-v1: neighborhood הוצא מ-ID_COLS — בגרסה זו הוא feature קטגורי.
ID_COLS = {"_id", "source_name", "street", "project_name", "transaction_date"}

# שינוי מ-v1: is_new_project יצא — לא קבוע יותר ברגע ש-odata לא היחיד שמסמן 1.
LOW_VALUE_COLS: set[str] = set()

# שינוי מ-v1: neighborhood התווסף.
CATEGORICAL_COLS = ["deal_nature", "city", "neighborhood"]

EXCLUDED_SOURCES = {"odata_il_nadlan"}

# ---------------------------------------------------------------------------
# Filtering / split (זהה ל-v1 כדי שהשוואה תהיה הוגנת)
# ---------------------------------------------------------------------------
TRAIN_END = pd.Timestamp("2024-01-01")
VAL_END = pd.Timestamp("2025-01-01")
MIN_DATE = pd.Timestamp("2015-01-01")
MIN_AREA = 15
MAX_AREA = 500
WINSOR_LOW = 0.01
WINSOR_HIGH = 0.99

# ---------------------------------------------------------------------------
# Mongo projection — שדות שמושכים מ-normalized_records.
# מכוון לא לכלול את 'source' (המקור הגולמי) כי temporal כבר נושא source_name —
# כפילות תזליג את ה-source-string הגולמי לתוך מטריצת ה-features.
# ---------------------------------------------------------------------------
_MONGO_PROJECTION = {
    "_id": 1,            # נדרש ל-cursor pagination; נופל אחר-כך.
    "source_id": 1,
    "transaction_date": 1,  # fallback ל-temporal CSV שמחסיר אותו ב-non-odata.
    "city_name": 1,
    "neighborhood": 1,
    "floor": 1,
    "building_floors": 1,
    "deal_nature": 1,
    "project_name": 1,
    "is_new_project": 1,
    "lon": 1,
    "lat": 1,
}

_NORMALIZED_COLS = [
    "_id",  # join key (לאחר rename מ-source_id)
    "transaction_date_norm",  # rename בעת ה-merge כדי לא להתנגש עם temporal.
    "city",  # לאחר rename מ-city_name
    "neighborhood",
    "floor",
    "building_floors",
    "deal_nature",
    "project_name",
    "is_new_project",
    "lon",
    "lat",
]


# ---------------------------------------------------------------------------
# Loading layers
# ---------------------------------------------------------------------------
def load_temporal_csv(path: Path = TEMPORAL_CSV) -> pd.DataFrame:
    """טוען את temporal_features.csv (במקום ה-xlsx של v1)."""
    if not path.exists():
        raise FileNotFoundError(
            f"temporal_features.csv לא נמצא ב-{path}. "
            f"קבע TEMPORAL_CSV או הרץ את ה-pre_processing pipeline."
        )
    _log(f"loading temporal csv ({path.name}, {path.stat().st_size/1e6:.1f}MB)...")
    t0 = time.time()
    df = pd.read_csv(path)
    df["_id"] = df["_id"].astype(str)
    df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
    _log(f"  → {len(df):,} rows × {df.shape[1]} cols  ({time.time()-t0:.1f}s)")
    return df


def _pull_normalized_from_mongo() -> pd.DataFrame:
    """
    מושך מ-normalized_records ב-batches של _id-cursor (Atlas free tier אוסר
    no_cursor_timeout). מחזיר DataFrame אחרי rename של source_id→_id ו-city_name→city.
    """
    # imports בתוך הפונקציה רק כדי שמודולים שלא משתמשים ב-Mongo לא יקרסו אם pymongo
    # חסר. ה-import הראשון (dotenv) הוא חובה — נתן ב-import הראשי.
    from pymongo import MongoClient  # pyright: ignore[reportMissingImports]

    uri = os.getenv("MONGODB_NORMALIZED_URI")
    if not uri:
        raise RuntimeError(
            "MONGODB_NORMALIZED_URI לא מוגדר; קבע אותו ב-.env או ספק "
            f"cache parquet ב-{CACHE_PARQUET}."
        )
    db_name = os.getenv("MONGODB_NORMALIZED_DB_NAME", "israel_housing")
    col_name = os.getenv("MONGODB_NORMALIZED_COLLECTION", "normalized_records")

    _log(f"connecting to mongo ({db_name}.{col_name})...")
    client = MongoClient(uri, serverSelectionTimeoutMS=15000)
    col = client[db_name][col_name]
    total = col.estimated_document_count()
    _log(f"  estimated {total:,} docs")

    BATCH = 5000
    rows: list[dict] = []
    last_id = None
    t0 = time.time()
    while True:
        query: dict = {}
        if last_id is not None:
            query["_id"] = {"$gt": last_id}
        batch = list(
            col.find(query, _MONGO_PROJECTION).sort("_id", 1).limit(BATCH)
        )
        if not batch:
            break
        rows.extend(batch)
        last_id = batch[-1]["_id"]
        _log(f"  pulled {len(rows):,} / ~{total:,}  ({time.time()-t0:.0f}s)")

    df = pd.DataFrame(rows)
    if df.empty:
        raise RuntimeError(
            f"normalized_records מ-{db_name}.{col_name} החזיר 0 רשומות. "
            "בדוק את ה-URI / שם ה-collection."
        )

    # source_id (string) הוא ה-join key. ה-_id המקורי של Mongo לא רלוונטי אחרי השליפה.
    df = df.drop(columns=["_id"])
    df = df.rename(columns={
        "source_id": "_id",
        "city_name": "city",
        # transaction_date מקבל suffix כדי לא להתנגש ב-merge עם העמודה
        # מה-temporal CSV. אנחנו ממלאים ממנה רק כשה-CSV NaN.
        "transaction_date": "transaction_date_norm",
    })
    df["_id"] = df["_id"].astype(str)
    if "transaction_date_norm" in df.columns:
        df["transaction_date_norm"] = pd.to_datetime(
            df["transaction_date_norm"], errors="coerce"
        )

    # שמור רק עמודות שאנחנו באמת רוצים (סדר יציב).
    df = df[[c for c in _NORMALIZED_COLS if c in df.columns]]

    _log(f"  → {len(df):,} normalized rows × {df.shape[1]} cols "
         f"({time.time()-t0:.0f}s total)")
    return df


def load_normalized() -> pd.DataFrame:
    """
    מחזיר את normalized_records, או מ-cache parquet או מ-Mongo.

    התנהגות:
        1. אם cache קיים ו-NORMALIZED_REFRESH != 1 → טוען מה-cache.
        2. אם URI קיים → מושך מ-Mongo, כותב cache, מחזיר.
        3. אם cache קיים אך URI חסר → טוען מה-cache (טוב לעבודה offline).
        4. אם שניהם חסרים → RuntimeError ברור.
    """
    refresh = os.getenv("NORMALIZED_REFRESH", "").strip() in ("1", "true", "True")
    cache_exists = CACHE_PARQUET.exists()
    uri = os.getenv("MONGODB_NORMALIZED_URI")

    if cache_exists and not refresh:
        _log(f"loading normalized from cache ({CACHE_PARQUET.name})...")
        t0 = time.time()
        df = pd.read_parquet(CACHE_PARQUET)
        df["_id"] = df["_id"].astype(str)
        _log(f"  → {len(df):,} rows × {df.shape[1]} cols  ({time.time()-t0:.1f}s)")
        return df

    if not uri:
        if cache_exists:
            _log(f"URI חסר ו-refresh=1; משתמש ב-cache הקיים ({CACHE_PARQUET.name}).")
            df = pd.read_parquet(CACHE_PARQUET)
            df["_id"] = df["_id"].astype(str)
            return df
        raise RuntimeError(
            "set MONGODB_NORMALIZED_URI or provide cache/normalized.parquet"
        )

    try:
        df = _pull_normalized_from_mongo()
    except Exception as e:
        if cache_exists:
            _log(f"⚠️  pymongo נכשל ({type(e).__name__}: {e}); נופלים ל-cache.")
            df = pd.read_parquet(CACHE_PARQUET)
            df["_id"] = df["_id"].astype(str)
            return df
        raise

    _log(f"writing cache → {CACHE_PARQUET}")
    df.to_parquet(CACHE_PARQUET, index=False)
    return df


# ---------------------------------------------------------------------------
# Join + cleanup
# ---------------------------------------------------------------------------
def join_layers(temporal: pd.DataFrame, normalized: pd.DataFrame,
                osm: pd.DataFrame) -> pd.DataFrame:
    """
    left-join על _id: temporal ⨝ normalized ⨝ osm. מדפיס כיסוי לכל שכבה
    כדי שכשל-join שקט ייחשף.

    אחרי ה-merge, נופלים על Mongo ל-`transaction_date` שלא נמצא ב-temporal
    (ה-temporal-CSV הנוכחי לא מחסיר תאריך לכל non-odata). אז נגזור מחדש
    `year`/`quarter`/`property_age` שמופקים מהתאריך.
    """
    _log("joining temporal ⨝ normalized ⨝ osm on _id...")
    t0 = time.time()

    merged = temporal.merge(normalized, on="_id", how="left", suffixes=("", "_norm"))
    city_cov = merged["city"].notna().mean() if "city" in merged.columns else 0.0
    nbh_cov = (merged["neighborhood"].notna().mean()
               if "neighborhood" in merged.columns else 0.0)
    latlon_cov = merged["lat"].notna().mean() if "lat" in merged.columns else 0.0
    _log(f"  + normalized: city={city_cov:.1%}  neighborhood={nbh_cov:.1%}  "
         f"lat/lon={latlon_cov:.1%}")

    merged = merged.merge(osm, on="_id", how="left", suffixes=("", "_osm"))
    first_osm_col = next((c for c in osm.columns if c != "_id"), None)
    osm_cov = merged[first_osm_col].notna().mean() if first_osm_col else 0.0
    _log(f"  + osm: coverage={osm_cov:.1%}")

    # ---- temporal-fallback מ-Mongo --------------------------------------
    if "transaction_date_norm" in merged.columns:
        td = pd.to_datetime(merged["transaction_date"], errors="coerce")
        td_norm = pd.to_datetime(merged["transaction_date_norm"], errors="coerce")
        n_filled = int((td.isna() & td_norm.notna()).sum())
        # combine_first: שומר ערכי-temporal שכבר קיימים, ממלא NaT ממונגו.
        merged["transaction_date"] = td.combine_first(td_norm)
        if n_filled > 0:
            _log(f"  + filled {n_filled:,} transaction_date NaT from normalized.")
        merged = merged.drop(columns=["transaction_date_norm"])

        # נגזור מחדש year/quarter/property_age על שורות חסרות.
        td_full = merged["transaction_date"]
        if "year" in merged.columns:
            need = merged["year"].isna() & td_full.notna()
            if need.any():
                merged.loc[need, "year"] = td_full[need].dt.year
        if "quarter" in merged.columns:
            need = merged["quarter"].isna() & td_full.notna()
            if need.any():
                merged.loc[need, "quarter"] = td_full[need].dt.quarter
        if "property_age" in merged.columns and "year_built" in merged.columns:
            need = (merged["property_age"].isna()
                    & merged["year_built"].notna()
                    & td_full.notna())
            if need.any():
                merged.loc[need, "property_age"] = (
                    td_full[need].dt.year - merged.loc[need, "year_built"]
                )

    # התראה רועשת אם כיסוי שכבה התרסק — סימן ל-join שבור או cache מיושן.
    for label, cov in (("city", city_cov), ("lat", latlon_cov), ("osm", osm_cov)):
        if cov < 0.5:
            _log(f"⚠️  כיסוי נמוך ל-{label} ({cov:.1%}). בדוק את ה-loader / cache.")

    _log(f"  → {len(merged):,} rows × {merged.shape[1]} cols  ({time.time()-t0:.1f}s)")
    return merged


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """זהה ל-data.py.clean פרט ל-real_price-fallback.

    ה-CSV הנוכחי של temporal_features אינו ממלא את real_price / price_index /
    real_price_factor (זה bug upstream ב-pre_processing). כדי שלא נגמור עם 0
    rows, נופלים ל-`price` הגולמי ומסמנים real_price_imputed=1. זה זהה
    אפקטיבית למה ש-v1 עשה ב-run 1 לפי EXPERIMENTS.md ("filled 71,054 missing
    real_price values from price"). הערה חשובה: התוצאה היא target נומינלי,
    לא CPI-adjusted — כל עוד ה-pre_processing pipeline לא מתוקן, אי אפשר
    להשוות בצורה הוגנת ל-runs ש-real_price שלהם היה צמוד-CPI.
    """
    _log("cleaning...")
    n0 = len(df)
    df = df.copy()

    df = df[~df["source_name"].isin(EXCLUDED_SOURCES)]
    _log(f"  after source filter:     {len(df):>8,}  (dropped {n0-len(df):,})")
    n = len(df)

    if TARGET in df.columns and "price" in df.columns:
        missing_target = df[TARGET].isna() & df["price"].notna()
        n_imp = int(missing_target.sum())
        if n_imp > 0:
            df = df.copy()
            df["real_price_imputed"] = missing_target.astype(int).values
            df.loc[missing_target, TARGET] = df.loc[missing_target, "price"].values
            _log(f"⚠️  real_price NaN — filled {n_imp:,} rows from `price` "
                 "(nominal target; upstream temporal pipeline isn't writing "
                 "real_price/price_index/factor).")

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
    """מחזיר רק את העמודות שייכנסו למודל (X).

    שינויים מ-v1:
        - neighborhood הוצא מ-ID_COLS → נכנס כקטגוריה.
        - is_new_project הוצא מ-LOW_VALUE_COLS → נכנס כפיצ'ר נומרי.
        - lon/lat *לא* מוסרים — RF יכול להשתמש בהם ישירות.
    """
    drop = LEAKAGE_COLS | ID_COLS | LOW_VALUE_COLS | {TARGET}
    X = df.drop(columns=[c for c in drop if c in df.columns])

    for c in CATEGORICAL_COLS:
        if c in X.columns:
            X[c] = X[c].astype("category")

    return X


# ---------------------------------------------------------------------------
# Split (זהה ל-v1)
# ---------------------------------------------------------------------------
def split(df: pd.DataFrame, seed: int = 42):
    """random 80/10/10 split (אותם seed וגדלים כמו v1 כדי שהשוואה תהיה הוגנת)."""
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
    """טוען את 3 השכבות, מאחד, ומנקה."""
    temporal = load_temporal_csv()
    normalized = load_normalized()
    osm = load_osm()
    merged = join_layers(temporal, normalized, osm)
    cleaned = clean(merged)
    return cleaned


def load_data():
    """entry point ל-runner. מחזיר X_train, y_train, X_val, y_val, X_test, y_test."""
    df = build_dataset()
    return split(df)
