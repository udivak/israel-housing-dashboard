import os
import pandas as pd
import numpy as np

from pymongo import MongoClient
from dotenv import load_dotenv
from tqdm import tqdm

# ========================
# CONFIG
# ========================

load_dotenv()

MONGO_URI = os.getenv("MONGODB_URI", "")
DB_NAME = os.getenv("MONGODB_DB_NAME", "")

OUTPUT_FILE = "temporal_features.xlsx"

# ========================
# MONGO
# ========================

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

raw_col = db["raw_records"]

# ========================
# LOAD RAW TRANSACTIONS
# ========================

def load_transactions():
    print("📥 Loading transactions...")

    cursor = raw_col.find(
        {},
        {
            "_id": 1,
            "source_name": 1,
            "raw_payload": 1
        }
    )

    data = list(cursor)
    return pd.DataFrame(data)

# ========================
# LOAD CBS INDEX
# ========================

def load_cbs():
    print("📥 Loading CBS index...")

    cursor = raw_col.find(
        {"source_name": "cbs_housing"},
        {"raw_payload": 1}
    )

    rows = []

    for doc in cursor:
        p = doc["raw_payload"]

        rows.append({
            "year": p.get("year"),
            "quarter": p.get("quarter"),
            "price_index": p.get("current_base"),
            "annual_change": p.get("percent_change_annual")
        })

    df = pd.DataFrame(rows)

    # ניקוי
    df = df.dropna(subset=["year", "quarter"])
    df = df.sort_values(["year", "quarter"])

    return df

# ========================
# EXTRACT FIELDS
# ========================

def extract_fields(row):
    p = row.get("raw_payload", {})

    return {
        "_id": row["_id"],
        "source_name": row.get("source_name"),

        "transaction_date": p.get("dealDate") or p.get("transaction_date"),
        "price": p.get("dealAmount") or p.get("price"),

        "area_sqm": p.get("assetArea") or p.get("area_sqm"),
        "rooms": p.get("roomNum") or p.get("rooms"),

        "year_built": p.get("yearBuilt") or p.get("building_year")
    }

# ========================
# MAIN PIPELINE
# ========================

def run():
    df = load_transactions()

    print("🔧 Extracting fields...")

    extracted = [extract_fields(r) for r in df.to_dict("records")]
    df = pd.DataFrame(extracted)

    # ========================
    # CLEAN TYPES
    # ========================

    df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df["area_sqm"] = pd.to_numeric(df["area_sqm"], errors="coerce")
    df["year_built"] = pd.to_numeric(df["year_built"], errors="coerce")

    # ========================
    # TIME FEATURES
    # ========================

    df["year"] = df["transaction_date"].dt.year
    df["quarter"] = df["transaction_date"].dt.quarter

    df["property_age"] = df["year"] - df["year_built"]

    df["is_new"] = (df["property_age"] <= 3).astype(int)
    df["is_old"] = (df["property_age"] >= 30).astype(int)

    # ========================
    # PRICE FEATURES
    # ========================

    df["price_per_sqm"] = df["price"] / df["area_sqm"]

    # ========================
    # CBS MERGE
    # ========================

    cbs = load_cbs()

    df = df.merge(cbs, on=["year", "quarter"], how="left")

    # ========================
    # REAL PRICE
    # ========================

    latest_index = cbs["price_index"].max()

    df["real_price"] = df["price"] * (latest_index / df["price_index"])
    df["real_price_factor"] = latest_index / df["price_index"]

    df["price_per_sqm_real"] = df["real_price"] / df["area_sqm"]

    # ========================
    # LOG FEATURES (למודלים)
    # ========================

    df["log_price"] = df["price"].apply(lambda x: None if pd.isna(x) else np.log1p(x))
    df["log_price_per_sqm"] = df["price_per_sqm"].apply(lambda x: None if pd.isna(x) else np.log1p(x))

    # ========================
    # SAVE
    # ========================

    print("💾 Saving Excel...")

    df.to_excel(OUTPUT_FILE, index=False)

    print(f"✅ Done → {OUTPUT_FILE}")

# ========================
# RUN
# ========================

if __name__ == "__main__":
    run()