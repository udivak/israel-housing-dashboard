import os
from pymongo import MongoClient
from dotenv import load_dotenv
from collections import Counter

load_dotenv()
db = MongoClient(os.getenv("MONGODB_URI"))[os.getenv("MONGODB_DB_NAME")]
col = db["raw_records"]

docs = list(col.find({"source_name": "cbs_housing"}, {"raw_payload": 1}))
print(f"Total CBS docs: {len(docs)}\n")

# כל הקומבינציות של series_code + period_type + year range
combos = Counter()
year_by_combo = {}

for doc in docs:
    p = doc["raw_payload"]
    sc = p.get("series_code")
    pt = p.get("period_type")
    yr = p.get("year")
    q  = p.get("quarter")
    key = (sc, pt)
    combos[key] += 1
    if key not in year_by_combo:
        year_by_combo[key] = {"years": [], "has_quarter": 0}
    if yr:
        year_by_combo[key]["years"].append(yr)
    if q is not None:
        year_by_combo[key]["has_quarter"] += 1

print(f"{'series_code':<14} {'period_type':<12} {'count':>6}  {'year_range':<16}  has_quarter")
print("-" * 70)
for (sc, pt), cnt in sorted(combos.items(), key=lambda x: -x[1]):
    years = year_by_combo[(sc, pt)]["years"]
    yr_range = f"{min(years)}–{max(years)}" if years else "?"
    hq = year_by_combo[(sc, pt)]["has_quarter"]
    print(f"{str(sc):<14} {str(pt):<12} {cnt:>6}  {yr_range:<16}  {hq}")

# דוגמה מכל combo
print("\n--- Sample doc per combo ---")
seen = set()
for doc in docs:
    p = doc["raw_payload"]
    key = (p.get("series_code"), p.get("period_type"))
    if key not in seen:
        seen.add(key)
        print(f"\n{key}:")
        print({k: v for k, v in p.items() if k not in ("base_description",)})