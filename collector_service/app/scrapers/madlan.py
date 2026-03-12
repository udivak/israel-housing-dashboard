from __future__ import annotations

import asyncio
import hashlib
import json
import re
from datetime import UTC, datetime
from typing import Any, ClassVar

import httpx

from app.core.config import Settings, settings
from app.models.records import RetrievalMethod
from app.scrapers.base import BaseScraper, ScrapeResult
from app.scrapers.madlan_config import CITY_SLUGS, FOR_SALE_URL_TEMPLATE

# ---------------------------------------------------------------------------
# HTTP headers that pass PerimeterX bot-detection.
# Madlan serves full SSR HTML (HTTP 200) to regular browser-like requests;
# the PerimeterX 403 is only triggered by headless-browser signals.
# ---------------------------------------------------------------------------
_BROWSER_HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}

_SSR_PATTERN = re.compile(r"window\.__SSR_HYDRATED_CONTEXT__\s*=\s*(.+)")


def _extract_poi(html: str) -> tuple[list[dict[str, Any]], int]:
    """Parse ``window.__SSR_HYDRATED_CONTEXT__`` from the page HTML.

    Returns ``(poi_list, total)`` where ``total`` is the city-level count
    reported by Madlan (used to decide when to stop paginating).
    """
    m = _SSR_PATTERN.search(html)
    if not m:
        return [], 0

    raw = m.group(1).rstrip(";")
    # Replace JS-only literals that break json.loads
    raw = re.sub(r"\bundefined\b", "null", raw)
    raw = re.sub(r"\bInfinity\b", "999999999", raw)
    raw = re.sub(r"\bNaN\b", "null", raw)

    # The line may contain multiple window.X = ... assignments concatenated;
    # find the boundary of the first JSON object by counting braces.
    depth = 0
    end_pos = 0
    for i, ch in enumerate(raw):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end_pos = i + 1
                break

    if not end_pos:
        return [], 0

    try:
        data = json.loads(raw[:end_pos])
    except json.JSONDecodeError:
        return [], 0

    try:
        spoi = (
            data["reduxInitialState"]["domainData"]["searchList"]["data"]["searchPoiV2"]
        )
        poi: list[dict[str, Any]] = spoi.get("poi") or []
        total: int = spoi.get("total") or 0
        return poi, total
    except (KeyError, TypeError):
        return [], 0


def _normalise_poi(item: dict[str, Any], city_slug: str) -> dict[str, Any]:
    """Flatten a raw ``poi`` item into the canonical record shape."""
    addr_details = item.get("addressDetails") or {}
    images = item.get("images") or []

    return {
        "listing_id": item.get("id"),
        "listing_url": (
            f"https://www.madlan.co.il/listing/{item['id']}"
            if item.get("id")
            else None
        ),
        "address": item.get("address"),
        "city": addr_details.get("city"),
        "neighbourhood": addr_details.get("neighbourhood"),
        "street_name": addr_details.get("streetName"),
        "street_number": addr_details.get("streetNumber"),
        "district": addr_details.get("district"),
        "lat": (item.get("locationPoint") or {}).get("lat"),
        "lng": (item.get("locationPoint") or {}).get("lng"),
        "price": item.get("price"),
        "rooms": item.get("beds"),
        "floor": item.get("floor"),
        "area_sqm": item.get("area"),
        "baths": item.get("baths"),
        "building_year": item.get("buildingYear"),
        "building_class": item.get("buildingClass"),
        "general_condition": item.get("generalCondition"),
        "deal_type": item.get("dealType"),
        "poi_type": item.get("type"),
        "first_time_seen": item.get("firstTimeSeen"),
        "last_updated": item.get("lastUpdated"),
        "image_urls": [
            f"https://images2.madlan.co.il/{img['imageUrl']}"
            for img in images
            if img.get("imageUrl")
        ],
        "city_slug": city_slug,
        "scraped_at": datetime.now(UTC).isoformat(),
    }


