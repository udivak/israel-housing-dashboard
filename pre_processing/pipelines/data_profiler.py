"""
full_profiler.py — תמונה מלאה של כל הנתונים בכל source
כולל top-level fields, geometry, raw_payload, וכל מה שביניהם
"""

import os
from pymongo import MongoClient
from dotenv import load_dotenv
from collections import defaultdict, Counter
import pandas as pd

load_dotenv()
db = MongoClient(os.getenv("MONGODB_URI"))[os.getenv("MONGODB_DB_NAME")]
col = db[os.getenv("MONGODB_RAW_COLLECTION", "raw_records")]

SOURCES = ["nadlan_gov", "odata_il_nadlan", "tax_authority_nadlan", "cbs_housing"]
SAMPLE_N = 500
SEP_HEAVY = "=" * 72
SEP_LIGHT = "-" * 72


def hdr(title):
    print(f"\n{SEP_HEAVY}\n  {title}\n{SEP_HEAVY}")


def sub(title):
    print(f"\n  ── {title}")


# ================================================================
# 0. TOTALS
# ================================================================
hdr("0. ROW COUNTS")
totals = {}
for src in SOURCES:
    n = col.count_documents({"source_name": src})
    totals[src] = n
    print(f"  {src:<32} {n:>8,}")

# ================================================================
# 1. TOP-LEVEL FIELDS (מחוץ ל-raw_payload)
# ================================================================
hdr("1. TOP-LEVEL FIELDS (excluding raw_payload)")

