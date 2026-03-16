"""
Nadlan.gov.il scraper — Israel Real Estate Tax Authority.

Uses Playwright (sync) to navigate the UI, trigger searches, and intercept
the AWS API responses. The API returns Base64+GZIP-compressed JSON.
"""

from __future__ import annotations

import asyncio
import base64
import gzip
import hashlib
import json
import random
import time
from typing import Any, ClassVar, Optional

import structlog
from playwright.sync_api import sync_playwright

from app.core.config import Settings, settings

from app.models.records import RetrievalMethod
from app.scrapers.base import BaseScraper, ScrapeResult

try:
    from playwright_stealth import Stealth
except ImportError:
    Stealth = None  # type: ignore[misc, assignment]

TARGET_API_URL = "execute-api.il-central-1.amazonaws.com/api/dea"
NADLAN_BASE_URL = "https://www.nadlan.gov.il/"

# Hebrew city names for nadlan.gov.il autocomplete (~50 cities).
NADLAN_CITIES: list[str] = [
    "תל אביב",
    "ירושלים",
    "חיפה",
    "באר שבע",
    "ראשון לציון",
    "פתח תקווה",
    "אשדוד",
    "נתניה",
    "בני ברק",
    "רמת גן",
    "בת ים",
    "רחובות",
    "אשקלון",
    "חולון",
    "הרצליה",
    "כפר סבא",
    "חדרה",
    "מודיעין מכבים רעות",
    "לוד",
    "רמלה",
    "קריית גת",
    "עכו",
    "נצרת",
    "טבריה",
    "צפת",
    "אילת",
    "קריית אונו",
    "יהוד",
    "אור יהודה",
    "גבעת שמואל",
    "הוד השרון",
    "אלעד",
    "ראש העין",
    "רמת השרון",
    "גבעתיים",
    "רעננה",
    "ביתר עילית",
    "מעלה אדומים",
    "ביתר",
    "עפולה",
    "כרמיאל",
    "נהריה",
    "דימונה",
    "טמרה",
    "שפרעם",
    "נתיבות",
    "אופקים",
    "קריית שמונה",
    "קריית מוצקין",
    "קריית ביאליק",
    "קריית ים",
    "מגדל העמק",
    "יקנעם",
    "זכרון יעקב",
    "חצור הגלילית",
]


def decode_nadlan_data(encoded_string: str) -> dict[str, Any] | None:
    """Decode Base64+GZIP-compressed string to JSON dict."""
    try:
        compressed_bytes = base64.b64decode(encoded_string)
        uncompressed_bytes = gzip.decompress(compressed_bytes)
        return json.loads(uncompressed_bytes.decode("utf-8"))
    except Exception as e:
        structlog.get_logger().warning("decode_nadlan_data failed", error=str(e))
        return None


def _content_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()


def _scrape_nadlan_sync(
    cities: list[str],
    headless: bool,
    initial_wait_s: float,
    page_timeout_ms: int,
    max_pages_per_city: int,
    delay_min_s: float,
    delay_max_s: float,
    logger: Any,
) -> tuple[list[dict[str, Any]], list[str]]:
    """
    Sync Playwright logic. Returns (all_records, city_errors).
    Each record is {"raw_payload": {...}, "content_hash": "..."}.
    """
    all_records: list[dict[str, Any]] = []
    city_errors: list[str] = []
    seen_hashes: set[str] = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        try:
            for city in cities:
                try:
                    city_records = _scrape_city_sync(
                        browser,
                        city,
                        seen_hashes,
                        initial_wait_s,
                        page_timeout_ms,
                        max_pages_per_city,
                        delay_min_s,
                        delay_max_s,
                        logger,
                    )
                    all_records.extend(city_records)
                    logger.info("City scraped", city=city, records=len(city_records))
                except Exception as exc:
                    city_errors.append(f"{city}: {exc}")
                    logger.warning(
                        "City scrape failed, skipping", city=city, error=str(exc)
                    )
        finally:
            browser.close()

    return all_records, city_errors


