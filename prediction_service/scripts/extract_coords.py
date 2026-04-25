"""
מושך _id, lat, lon מ-raw_records ושומר ל-features_coords.csv.
ריצה חד-פעמית — מספיק להריץ פעם אחת או כשמתעדכנים נתונים חדשים.
"""
import os
import csv
from pathlib import Path
from pymongo import MongoClient
from dotenv import load_dotenv

ENV = Path(__file__).resolve().parent.parent.parent / "pre_processing" / ".env"
load_dotenv(ENV)

OUTPUT = Path(__file__).resolve().parent.parent.parent / "features_coords.csv"

uri = os.getenv("MONGODB_URI")
db_name = os.getenv("MONGODB_DB_NAME")
col_name = os.getenv("MONGODB_RAW_COLLECTION", "raw_records")

print(f"connecting to {db_name}.{col_name}...")
client = MongoClient(uri, serverSelectionTimeoutMS=15000)
col = client[db_name][col_name]
total = col.estimated_document_count()
print(f"{total:,} docs total")

# Atlas free tier אוסר no_cursor_timeout — נשבור ל-batches
BATCH = 5000
written = 0
skipped = 0
last_id = None

with open(OUTPUT, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["_id", "lon", "lat"])
    while True:
        query = {"geometry.coordinates": {"$exists": True}}
        if last_id is not None:
            query["_id"] = {"$gt": last_id}
        batch = list(col.find(query, {"_id": 1, "geometry.coordinates": 1})
                       .sort("_id", 1).limit(BATCH))
        if not batch:
            break
        for doc in batch:
            coords = (doc.get("geometry") or {}).get("coordinates") or []
            if len(coords) >= 2 and all(c is not None for c in coords[:2]):
                w.writerow([str(doc["_id"]), coords[0], coords[1]])
                written += 1
            else:
                skipped += 1
        last_id = batch[-1]["_id"]
        f.flush()
        print(f"  processed {written + skipped:,}  (written {written:,}, skipped {skipped:,})")

print(f"\n✅ done. wrote {written:,} rows to {OUTPUT}  ({skipped:,} skipped)")