for src in SOURCES:
    sub(src)
    docs = list(col.find({"source_name": src}).limit(SAMPLE_N))
    total = len(docs)

    field_data = defaultdict(list)
    for doc in docs:
        for k, v in doc.items():
            if k in ("_id", "raw_payload"):
                continue
            field_data[k].append(v)

    print(f"\n  {'field':<26} {'non_null':>8} {'null%':>6}  {'type(s)':<22}  sample")
    print(f"  {'-'*26} {'-'*8} {'-'*6}  {'-'*22}  {'-'*30}")

    for field, vals in sorted(field_data.items()):
        non_null = [v for v in vals if v is not None and v != \"\" and v != []]
        null_pct = 100 * (total - len(non_null)) / total
        types = Counter(type(v).__name__ for v in non_null)
        type_str = \", \".join(f\"{t}({n})\" for t, n in types.most_common(2))
        samples = []
        for v in non_null:
            sv = str(v)[:50]
            if sv not in samples:
                samples.append(sv)
            if len(samples) == 2:
                break
        print(f\"  {field:<26} {len(non_null):>8} {null_pct:>5.1f}%  {type_str:<22}  {' | '.join(samples)}\")

# ================================================================
# 2. GEOMETRY DEEP DIVE
# ================================================================
hdr("2. GEOMETRY FIELDS")

for src in SOURCES:
    sub(src)
    docs = list(col.find({"source_name": src}).limit(SAMPLE_N))
    total = len(docs)

    has_geo_toplevel = sum(1 for d in docs if "geometry" in d)
    has_geo_payload = sum(1 for d in docs if "geometry" in d.get("raw_payload", {}))

    print(f"  top-level geometry:     {has_geo_toplevel}/{total}")
    print(f"  raw_payload.geometry:   {has_geo_payload}/{total}")

    sample = next((d for d in docs if "geometry" in d), None)
    if sample:
        geo = sample["geometry"]
        print(f"  sample (top-level):     {geo}")

    sample_p = next((d for d in docs if "geometry" in d.get("raw_payload", {})), None)
    if sample_p:
        geo = sample_p["raw_payload"]["geometry"]
        print(f"  sample (raw_payload):   {geo}")

    if not sample and not sample_p:
        print("  (no geometry found)")

# ================================================================
# 3. GEOGRAPHIC / LOCATION FIELDS — raw_payload
# ================================================================
hdr("3. GEOGRAPHIC & LOCATION FIELDS — raw_payload")

GEO_FIELDS = {
    "nadlan_gov": [
        "address",
        "neighborhoodName",
        "neighborhoodId",
        "settlmentID",
        "streetCode",
        "polygonId",
        "parcelNum",
    ],
    "odata_il_nadlan": ["city", "street", "display_address", "full_address", "polygon_id", "block"],
    "tax_authority_nadlan": [
        "settlementId",
        "settlementNameHeb",
        "settlementNameEng",
        "streetCode",
        "streetNameHeb",
        "streetNameEng",
        "houseNum",
        "neighborhood",
        "polygon_id",
        "gushNum",
        "parcelNum",
        "subParcelNum",
    ],
    "cbs_housing": [],
}

for src, fields in GEO_FIELDS.items():
    if not fields:
        continue
    sub(src)
    docs = list(col.find({"source_name": src}, {"raw_payload": 1}).limit(SAMPLE_N))
    total = len(docs)

    print(f"  {'field':<26} {'non_null':>8} {'null%':>6}  sample_values")
    print(f"  {'-'*26} {'-'*8} {'-'*6}  {'-'*40}")

    for f in fields:
        vals = [d["raw_payload"].get(f) for d in docs]
        non_null = [v for v in vals if v is not None and v != 0 and v != \"\"]
        null_pct = 100 * (len(vals) - len(non_null)) / len(vals)
        samples = []
        for v in non_null:
            sv = str(v)[:35]
            if sv not in samples:
                samples.append(sv)
            if len(samples) == 3:
                break
        print(f\"  {f:<26} {len(non_null):>8} {null_pct:>5.1f}%  {' | '.join(samples)}\")

# ================================================================
# 4. SETTLEMENT ID DISTRIBUTION
# ================================================================
hdr("4. SETTLEMENT IDs — distribution")

sub("nadlan_gov — settlmentID")
docs = list(col.find({"source_name": "nadlan_gov"}, {"raw_payload.settlmentID": 1}).limit(5000))
ids = [d["raw_payload"].get("settlmentID") for d in docs if d["raw_payload"].get("settlmentID")]
c = Counter(ids)
print(f"  distinct settlement IDs in sample: {len(c)}")
print(f"  top 10: {c.most_common(10)}")

sub("tax_authority_nadlan — settlementId + settlementNameHeb")
docs = list(
    col.find(
        {"source_name": "tax_authority_nadlan"},
        {"raw_payload.settlementId": 1, "raw_payload.settlementNameHeb": 1},
    ).limit(5000)
)
pairs = [(d["raw_payload"].get("settlementId"), d["raw_payload"].get("settlementNameHeb")) for d in docs]
id_name = {sid: name for sid, name in pairs if sid and name}
print(f"  distinct settlement IDs in sample: {len(set(p[0] for p in pairs if p[0]))}")
print(f"  sample ID→name mapping (10):")
for sid, name in list(id_name.items())[:10]:
    print(f"    {sid} → {name}")

sub("odata_il_nadlan — city values")
docs = list(col.find({"source_name": "odata_il_nadlan"}, {"raw_payload.city": 1}).limit(5000))
cities = Counter(d["raw_payload"].get("city") for d in docs if d["raw_payload"].get("city"))
print(f"  distinct cities in sample: {len(cities)}")
print(f"  top 10: {cities.most_common(10)}")

# ================================================================
# 5. ALL RAW_PAYLOAD FIELDS — complete list per source
# ================================================================
hdr("5. COMPLETE raw_payload FIELD LIST")

for src in SOURCES:
    sub(src)
    docs = list(col.find({"source_name": src}, {"raw_payload": 1}).limit(SAMPLE_N))
    total = len(docs)

    field_data = defaultdict(list)
    for doc in docs:
        for k, v in doc.get("raw_payload", {}).items():
            field_data[k].append(v)

    print(f"  {'field':<28} {'non_null':>8} {'null%':>6}  {'types':<24}  sample")
    print(f"  {'-'*28} {'-'*8} {'-'*6}  {'-'*24}  {'-'*30}")

    for field, vals in sorted(field_data.items()):
        non_null = [v for v in vals if v is not None and v != \"\" and v != []]
        null_pct = 100 * (total - len(non_null)) / total
        types = Counter(type(v).__name__ for v in non_null)
        type_str = \", \".join(f\"{t}({n})\" for t, n in types.most_common(2))
        samples = []
        for v in non_null:
            sv = str(v)[:35]
            if sv not in samples:
                samples.append(sv)
            if len(samples) == 2:
                break
        print(f\"  {field:<28} {len(non_null):>8} {null_pct:>5.1f}%  {type_str:<24}  {' | '.join(samples)}\")

print(f"\n{SEP_HEAVY}")
print("  PROFILING COMPLETE")
print(SEP_HEAVY)

