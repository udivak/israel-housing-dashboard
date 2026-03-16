"""
Standalone Nadlan.gov.il scraper — With Memory & Popup Handling.
Remembers finished cities in MongoDB to avoid redundant runs.
"""
from __future__ import annotations

import base64
import gzip
import hashlib
import json
import os
import random
import time
import logging
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("scraper_debug.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv(Path(__file__).resolve().parent / ".env")

TARGET_API_URL = "execute-api.il-central-1.amazonaws.com/api/dea"
NADLAN_BASE_URL = "https://www.nadlan.gov.il/"
SOURCE_NAME = "nadlan_gov"
MAX_PAGES_TO_CLICK = 3000
CLICK_WAIT_MS = 1500

CITIES = [
    "ירושלים", "חיפה", "באר שבע", "ראשון לציון", "פתח תקווה",
    "אשדוד", "נתניה", "בני ברק", "רמת גן", "בת ים", "רחובות", "אשקלון",
    "חולון", "הרצליה", "כפר סבא", "חדרה", "מודיעין מכבים רעות", "לוד",
    "רמלה", "קריית גת", "עכו", "נצרת", "טבריה", "צפת", "אילת", "קריית אונו",
    "יהוד", "אור יהודה", "גבעת שמואל", "הוד השרון", "אלעד", "ראש העין",
    "רמת השרון", "גבעתיים", "רעננה", "ביתר עילית", "מעלה אדומים", "ביתר",
    "עפולה", "כרמיאל", "נהריה", "דימונה", "טמרה", "שפרעם", "נתיבות",
    "אופקים", "קריית שמונה", "קריית מוצקין", "קריית ביאליק", "קריית ים",
    "מגדל העמק", "יקנעם", "זכרון יעקב", "חצור הגלילית",
]

def decode_nadlan_data(encoded_string: str) -> dict | None:
    try:
        compressed_bytes = base64.b64decode(encoded_string)
        uncompressed_bytes = gzip.decompress(compressed_bytes)
        return json.loads(uncompressed_bytes.decode("utf-8"))
    except Exception as e:
        logger.error(f"שגיאה בפענוח: {e}")
        return None

def content_hash(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()

def scrape_city(browser, city_name: str, seen_hashes: set, col, status_col) -> tuple[int, int]:
    captured_data: list[dict] = []

    def handle_response(response):
        if TARGET_API_URL in response.url and response.status == 200:
            try:
                raw = response.json()
                if isinstance(raw, str):
                    decoded = decode_nadlan_data(raw)
                    if decoded: captured_data.append(decoded)
            except: pass

    page = browser.new_page()
    page.on("response", handle_response)

    logger.info(f"🚀 סריקה עמוקה: {city_name}")
    page.goto(NADLAN_BASE_URL)
    page.wait_for_load_state("networkidle")

    try:
        search_input = page.locator('input[type="text"]').first
        search_input.fill(city_name)
        time.sleep(1)
        page.keyboard.press("Enter")
    except Exception as e:
        logger.error(f"❌ שגיאה בחיפוש {city_name}: {e}")
        page.close()
        return 0, 0

    page.wait_for_timeout(5000)
    if not captured_data:
        page.close()
        return 0, 0

    inserted, skipped = 0, 0

    def save_captured_items():
        nonlocal inserted, skipped
        if not captured_data: return
        data_block = captured_data.pop()
        items = (data_block.get("data") or {}).get("items") or []
        for item in items:
            ch = content_hash(item)
            if ch in seen_hashes:
                skipped += 1
                continue
            seen_hashes.add(ch)
            doc = {
                "source_name": SOURCE_NAME,
                "ingested_at": datetime.now(timezone.utc),
                "raw_payload": item,
                "content_hash": ch,
            }
            try:
                col.insert_one(doc)
                inserted += 1
            except DuplicateKeyError:
                skipped += 1

    save_captured_items()

    for current_click in range(1, MAX_PAGES_TO_CLICK):
        # טיפול בפופ-אפ החסימה (אם מופיע)
        modal_close = page.locator('button[aria-label="Close"], .modal-close, button:has-text("✕")').first
        if modal_close.is_visible():
            logger.warning(f"[{city_name}] פופ-אפ חסימה הופיע! מנסה לסגור...")
            modal_close.click()
            page.wait_for_timeout(1000)

        next_btn = page.locator('button[aria-label="Next page"], .pagination-next, [aria-label="עמוד הבא"], button:has-text("הבא")').first
        if not next_btn.is_visible() or next_btn.is_disabled():
            break

        try:
            next_btn.click()
            page.wait_for_timeout(CLICK_WAIT_MS)
            if captured_data:
                save_captured_items()
            if current_click % 100 == 0:
                logger.info(f"  ... לחיצה {current_click} ...")
        except:
            break

    # סימון העיר כ"הושלמה" ב-DB
    status_col.update_one(
        {"city": city_name},
        {"$set": {"last_scraped": datetime.now(timezone.utc), "status": "completed"}},
        upsert=True
    )
    
    page.close()
    return inserted, skipped

def main():
    uri = os.getenv("MONGODB_URI")
    db_name = os.getenv("MONGODB_DB_NAME", "israel_housing")

    client = MongoClient(uri)
    db = client[db_name]
    col = db["raw_records"]
    status_col = db["scraping_status"] # אוסף הסטטוסים החדש

    # שליפת רשימת הערים שכבר סיימנו
    completed_cities = status_col.distinct("city", {"status": "completed"})
    logger.info(f"✅ ערים שכבר נסרקו ויושמטו: {completed_cities}, {len(completed_cities)}")
    logger.info(f"cities left to scrape: {len(CITIES)-len(completed_cities)}")

    seen_hashes: set[str] = set()
    total_new = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        try:
            for city in CITIES:
                if city in completed_cities:
                    logger.info(f"⏭️ מדלג על {city} - כבר נסרקה בהצלחה.")
                    continue
                
                ins, skip = scrape_city(browser, city, seen_hashes, col, status_col)
                total_new += ins
                logger.info(f"🏁 סיכום {city}: נשמרו {ins} עסקאות.")
        finally:
            browser.close()

    client.close()
    logger.info(f"✨ סיום. נשמרו {total_new} חדשות.")

if __name__ == "__main__":
    main()