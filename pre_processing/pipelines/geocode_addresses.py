"""Upgrade marker coordinates in `normalized_records` from parcel-block centroids
to address-level (street + house number) coordinates via Govmap autocomplete.

Run order: scrape → get_geom_by_block → normalize_data → geocode_addresses.

Idempotent: skips records already marked `coord_source == "address"`. Uses a
`geocode_cache` collection keyed by the query string to avoid repeated upstream
calls.

Flags:
    --limit N      process at most N records (default: all)
    --dry-run      print planned updates, write nothing
    --refresh      ignore the cache (re-query Govmap)
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient, UpdateOne
from tqdm import tqdm

# Allow `python pre_processing/pipelines/geocode_addresses.py` from repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib.govmap import (  # noqa: E402
    GeocodeResult,
    build_query,
    geocode_address,
    in_israel_bbox,
    make_client,
    polite_sleep,
)

load_dotenv()

NORM_URI = os.getenv("MONGODB_NORMALIZED_URI") or os.getenv("MONGODB_URI")
NORM_DB_NAME = (
    os.getenv("MONGODB_NORMALIZED_DB_NAME")
    or os.getenv("MONGODB_DB_NAME")
)
NORM_COLLECTION = os.getenv("MONGODB_NORMALIZED_COLLECTION", "normalized_records")
CACHE_COLLECTION = os.getenv("MONGODB_GEOCODE_CACHE", "geocode_cache")

REQUEST_DELAY_S = float(os.getenv("GOVMAP_REQUEST_DELAY_S", "0.2"))
BATCH_SIZE = 200


def _normalize_key(query: str) -> str:
    return " ".join(query.split()).lower()


def _cache_get(cache_col, key: str) -> GeocodeResult | None:
    doc = cache_col.find_one({"_id": key})
    if not doc:
        return None
    lat, lon = doc.get("lat"), doc.get("lon")
    if lat is None or lon is None:
        return None
    if not in_israel_bbox(float(lat), float(lon)):
        return None
    return GeocodeResult(lat=float(lat), lon=float(lon), raw_label=doc.get("label", ""))


def _cache_put(cache_col, key: str, query: str, result: GeocodeResult | None) -> None:
    cache_col.update_one(
        {"_id": key},
        {
            "$set": {
                "query": query,
                "lat": result.lat if result else None,
                "lon": result.lon if result else None,
                "label": result.raw_label if result else None,
                "fetched_at": datetime.now(timezone.utc),
                "hit": result is not None,
            }
        },
        upsert=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()

    if not NORM_URI or not NORM_DB_NAME:
        print("error: MONGODB_NORMALIZED_URI / MONGODB_NORMALIZED_DB_NAME not set")
        return 2

    client = MongoClient(NORM_URI)
    db = client[NORM_DB_NAME]
    norm_col = db[NORM_COLLECTION]
    cache_col = db[CACHE_COLLECTION]
    try:
        cache_col.create_index("fetched_at")
    except Exception as e:
        print(f"warning: could not create cache index: {e}")
        if not args.dry_run:
            print("error: DB write unavailable — cannot run geocoder. Free Atlas space first.")
            return 1

    query_filter = {"coord_source": {"$ne": "address"}, "street": {"$exists": True, "$ne": None}}
    total = norm_col.count_documents(query_filter)
    if args.limit:
        total = min(total, args.limit)
    print(f"candidates: {total}")

    cursor = norm_col.find(
        query_filter,
        {"_id": 1, "street": 1, "city_name": 1, "lat": 1, "lon": 1, "coord_source": 1},
        batch_size=500,
    )
    if args.limit:
        cursor = cursor.limit(args.limit)

    http = make_client()
    updates: list[UpdateOne] = []
    stats = {"hit_cache": 0, "hit_remote": 0, "miss": 0, "no_query": 0, "updated": 0}

    try:
        for doc in tqdm(cursor, total=total):
            query = build_query(doc.get("street"), doc.get("city_name"))
            if query is None:
                stats["no_query"] += 1
                continue

            key = _normalize_key(query)
            result: GeocodeResult | None = None
            if not args.refresh:
                result = _cache_get(cache_col, key)
                if result is not None:
                    stats["hit_cache"] += 1

            if result is None:
                result = geocode_address(http, query, city=doc.get("city_name"))
                if not args.dry_run:
                    _cache_put(cache_col, key, query, result)
                polite_sleep(REQUEST_DELAY_S)
                if result is not None:
                    stats["hit_remote"] += 1
                else:
                    stats["miss"] += 1

            if result is None:
                continue

            set_doc = {
                "lat": result.lat,
                "lon": result.lon,
                "coord_source": "address",
                "coord_label": result.raw_label,
                "coord_updated_at": datetime.now(timezone.utc),
            }
            if args.dry_run:
                print(f"[dry] {doc['_id']}  {query!r:60s} -> ({result.lat:.6f}, {result.lon:.6f})")
                stats["updated"] += 1
                continue

            updates.append(UpdateOne({"_id": doc["_id"]}, {"$set": set_doc}))
            if len(updates) >= BATCH_SIZE:
                norm_col.bulk_write(updates, ordered=False)
                stats["updated"] += len(updates)
                updates.clear()

        if updates and not args.dry_run:
            norm_col.bulk_write(updates, ordered=False)
            stats["updated"] += len(updates)
    finally:
        http.close()
        client.close()

    print("done:", stats)
    return 0


if __name__ == "__main__":
    sys.exit(main())
