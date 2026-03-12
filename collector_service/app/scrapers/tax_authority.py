import asyncio
from collections.abc import Awaitable, Callable
from typing import Any, ClassVar, Optional

import httpx

from app.core.config import Settings, settings
from app.models.records import RetrievalMethod
from app.scrapers._utils import content_hash, normalize_row
from app.scrapers.base import BaseScraper, ScrapeResult

# Major Israeli cities with Hebrew names used for Govmap autocomplete.
# The list covers ~90 % of the country's real estate transaction volume.
GOVMAP_CITIES: list[str] = [
    "תל אביב",
    "ירושלים",
    "חיפה",
    "ראשון לציון",
    "פתח תקווה",
    "אשדוד",
    "נתניה",
    "באר שבע",
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
]

_AUTOCOMPLETE_URL_PATH = "search-service/autocomplete"
_DEALS_RADIUS_URL_PATH = "real-estate/deals/{lon},{lat}/{radius}"
_STREET_DEALS_URL_PATH = "real-estate/street-deals/{polygon_id}"


class TaxAuthorityScraper(BaseScraper):
    """Israel Tax Authority real estate transactions via the public Govmap REST API.

    Flow per city:
      1. POST /search-service/autocomplete  →  ITM coordinates (lon, lat)
      2. GET  /real-estate/deals/{lon},{lat}/{radius_m}  →  list of polygon metadata
      3. GET  /real-estate/street-deals/{polygon_id}?limit=N&offset=P&dealType=D
             (paginated)  →  actual deal records
    No authentication is required; Govmap is a public government API.
    """

    source_name: ClassVar[str] = "tax_authority_nadlan"
    source_url: ClassVar[str] = "https://www.govmap.gov.il/api"
    retrieval_method: ClassVar[RetrievalMethod] = RetrievalMethod.HTTP_GET

    def __init__(
        self,
        scraper_settings: Settings = settings,
        flush_callback: Optional[Callable[[list[dict[str, Any]]], Awaitable[None]]] = None,
    ) -> None:
        super().__init__(scraper_settings)
        self._base = scraper_settings.GOVMAP_BASE_URL.rstrip("/")
        self._flush_callback = flush_callback

    # ------------------------------------------------------------------
    # Public entry point (called by BaseScraper.run -> _fetch_with_retry)
    # ------------------------------------------------------------------

    async def fetch(self) -> ScrapeResult:
        timeout = httpx.Timeout(
            connect=10.0,
            read=float(self.settings.GOVMAP_READ_TIMEOUT_S),
            write=10.0,
            pool=10.0,
        )
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        }

        records: list[dict[str, Any]] = []
        seen_hashes: set[str] = set()

        async with httpx.AsyncClient(
            timeout=timeout, headers=headers, follow_redirects=True
        ) as client:
            for city in GOVMAP_CITIES:
                try:
                    city_records = await self._collect_city(client, city, seen_hashes)
                    records.extend(city_records)
                    await self._logger.ainfo(
                        "City collected",
                        city=city,
                        new_records=len(city_records),
                        total_so_far=len(records),
                    )
                    if city_records and self._flush_callback is not None:
                        await self._flush_callback(city_records)
                except Exception as exc:
                    await self._logger.awarning(
                        "City collection failed, skipping",
                        city=city,
                        error=str(exc),
                    )

        if not records:
            return ScrapeResult(
                source_name=self.source_name,
                records=[],
                status="empty",
                error="No records returned from Govmap for any city",
            )

        return ScrapeResult(
            source_name=self.source_name,
            records=records,
            status="success",
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _collect_city(
        self,
        client: httpx.AsyncClient,
        city_name: str,
        seen_hashes: set[str],
    ) -> list[dict[str, Any]]:
        """Run the 3-step Govmap flow for a single city."""
        point = await self._autocomplete(client, city_name)
        if point is None:
            await self._logger.awarning("Autocomplete returned no coordinates", city=city_name)
            return []

        lon, lat = point
        polygons = await self._get_polygons(client, lon, lat)
        if not polygons:
            await self._logger.awarning("No polygons found near city", city=city_name)
            return []

        records: list[dict[str, Any]] = []
        max_polygons = self.settings.GOVMAP_MAX_POLYGONS_PER_CITY

        for polygon_meta in polygons[:max_polygons]:
            polygon_id = polygon_meta.get("polygon_id") or polygon_meta.get("polygonId")
            if not polygon_id:
                continue

            polygon_records = await self._get_street_deals(
                client, str(polygon_id), seen_hashes
            )
            records.extend(polygon_records)

            if self.settings.GOVMAP_REQUEST_DELAY_S > 0:
                await asyncio.sleep(self.settings.GOVMAP_REQUEST_DELAY_S)

        return records

    async def _autocomplete(
        self, client: httpx.AsyncClient, search_text: str
    ) -> tuple[float, float] | None:
        """Return (longitude, latitude) in ITM coordinates for a city name."""
        url = f"{self._base}/{_AUTOCOMPLETE_URL_PATH}"
        payload = {
            "searchText": search_text,
            "language": "he",
            "isAccurate": False,
            "maxResults": 1,
        }
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()

        results = data.get("results") if isinstance(data, dict) else None
        if not results:
            return None

        first = results[0]
        shape = first.get("shape", "")
        if shape and shape.startswith("POINT("):
            # Format: "POINT(lon lat)"
            coords_str = shape[6:-1]
            parts = coords_str.split()
            if len(parts) == 2:
                try:
                    return float(parts[0]), float(parts[1])
                except ValueError:
                    pass

        # Fallback: some responses embed x/y directly
        x = first.get("x") or first.get("lon")
        y = first.get("y") or first.get("lat")
        if x and y:
            try:
                return float(x), float(y)
            except ValueError:
                pass

        return None

    async def _get_polygons(
        self, client: httpx.AsyncClient, lon: float, lat: float
    ) -> list[dict[str, Any]]:
        """Return polygon metadata list near (lon, lat)."""
        radius = self.settings.GOVMAP_RADIUS_M
        url = f"{self._base}/{_DEALS_RADIUS_URL_PATH.format(lon=lon, lat=lat, radius=radius)}"
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, list) else []

    async def _get_street_deals(
        self,
        client: httpx.AsyncClient,
        polygon_id: str,
        seen_hashes: set[str],
    ) -> list[dict[str, Any]]:
        """Fetch all pages of street deals for a polygon and return normalised records."""
        url = f"{self._base}/{_STREET_DEALS_URL_PATH.format(polygon_id=polygon_id)}"
        limit = self.settings.GOVMAP_PAGE_LIMIT
        deal_type = self.settings.GOVMAP_DEAL_TYPE

        records: list[dict[str, Any]] = []
        offset = 0

        while True:
            params: dict[str, Any] = {
                "limit": limit,
                "offset": offset,
                "dealType": deal_type,
            }
            response = await client.get(url, params=params)

            # 404 means polygon has no deals — treat as empty, not an error
            if response.status_code == 404:
                break
            response.raise_for_status()

            data = response.json()
            deal_list: list[dict[str, Any]] = []
            if isinstance(data, dict):
                deal_list = data.get("data") or []
            elif isinstance(data, list):
                deal_list = data

            if not deal_list:
                break

            for raw_deal in deal_list:
                normalized = normalize_row(raw_deal)
                # Add provenance metadata
                normalized["polygon_id"] = normalized.get("polygon_id") or polygon_id
                normalized["source"] = "govmap"
                ch = content_hash(normalized)
                if ch not in seen_hashes:
                    seen_hashes.add(ch)
                    records.append({"raw_payload": normalized, "content_hash": ch})

            # Stop paginating if we received a partial page
            if len(deal_list) < limit:
                break

            offset += limit
            if self.settings.GOVMAP_REQUEST_DELAY_S > 0:
                await asyncio.sleep(self.settings.GOVMAP_REQUEST_DELAY_S)

        return records
