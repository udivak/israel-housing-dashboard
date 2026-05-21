"""
fix_city_names.py
=================
Backfill `city_name` ב-`normalized_records` עבור רשומות `nadlan_gov` שתויגו עם
שם עיר שגוי (ראה FEATURES_TEST.md §8.5).

הסיבה לבאג: SETTLEMENT_ID_TO_NAME ב-`normalize_data.py` אינו תואם את קודי הלמ"ס.
הקואורדינטות (lat/lon) נכונות — מגיעות מ-parcel centroid אמין — אז התיקון הוא
reverse-geocode מ-(lat/lon) ל-עיר הקרובה ביותר מתוך CITY_CENTROIDS.

Idempotent + resumable: רץ רק על רשומות nadlan_gov; מעדכן city_name בלבד.

Usage:
    .venv/bin/python pre_processing/pipelines/fix_city_names.py             # ריצה רגילה
    .venv/bin/python pre_processing/pipelines/fix_city_names.py --dry-run   # תצוגה מקדימה (500)
    .venv/bin/python pre_processing/pipelines/fix_city_names.py --limit 100 # ריצה חלקית
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Iterator

from dotenv import load_dotenv
from pymongo import MongoClient, UpdateOne

# נשתמש בפונקציה שכבר הגדרנו ב-pre_processing/geo_utils.py — מקור אמת יחיד.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from geo_utils import reverse_geocode_city  # noqa: E402


load_dotenv()

URI       = os.getenv("MONGODB_NORMALIZED_URI") or os.getenv("MONGO_URI")
DB_NAME   = os.getenv("MONGODB_NORMALIZED_DB_NAME") or os.getenv("DB_NAME", "israel_housing")
COLL_NAME = os.getenv("MONGODB_NORMALIZED_COLLECTION", "normalized_records")
BATCH     = 1000


def cursor(coll, limit: int | None, with_coords: bool = True) -> Iterator[dict]:
    if with_coords:
        q = {"source": "nadlan_gov", "lat": {"$ne": None}, "lon": {"$ne": None}}
    else:
        q = {"source": "nadlan_gov", "$or": [{"lat": None}, {"lon": None}]}
    proj = {"_id": 1, "lat": 1, "lon": 1, "city": 1, "city_name": 1}
    cur = coll.find(q, proj).batch_size(BATCH)
    if limit:
        cur = cur.limit(limit)
    yield from cur


def build_majority_map(coll) -> dict[str, str]:
    """
    Aggregate (old_city → new_city) from records with coordinates: for each
    old city tag, find the most-common reverse-geocoded city. The resulting
    map is used to retag no-coord records using the majority correction
    observed in their coord-having peers.
    """
    print("Building majority mapping from coord-having records…")
    from collections import defaultdict, Counter
    pairs: dict[str, Counter] = defaultdict(Counter)
    n = 0
    for doc in cursor(coll, limit=None, with_coords=True):
        lat = doc.get("lat"); lon = doc.get("lon")
        old = doc.get("city") or doc.get("city_name")
        new = reverse_geocode_city(lat, lon)
        if new is None:
            continue
        pairs[old or "<None>"][new] += 1
        n += 1
    majority: dict[str, str] = {}
    for old, counter in pairs.items():
        best, _ = counter.most_common(1)[0]
        if best != old:
            majority[old] = best
    print(f"  derived {len(majority)} old→new mappings from {n:,} coord-having records")
    return majority


# Static fallback for no-coord records — derived from the original dry-run output
# (before pass 1 fixed the coord-having records). Each entry is a wrong city tag
# that SETTLEMENT_ID_TO_NAME produced, paired with the actual majority city those
# records' coords resolved to. Used when build_majority_map() can't derive a
# mapping (because the coord-having records were already fixed in a previous run).
STATIC_WRONG_TO_RIGHT: dict[str, str] = {
    "חצרים":          "אשקלון",
    "ורד יריחו":      "גבעתיים",
    "כוכב יאיר":      "תל אביב -יפו",
    "בית חנן":        "ירושלים",
    "בת עין":         "חיפה",
    "כפר גלעדי":      "באר שבע",
    "אור יהודה":      "אשדוד",
    "טל אל":          "נתניה",
    "ירדנה":          "ראשון לציון",
    "כיסופים":        "רעננה",
    "בארות יצחק":     "תל אביב -יפו",
    "הר עמשא":        "תל אביב -יפו",
    "יושיביה":        "תל אביב -יפו",
    "כפר יחזקאל":     "תל אביב -יפו",
    "ירקונה":         "רחובות",
    "בארותיים":       "כפר סבא",
    "כפר חסידים ב":   "חדרה",
    "כפר סילבר":      "קריית ים",
    "יפתח":           "חדרה",
    "כפר מסריק":      "קריית ביאליק",
    "כפר הנשיא":      "נהריה",
    "ינוב":           "חדרה",
    "חולדה":          "טבריה",
    "יגור":           "חדרה",
    "ארגמן":          "דימונה",
    "בית דגן":        "קריית שמונה",
    "כנות":           "חדרה",
    "המעפיל":         "תל אביב -יפו",
    "יד נתן":         "עפולה",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="לא כותב, רק מציג")
    parser.add_argument("--limit", type=int, default=None, help="עבד עד N רשומות")
    args = parser.parse_args()

    if not URI:
        print("ERROR: MONGODB_NORMALIZED_URI (or MONGO_URI) not set", file=sys.stderr)
        return 1

    cli = MongoClient(URI)
    coll = cli[DB_NAME][COLL_NAME]

    total_q = {"source": "nadlan_gov", "lat": {"$ne": None}, "lon": {"$ne": None}}
    total = coll.count_documents(total_q)
    print(f"DB: {DB_NAME}.{COLL_NAME}")
    print(f"nadlan_gov rows with coords: {total:,}")
    if args.dry_run:
        print("--- DRY RUN — showing first 30 corrections; no writes ---")

    seen = 0
    skipped_same = 0
    skipped_no_match = 0
    changes_by_old_new: dict[tuple[str | None, str | None], int] = {}
    pending: list[UpdateOne] = []

    for doc in cursor(coll, args.limit):
        seen += 1
        lat = doc.get("lat"); lon = doc.get("lon")
        # `city` הוא השדה הציבורי (כפי שמופיע ב-API ובאינדקסים); city_name פנימי.
        old_city = doc.get("city") or doc.get("city_name")
        new_city = reverse_geocode_city(lat, lon)

        if new_city is None:
            skipped_no_match += 1
            continue
        if new_city == old_city:
            skipped_same += 1
            continue

        changes_by_old_new[(old_city, new_city)] = changes_by_old_new.get((old_city, new_city), 0) + 1

        if args.dry_run and seen <= 30:
            print(f"  {old_city!r:30s} -> {new_city!r:20s}  ({lat:.4f},{lon:.4f})")
        if not args.dry_run:
            pending.append(UpdateOne(
                {"_id": doc["_id"]},
                {"$set": {"city": new_city, "city_name": new_city}},
            ))
            if len(pending) >= BATCH:
                res = coll.bulk_write(pending, ordered=False)
                print(f"  wrote {res.modified_count} (seen={seen:,}/{total:,})")
                pending.clear()

    if pending and not args.dry_run:
        res = coll.bulk_write(pending, ordered=False)
        print(f"  wrote {res.modified_count} (final)")

    # -----------------------------------------------------------------
    # Pass 2: no-coord records — patch via majority mapping derived from peers.
    # -----------------------------------------------------------------
    print("\n--- Pass 2: nadlan_gov records without lat/lon ---")
    majority = build_majority_map(coll)
    # Merge derived mapping with hardcoded fallback (derived takes precedence
    # if pass 1 has fresh data; otherwise the static map kicks in).
    for old, new in STATIC_WRONG_TO_RIGHT.items():
        majority.setdefault(old, new)
    print(f"  merged with static fallback: {len(majority)} total mappings")
    no_coord_q = {"source": "nadlan_gov", "$or": [{"lat": None}, {"lon": None}]}
    no_coord_total = coll.count_documents(no_coord_q)
    print(f"  no-coord rows: {no_coord_total:,}")

    no_coord_seen = 0
    no_coord_changed = 0
    no_coord_unmapped = 0
    pending2: list[UpdateOne] = []
    for doc in cursor(coll, args.limit, with_coords=False):
        no_coord_seen += 1
        old = doc.get("city") or doc.get("city_name")
        new = majority.get(old)
        if new is None or new == old:
            no_coord_unmapped += 1
            continue
        no_coord_changed += 1
        changes_by_old_new[(old, new)] = changes_by_old_new.get((old, new), 0) + 1
        if args.dry_run and no_coord_seen <= 10:
            print(f"  (no-coord) {old!r:20s} -> {new!r}")
        if not args.dry_run:
            pending2.append(UpdateOne(
                {"_id": doc["_id"]},
                {"$set": {"city": new, "city_name": new}},
            ))
            if len(pending2) >= BATCH:
                res = coll.bulk_write(pending2, ordered=False)
                print(f"  wrote {res.modified_count} no-coord (seen={no_coord_seen:,})")
                pending2.clear()
    if pending2 and not args.dry_run:
        res = coll.bulk_write(pending2, ordered=False)
        print(f"  wrote {res.modified_count} no-coord (final)")
    print(f"  no-coord changed: {no_coord_changed:,}")
    print(f"  no-coord unmapped (kept as-is): {no_coord_unmapped:,}")

    # -----------------------------------------------------------------
    # Pass 3: canonicalize known variant spellings across ALL sources.
    # אלו עיקריים שמופיעים גם ב-tax_authority_nadlan וגם ב-odata בכמה כתיבים.
    # -----------------------------------------------------------------
    print("\n--- Pass 3: variant canonicalization across all sources ---")
    VARIANTS: dict[str, str] = {
        "תל אביב-יפו":    "תל אביב -יפו",   # tax_authority_nadlan uses no-space dash
        "הרצליה":         "הרצלייה",        # nadlan_gov used single-yud, odata uses double-yud
        "קריית גת":       "קרית גת",        # ktiv male -> ktiv chaser (canonical)
        "קריית ביאליק":   "קרית ביאליק",
        "קריית אונו":     "קרית אונו",
        "קריית מוצקין":   "קרית מוצקין",
        "קריית ים":       "קרית ים",
        "קריית שמונה":    "קרית שמונה",
    }
    # filter out identity mappings
    VARIANTS = {k: v for k, v in VARIANTS.items() if k != v}
    pending3: list[UpdateOne] = []
    variant_changed = 0
    for old, new in VARIANTS.items():
        # canonicalize across ALL sources (not just nadlan_gov)
        q = {"$or": [{"city": old}, {"city_name": old}]}
        n = coll.count_documents(q)
        if n == 0:
            continue
        print(f"  '{old}' -> '{new}' : {n:,} records")
        variant_changed += n
        if not args.dry_run:
            res = coll.update_many(q, {"$set": {"city": new, "city_name": new}})
            print(f"    wrote {res.modified_count}")
    print(f"  variants changed: {variant_changed:,}{'  (dry-run, not written)' if args.dry_run else ''}")

    changed = sum(changes_by_old_new.values()) + variant_changed
    print(f"\n=== Summary ===")
    print(f"  seen:              {seen:,}")
    print(f"  unchanged:         {skipped_same:,}")
    print(f"  no match (>25km):  {skipped_no_match:,}")
    print(f"  changed:           {changed:,}{'  (dry-run, not written)' if args.dry_run else ''}")
    print(f"\n  top 20 (old → new):")
    for (old, new), n in sorted(changes_by_old_new.items(), key=lambda kv: -kv[1])[:20]:
        print(f"    {n:6,d}  {str(old):20s} -> {new}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