def _content_hash(payload: dict[str, Any]) -> str:
    key = {
        "listing_id": payload.get("listing_id"),
        "price": payload.get("price"),
        "address": payload.get("address"),
    }
    canonical = json.dumps(key, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()


class MadlanScraper(BaseScraper):
    """HTTP-based scraper for madlan.co.il for-sale listings.

    Fetches the SSR HTML of each city's for-sale page with plain ``httpx``
    requests and extracts listing data from the ``window.__SSR_HYDRATED_CONTEXT__``
    JSON blob embedded in the page.  No browser automation is required, which
    bypasses PerimeterX bot-detection entirely.
    """

    source_name: ClassVar[str] = "madlan_for_sale"
    source_url: ClassVar[str] = "https://www.madlan.co.il/for-sale/ישראל"
    retrieval_method: ClassVar[RetrievalMethod] = RetrievalMethod.HTTP_GET

    def __init__(self, scraper_settings: Settings = settings) -> None:
        super().__init__(scraper_settings)

    async def fetch(self) -> ScrapeResult:
        """Scrape all cities concurrently and return collected records."""
        all_records: list[dict[str, Any]] = []
        city_errors: list[str] = []
        sem = asyncio.Semaphore(self.settings.MADLAN_CONCURRENCY)

        async with httpx.AsyncClient(
            headers=_BROWSER_HEADERS,
            timeout=self.settings.MADLAN_PAGE_TIMEOUT_MS / 1000,
            follow_redirects=True,
        ) as client:

            async def scrape_city(city_slug: str) -> None:
                async with sem:
                    try:
                        city_records = await self._scrape_city(client, city_slug)
                        all_records.extend(city_records)
                        await self._logger.ainfo(
                            "City scraped",
                            city=city_slug,
                            records=len(city_records),
                        )
                    except asyncio.CancelledError:
                        await self._logger.awarning(
                            "Run cancelled during city", city=city_slug
                        )
                        raise
                    except Exception as exc:
                        city_errors.append(f"{city_slug}: {exc}")
                        await self._logger.awarning(
                            "City scrape failed — skipping",
                            city=city_slug,
                            error=str(exc),
                        )

            await asyncio.gather(
                *[scrape_city(slug) for slug in CITY_SLUGS],
                return_exceptions=False,
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

    async def _scrape_city(
        self, client: httpx.AsyncClient, city_slug: str
    ) -> list[dict[str, Any]]:
        """Fetch all pages for a single city and return normalised records."""
        records: list[dict[str, Any]] = []
        seen_ids: set[str] = set()

        for page_num in range(1, self.settings.MADLAN_MAX_PAGES_PER_CITY + 1):
            base_url = FOR_SALE_URL_TEMPLATE.format(city_slug=city_slug)
            url = f"{base_url}?page={page_num}" if page_num > 1 else base_url

            response = await client.get(url)
            if response.status_code == 403:
                await self._logger.awarning(
                    "Bot-detection 403 — skipping city",
                    city=city_slug,
                    page=page_num,
                    url=url,
                )
                break
            response.raise_for_status()

            poi, total = _extract_poi(response.text)

            await self._logger.adebug(
                "Page fetched",
                city=city_slug,
                page=page_num,
                poi_on_page=len(poi),
                total=total,
            )

            if not poi:
                break

            for item in poi:
                listing_id = item.get("id")
                if listing_id and listing_id in seen_ids:
                    continue
                if listing_id:
                    seen_ids.add(listing_id)

                payload = _normalise_poi(item, city_slug)
                records.append(
                    {
                        "raw_payload": payload,
                        "content_hash": _content_hash(payload),
                    }
                )

            # Stop when we've collected everything or reached the last page
            if total and len(records) >= total:
                break
            if len(poi) < 50:
                # Last page returned fewer than a full page of results
                break

            await asyncio.sleep(self.settings.MADLAN_REQUEST_DELAY_S)

        return records