def _scrape_city_sync(
    browser: Any,
    city_name: str,
    seen_hashes: set[str],
    initial_wait_s: float,
    page_timeout_ms: int,
    max_pages_per_city: int,
    delay_min_s: float,
    delay_max_s: float,
    logger: Any,
) -> list[dict[str, Any]]:
    """Scrape one city: navigate, search, capture responses, paginate."""
    records: list[dict[str, Any]] = []
    captured: list[dict] = []

    def handle_response(response: Any) -> None:
        if TARGET_API_URL in response.url and response.status == 200:
            try:
                raw = response.json()
                if isinstance(raw, str):
                    decoded = decode_nadlan_data(raw)
                    if decoded:
                        captured.append(decoded)
            except Exception:
                pass

    context = browser.new_context()
    if Stealth is not None:
        try:
            stealth = Stealth()
            if hasattr(stealth, "apply_stealth"):
                stealth.apply_stealth(context)
        except Exception:
            pass  # Stealth API may vary by version
    page = context.new_page()
    page.set_default_timeout(page_timeout_ms)
    page.on("response", handle_response)

    page.goto(NADLAN_BASE_URL)
    page.wait_for_load_state("networkidle")

    # First search
    try:
        search_input = page.locator('input[type="text"]').first
        search_input.fill(city_name)
        time.sleep(1)
        page.keyboard.press("Enter")
    except Exception as e:
        logger.warning("Search input failed", city=city_name, error=str(e))
        page.close()
        context.close()
        return []

    # Wait for first response
    time.sleep(initial_wait_s)
    if not captured:
        logger.warning("No response captured for initial search", city=city_name)
        page.close()
        context.close()
        return []

    data = captured[-1]
    items = (data.get("data") or {}).get("items") or []
    total_page = (data.get("data") or {}).get("total_page") or 1
    pages_to_fetch = min(total_page, max_pages_per_city)

    for item in items:
        ch = _content_hash(item)
        if ch not in seen_hashes:
            seen_hashes.add(ch)
            records.append({"raw_payload": item, "content_hash": ch})

    # Pagination loop
    current_page = 1
    while current_page < pages_to_fetch:
        time.sleep(random.uniform(delay_min_s, delay_max_s))
        captured.clear()

        next_btn = page.locator(
            'button[aria-label="Next page"], .pagination-next, '
            '[aria-label="עמוד הבא"], button:has-text("הבא"), a:has-text("הבא")'
        ).first
        if not next_btn.count():
            logger.warning(
                "Next button not found", city=city_name, page=current_page
            )
            break

        try:
            next_btn.click()
        except Exception as e:
            logger.warning(
                "Next click failed", city=city_name, error=str(e)
            )
            break

        time.sleep(initial_wait_s)
        if not captured:
            logger.warning(
                "No response captured after next click", city=city_name
            )
            break

        data = captured[-1]
        items = (data.get("data") or {}).get("items") or []
        for item in items:
            ch = _content_hash(item)
            if ch not in seen_hashes:
                seen_hashes.add(ch)
                records.append({"raw_payload": item, "content_hash": ch})

        current_page += 1
        total_page = (data.get("data") or {}).get("total_page") or current_page
        pages_to_fetch = min(total_page, max_pages_per_city)

    page.close()
    context.close()
    return records


class NadlanGovScraper(BaseScraper):
    """Playwright-based scraper for nadlan.gov.il (Israel Tax Authority)."""

    source_name: ClassVar[str] = "nadlan_gov"
    source_url: ClassVar[str] = NADLAN_BASE_URL
    retrieval_method: ClassVar[RetrievalMethod] = RetrievalMethod.BROWSER

    def __init__(self, scraper_settings: Settings = settings) -> None:
        super().__init__(scraper_settings)
        self._cities = NADLAN_CITIES
        self._headless = self.settings.NADLAN_HEADLESS
        self._initial_wait_s = self.settings.NADLAN_INITIAL_WAIT_S
        self._page_timeout_ms = self.settings.NADLAN_PAGE_TIMEOUT_MS
        self._max_pages_per_city = self.settings.NADLAN_MAX_PAGES_PER_CITY
        self._delay_min_s = self.settings.NADLAN_DELAY_MIN_S
        self._delay_max_s = self.settings.NADLAN_DELAY_MAX_S

    async def fetch(self) -> ScrapeResult:
        """Run sync Playwright in a thread to avoid blocking the event loop."""
        all_records, city_errors = await asyncio.to_thread(
            _scrape_nadlan_sync,
            self._cities,
            self._headless,
            self._initial_wait_s,
            self._page_timeout_ms,
            self._max_pages_per_city,
            self._delay_min_s,
            self._delay_max_s,
            self._logger,
        )

        if not all_records and city_errors:
            return ScrapeResult(
                source_name=self.source_name,
                records=[],
                status="failed",
                error="; ".join(city_errors),
            )

        return ScrapeResult(
            source_name=self.source_name,
            records=all_records,
            status="success",
        )
