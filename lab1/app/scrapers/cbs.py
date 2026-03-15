import asyncio
from typing import Any, ClassVar, Optional
from urllib.parse import urlencode

import httpx

from app.core.config import Settings, settings
from app.models.records import RetrievalMethod
from app.scrapers._utils import content_hash, normalize_row
from app.scrapers.base import BaseScraper, ScrapeResult


class CBSScraper(BaseScraper):
    """Central Bureau of Statistics (CBS) housing price indices.

    Fetches monthly/bi-monthly time-series from the CBS public price-index API.
    Default series:
      - 40010  מחירי דירות          — all-housing price index (base 1993)
      - 70000  מדד מחירי דירות חדשות — new-construction price index (from 2017)
      - 140235 שכר דירה              — rent sub-index of the CPI

    Retrieval method: http_get — paginated REST API, follows paging.next_url until null.

    Runtime overrides:
      - series_ids: comma-separated series IDs, e.g. "40010,70000"
      - start_period: start date string, e.g. "01-2020"

    SSL note: api.cbs.gov.il terminates with a self-signed intermediate CA that is
    not trusted by Python's default CA bundle. verify=False is intentional here.
    """

    source_name: ClassVar[str] = "cbs_housing"
    source_url: ClassVar[str] = "https://api.cbs.gov.il/index/data/price"
    retrieval_method: ClassVar[RetrievalMethod] = RetrievalMethod.HTTP_GET

    def __init__(
        self,
        scraper_settings: Settings = settings,
        overrides: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(scraper_settings)
        self._base = scraper_settings.CBS_BASE_URL.rstrip("/")
        _ov = overrides or {}
        self._series_ids: str = _ov.get("series_ids") or scraper_settings.CBS_SERIES_IDS
        self._start_period: str = _ov.get("start_period") or scraper_settings.CBS_START_PERIOD

    async def fetch(self) -> ScrapeResult:
        timeout = httpx.Timeout(
            connect=10.0,
            read=float(self.settings.CBS_READ_TIMEOUT_S),
            write=10.0,
            pool=10.0,
        )
        headers = {
            "Accept": "application/json",
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        }

        async with httpx.AsyncClient(
            timeout=timeout,
            headers=headers,
            follow_redirects=True,
            verify=self.settings.CBS_VERIFY_SSL,
        ) as client:
            records = await self._fetch_all_pages(client)

        if not records:
            return ScrapeResult(
                source_name=self.source_name,
                records=[],
                status="empty",
                error="No records returned from CBS price API",
            )

        return ScrapeResult(
            source_name=self.source_name,
            records=records,
            status="success",
        )

    async def _fetch_all_pages(self, client: httpx.AsyncClient) -> list[dict[str, Any]]:
        """Fetch each series independently to avoid the CBS server 500 bug on page 10+."""
        all_records: list[dict[str, Any]] = []
        series_ids = [s.strip() for s in self._series_ids.split(",") if s.strip()]

        for series_id in series_ids:
            try:
                series_records = await self._fetch_series_pages(client, series_id)
                all_records.extend(series_records)
                await self._logger.ainfo(
                    "CBS series collected",
                    series_id=series_id,
                    records=len(series_records),
                    total_so_far=len(all_records),
                )
            except Exception as exc:
                await self._logger.awarning(
                    "CBS series fetch failed, skipping",
                    series_id=series_id,
                    error=str(exc),
                )

        return all_records

    async def _fetch_series_pages(
        self, client: httpx.AsyncClient, series_id: str
    ) -> list[dict[str, Any]]:
        """Follow paging.next_url for a single series until exhausted."""
        _CBS_500_MAX_RETRIES = 3
        _CBS_500_DEEP_PAGE = 8

        params: dict[str, Any] = {
            "id": series_id,
            "format": "json",
            "download": "false",
            "PageSize": self.settings.CBS_PAGE_SIZE,
        }
        if self._start_period:
            params["startPeriod"] = self._start_period

        url: Optional[str] = f"{self._base}?{self._encode_params(params)}"
        records: list[dict[str, Any]] = []
        page = 0

        while url:
            page += 1
            retries = 0
            response = await client.get(url)

            while response.status_code == 500 and retries < _CBS_500_MAX_RETRIES and page < _CBS_500_DEEP_PAGE:
                retries += 1
                delay = 2.0 * retries
                await self._logger.awarning(
                    "CBS API returned 500, retrying",
                    series_id=series_id,
                    page=page,
                    attempt=retries,
                    delay_s=delay,
                )
                await asyncio.sleep(delay)
                response = await client.get(url)

            if response.status_code == 500:
                await self._logger.awarning(
                    "CBS API 500 on pagination — stopping series early",
                    series_id=series_id,
                    page=page,
                    records_collected=len(records),
                )
                break

            response.raise_for_status()
            data: dict[str, Any] = response.json()

            page_records = self._parse_page(data)
            records.extend(page_records)

            paging = data.get("paging") or {}
            url = paging.get("next_url") or None

            if url and self.settings.CBS_REQUEST_DELAY_S > 0:
                await asyncio.sleep(self.settings.CBS_REQUEST_DELAY_S)

        return records

    def _parse_page(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []

        for period_type, series_list in (
            ("month", data.get("month") or []),
            ("quarter", data.get("quarter") or []),
        ):
            for series in series_list:
                series_code = series.get("code")
                series_name = series.get("name")

                for entry in series.get("date") or []:
                    flat = self._flatten_entry(entry, series_code, series_name, period_type)
                    normalized = normalize_row(flat)
                    records.append(
                        {
                            "raw_payload": normalized,
                            "content_hash": content_hash(normalized),
                        }
                    )

        return records

    def _flatten_entry(
        self,
        entry: dict[str, Any],
        series_code: Any,
        series_name: Any,
        period_type: str,
    ) -> dict[str, Any]:
        curr_base = entry.get("currBase") or {}
        prev_base = entry.get("prevBase") or {}

        flat: dict[str, Any] = {
            "series_code": series_code,
            "series_name": series_name,
            "period_type": period_type,
            "year": entry.get("year"),
            "percent": entry.get("percent"),
            "percentYear": entry.get("percentYear"),
            "currBase": curr_base.get("value"),
            "baseDesc": curr_base.get("baseDesc"),
            "prevBase": prev_base.get("value") if prev_base else None,
            "source": "cbs",
        }

        if period_type == "month":
            flat["month"] = entry.get("month")
            flat["monthDesc"] = entry.get("monthDesc")
        else:
            flat["quarter"] = entry.get("quarter")
            flat["quarterDesc"] = entry.get("quarterDesc")

        return flat

    @staticmethod
    def _encode_params(params: dict[str, Any]) -> str:
        return urlencode(params, safe=",")
