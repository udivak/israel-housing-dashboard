import io
import zipfile
from typing import Any, ClassVar, Optional

import httpx
import openpyxl

from app.core.config import Settings, settings
from app.models.records import RetrievalMethod
from app.scrapers._utils import content_hash, normalize_row
from app.scrapers.base import BaseScraper, ScrapeResult


class OdataILScraper(BaseScraper):
    """Downloads real estate transaction records from odata.org.il as a ZIP/XLSX.

    Retrieval method: zip_download — fetches a ZIP archive containing one or more
    XLSX files and parses each sheet row into a flat dict.

    Runtime override: pass overrides={"resource_id": "<uuid>"} to target a specific
    dataset resource without changing the global settings.
    """

    source_name: ClassVar[str] = "odata_il_nadlan"
    retrieval_method: ClassVar[RetrievalMethod] = RetrievalMethod.ZIP_DOWNLOAD

    def __init__(
        self,
        scraper_settings: Settings = settings,
        overrides: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(scraper_settings)
        resource_id = (overrides or {}).get("resource_id") or scraper_settings.ODATA_IL_RESOURCE_ID
        base = scraper_settings.ODATA_IL_BASE_URL.rstrip("/")
        self.source_url = (
            f"{base}/dataset/84f2bc2d-87a0-474e-a3ea-63d7bb9b5447"
            f"/resource/{resource_id}/download/.zip"
        )

    @property
    def _source_url(self) -> str:
        return self.source_url

    async def fetch(self) -> ScrapeResult:
        timeout = httpx.Timeout(
            connect=10.0,
            read=float(self.settings.ODATA_IL_DOWNLOAD_TIMEOUT_S),
            write=10.0,
            pool=10.0,
        )
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(self.source_url)
            response.raise_for_status()
            zip_bytes = response.content

        buffer = io.BytesIO(zip_bytes)
        records: list[dict[str, Any]] = []

        with zipfile.ZipFile(buffer) as zf:
            xlsx_names = [n for n in zf.namelist() if n.lower().endswith(".xlsx")]
            if not xlsx_names:
                return ScrapeResult(
                    source_name=self.source_name,
                    records=[],
                    status="empty",
                    error="No XLSX file found in ZIP archive",
                )

            for xlsx_name in xlsx_names:
                with zf.open(xlsx_name) as xlsx_file:
                    wb = openpyxl.load_workbook(
                        io.BytesIO(xlsx_file.read()), read_only=True, data_only=True
                    )
                    ws = wb.active
                    row_iter = ws.iter_rows(values_only=True)
                    headers = next(row_iter, None)
                    if not headers:
                        wb.close()
                        continue
                    for row in row_iter:
                        raw = dict(zip(headers, row))
                        normalized = normalize_row(raw)
                        records.append(
                            {
                                "raw_payload": normalized,
                                "content_hash": content_hash(normalized),
                            }
                        )
                    wb.close()

        if not records:
            return ScrapeResult(source_name=self.source_name, records=[], status="empty")

        return ScrapeResult(source_name=self.source_name, records=records, status="success")
