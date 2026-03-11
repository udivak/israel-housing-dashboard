import csv
import hashlib
import io
import json
import zipfile
from typing import Any, ClassVar

import httpx

from app.core.config import Settings, settings
from app.models.records import RetrievalMethod
from app.scrapers.base import BaseScraper, ScrapeResult

COLUMN_MAP: dict[str, str] = {
    "תאריך עסקה": "transaction_date",
    "מחיר": "price",
    "כתובת": "address",
    "עיר": "city",
    "סוג נכס": "property_type",
    "שכונה": "neighborhood",
    "חדרים": "rooms",
    "קומה": "floor",
    "שטח": "area_sqm",
    "גוש": "block",
    "חלקה": "parcel",
}


def _normalize_row(row: dict[str, str]) -> dict[str, Any]:
    return {COLUMN_MAP.get(k, k): v for k, v in row.items()}


def _content_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()


class OdataILScraper(BaseScraper):
    source_name: ClassVar[str] = "odata_il_nadlan"
    retrieval_method: ClassVar[RetrievalMethod] = RetrievalMethod.ZIP_DOWNLOAD

    def __init__(self, scraper_settings: Settings = settings) -> None:
        super().__init__(scraper_settings)
        resource_id = scraper_settings.ODATA_IL_RESOURCE_ID
        base = scraper_settings.ODATA_IL_BASE_URL.rstrip("/")
        self.source_url = (
            f"{base}/dataset/84f2bc2d-87a0-474e-a3ea-63d7bb9b5447"
            f"/resource/{resource_id}/download/.zip"
        )

    # ClassVar must match instance; override via property to keep ClassVar valid.
    @property
    def _source_url(self) -> str:
        return self.source_url

    async def fetch(self) -> ScrapeResult:
        async with httpx.AsyncClient(
            timeout=self.settings.SCRAPER_REQUEST_TIMEOUT_S,
            follow_redirects=True,
        ) as client:
            response = await client.get(self.source_url)
            response.raise_for_status()
            zip_bytes = response.content

        buffer = io.BytesIO(zip_bytes)
        records: list[dict[str, Any]] = []

        with zipfile.ZipFile(buffer) as zf:
            csv_names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
            if not csv_names:
                return ScrapeResult(
                    source_name=self.source_name,
                    records=[],
                    status="empty",
                    error="No CSV file found in ZIP archive",
                )
            with zf.open(csv_names[0]) as csv_file:
                text = csv_file.read().decode("utf-8-sig", errors="replace")
                reader = csv.DictReader(io.StringIO(text))
                for row in reader:
                    normalized = _normalize_row(dict(row))
                    records.append(
                        {
                            "raw_payload": normalized,
                            "content_hash": _content_hash(normalized),
                        }
                    )

        if not records:
            return ScrapeResult(source_name=self.source_name, records=[], status="empty")

        return ScrapeResult(source_name=self.source_name, records=records, status="success")
