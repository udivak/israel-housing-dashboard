import os
import geopandas as gpd
from pymongo import MongoClient, UpdateOne
from dotenv import load_dotenv
from tqdm import tqdm


load_dotenv()

MONGO_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("MONGODB_DB_NAME")
COLLECTION = os.getenv("MONGODB_RAW_COLLECTION", "raw_records")

PARCEL_PATH = os.getenv("PARCEL_PATH", "parcel_all/PARCEL_ALL.shp")

BATCH_SIZE = 1000


# -----------------------------
# connect mongo
# -----------------------------

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION]


# -----------------------------
# load parcel shapefile
# -----------------------------

print("loading parcels...")

gdf = gpd.read_file(PARCEL_PATH)


# -----------------------------
# centroid in projected CRS
# -----------------------------

print("creating centroids...")

gdf["centroid"] = gdf.geometry.centroid


# -----------------------------
# convert to WGS84
# -----------------------------

print("reprojecting to WGS84...")

centroids = gdf.set_geometry("centroid").to_crs(epsg=4326)


# -----------------------------
# build lookup map
# -----------------------------

print("building lookup map...")

parcel_map = {}

for row in tqdm(centroids.itertuples(), total=len(centroids)):
    try:
        gush = str(int(row.GUSH_NUM))
        parcel = str(int(row.PARCEL))

        key = f"{gush}-{parcel}"

        point = row.centroid

        parcel_map[key] = (point.x, point.y)

    except Exception:
        continue


print("parcel map size:", len(parcel_map))


# -----------------------------
# helper function
# -----------------------------


def extract_parcel_key(doc):
    payload = doc.get("raw_payload", {})
    source = doc.get("source_name")

    try:
        # ---------- nadlan.gov ----------
        if source == "nadlan_gov":
            parcel_num = payload.get("parcelNum")

            if parcel_num:
                parts = parcel_num.split("-")
                if len(parts) >= 2:
                    return f"{parts[0]}-{parts[1]}"

            polygon = payload.get("polygonId")

            if polygon and "-" in polygon:
                return polygon

        # ---------- odata dataset ----------
        block = payload.get("block")

        if block:
            parts = block.split("-")
            if len(parts) >= 2:
                return f"{parts[0]}-{parts[1]}"

        # ---------- fallback ----------
        polygon = payload.get("polygonId")

        if polygon and "-" in polygon:
            return polygon

    except Exception:
        pass

    return None


# -----------------------------
# query records
# -----------------------------

query = {"geometry": {"$exists": False}}

projection = {
    "raw_payload.block": 1,
    "raw_payload.parcelNum": 1,
    "raw_payload.polygonId": 1,
    "source_name": 1,
}

total = collection.count_documents(query)

print("documents to update:", total)

cursor = collection.find(query, projection, batch_size=1000)


# -----------------------------
# update mongo
# -----------------------------

batch = []
missing = set()

for doc in tqdm(cursor, total=total):
    key = extract_parcel_key(doc)

    if not key:
        continue

    coords = parcel_map.get(key)

    if not coords:
        missing.add(key)
        continue

    batch.append(
        UpdateOne(
            {"_id": doc["_id"]},
            {
                "$set": {
                    "geometry": {
                        "type": "Point",
                        "coordinates": list(coords),
                    }
                }
            },
        )
    )

    if len(batch) >= BATCH_SIZE:
        collection.bulk_write(batch)
        batch = []


if batch:
    collection.bulk_write(batch)


print("done")
print("missing parcels:", len(missing))

