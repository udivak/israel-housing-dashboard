"""
ETL: temporal_features.xlsx + features_osm.csv + features_coords.csv
     -> Mongo collection `features_enriched` with H3 indices and 2dsphere.

Idempotent: bulk upsert by _id. Run again after pre_processing regenerates the files.

Env:
    MONGO_URI            (default: mongodb://localhost:27017)
    DB_NAME              (default: israel_housing)
    FEATURES_COLLECTION  (default: features_enriched)
    OUTPUTS_DIR          (default: pre_processing/outputs)
    BATCH_SIZE           (default: 2000)
    H3_RESOLUTIONS       (default: 5,7,8)

Run:
    python -m pre_processing.pipelines.load_to_mongo
"""

from __future__ import annotations

import logging
import math
import os
import sys
from pathlib import Path

import h3
import pandas as pd
from pymongo import MongoClient, UpdateOne
from pymongo.errors import BulkWriteError
from tqdm import tqdm

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("load_to_mongo")

ROOT = Path(__file__).resolve().parents[2]
OUTPUTS_DIR = Path(os.getenv("OUTPUTS_DIR", str(ROOT / "pre_processing" / "outputs")))
TEMPORAL_PATH = OUTPUTS_DIR / "temporal_features.xlsx"
OSM_PATH = OUTPUTS_DIR / "features_osm.csv"
COORDS_PATH = OUTPUTS_DIR / "features_coords.csv"

MONGO_URI = os.getenv("MONGO_URI") or os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME") or os.getenv("MONGODB_DB_NAME", "israel_housing")
COLLECTION = os.getenv("FEATURES_COLLECTION", "features_enriched")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "2000"))
H3_RESOLUTIONS = [int(x) for x in os.getenv("H3_RESOLUTIONS", "5,7,8").split(",")]


def _clean_value(v):
    """Mongo-safe scalar: NaN/Inf -> None."""
    if v is None:
        return None
    if isinstance(v, float):
        if math.isnan(v) or math.isinf(v):
            return None
    return v


def _doc_from_row(row: pd.Series) -> dict | None:
    lon, lat = row.get("lon"), row.get("lat")
    has_geom = pd.notna(lon) and pd.notna(lat)

    base: dict = {k: _clean_value(v) for k, v in row.items() if k not in ("lon", "lat")}

    if has_geom:
        lon_f, lat_f = float(lon), float(lat)
        base["geometry"] = {"type": "Point", "coordinates": [lon_f, lat_f]}
        for res in H3_RESOLUTIONS:
            base[f"h3_r{res}"] = h3.latlng_to_cell(lat_f, lon_f, res)
    else:
        base["geometry"] = None

    if "transaction_date" in base and base["transaction_date"] is not None:
        ts = pd.to_datetime(base["transaction_date"], errors="coerce")
        base["transaction_date"] = None if pd.isna(ts) else ts.to_pydatetime()

    return base


def load_dataframes() -> pd.DataFrame:
    log.info("Reading temporal: %s", TEMPORAL_PATH)
    temporal = pd.read_excel(TEMPORAL_PATH)
    log.info("  rows=%d cols=%d", len(temporal), len(temporal.columns))

    log.info("Reading osm: %s", OSM_PATH)
    osm = pd.read_csv(OSM_PATH)
    log.info("  rows=%d cols=%d", len(osm), len(osm.columns))

    log.info("Reading coords: %s", COORDS_PATH)
    coords = pd.read_csv(COORDS_PATH)
    log.info("  rows=%d cols=%d", len(coords), len(coords.columns))

    log.info("Joining on _id (inner)")
    df = temporal.merge(osm, on="_id", how="inner").merge(coords, on="_id", how="inner")
    log.info("Joined: rows=%d cols=%d", len(df), len(df.columns))
    return df


def upsert_bulk(coll, df: pd.DataFrame) -> tuple[int, int]:
    upserts = matched = 0
    pbar = tqdm(total=len(df), desc="upsert", unit="doc")
    ops: list[UpdateOne] = []
    for _, row in df.iterrows():
        doc = _doc_from_row(row)
        if doc is None:
            pbar.update(1)
            continue
        _id = doc.pop("_id", None)
        if _id is None:
            pbar.update(1)
            continue
        ops.append(UpdateOne({"_id": _id}, {"$set": doc}, upsert=True))
        if len(ops) >= BATCH_SIZE:
            res = coll.bulk_write(ops, ordered=False)
            upserts += res.upserted_count
            matched += res.matched_count
            pbar.update(len(ops))
            ops.clear()
    if ops:
        res = coll.bulk_write(ops, ordered=False)
        upserts += res.upserted_count
        matched += res.matched_count
        pbar.update(len(ops))
    pbar.close()
    return upserts, matched


def ensure_indexes(coll) -> None:
    log.info("Ensuring indexes on %s", coll.name)
    coll.create_index([("geometry", "2dsphere")], name="geo_2dsphere")
    for res in H3_RESOLUTIONS:
        coll.create_index(f"h3_r{res}", name=f"h3_r{res}")
    coll.create_index("city", name="city")
    coll.create_index("neighborhood", name="neighborhood")
    coll.create_index("transaction_date", name="transaction_date")
    coll.create_index("price_per_sqm", name="price_per_sqm")
    coll.create_index([("city", 1), ("transaction_date", -1)], name="city_date")
    coll.create_index([("source_name", 1)], name="source_name")
    coll.create_index(
        [("city", "text"), ("neighborhood", "text"), ("street", "text")],
        name="text_search",
        default_language="none",
    )


def main() -> int:
    if not (TEMPORAL_PATH.exists() and OSM_PATH.exists() and COORDS_PATH.exists()):
        log.error("Missing input files in %s", OUTPUTS_DIR)
        return 1

    log.info("Mongo: %s db=%s collection=%s", MONGO_URI, DB_NAME, COLLECTION)
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    coll = db[COLLECTION]

    df = load_dataframes()
    try:
        upserts, matched = upsert_bulk(coll, df)
    except BulkWriteError as exc:
        log.error("Bulk write error: %s", exc.details)
        return 2

    log.info("Upserts: %d  Matched: %d", upserts, matched)
    ensure_indexes(coll)
    log.info("Done. Total docs in %s: %d", COLLECTION, coll.estimated_document_count())
    return 0


if __name__ == "__main__":
    sys.exit(main())
