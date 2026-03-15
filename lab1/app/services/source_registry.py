from typing import Any, Optional, Type

from pymongo.asynchronous.database import AsyncDatabase

from app.core.config import Settings, settings as global_settings
from app.core.exceptions import SourceNotFoundError
from app.core.logging import get_logger
from app.models.source import SourceDefinition, SourceStatus
from app.scrapers.base import BaseScraper
from app.scrapers.cbs import CBSScraper
from app.scrapers.odata_il import OdataILScraper

logger = get_logger(__name__)

_SCRAPER_REGISTRY: dict[str, Type[BaseScraper]] = {
    OdataILScraper.source_name: OdataILScraper,
    CBSScraper.source_name: CBSScraper,
}

DEFAULT_SOURCES: list[SourceDefinition] = [
    SourceDefinition(
        name="odata_il_nadlan",
        display_name="odata.org.il — Real Estate Transactions",
        description=(
            "Real estate transaction data from the Israeli open data portal. "
            "Retrieval: ZIP download containing XLSX spreadsheet, parsed with openpyxl."
        ),
        status=SourceStatus.ACTIVE,
        source_url=(
            "https://www.odata.org.il/dataset/84f2bc2d-87a0-474e-a3ea-63d7bb9b5447"
            "/resource/5eb859da-6236-4b67-bcd1-ec4b90875739/download/.zip"
        ),
        tags=["real-estate", "transactions", "zip", "xlsx"],
    ),
    SourceDefinition(
        name="cbs_housing",
        display_name="CBS Housing Price Indices",
        description=(
            "Housing price indices and rent statistics from the Central Bureau of Statistics. "
            "Retrieval: paginated HTTP GET REST API."
        ),
        status=SourceStatus.ACTIVE,
        source_url="https://api.cbs.gov.il/index/data/price",
        tags=["housing", "statistics", "cbs", "price-index", "rest-api"],
    ),
]


class SourceRegistry:
    def __init__(self, db: AsyncDatabase, scraper_settings: Settings = global_settings) -> None:
        self._db = db
        self._settings = scraper_settings
        self._col = db["source_registry"]

    async def seed_default_sources(self) -> None:
        for source in DEFAULT_SOURCES:
            doc = source.model_dump(exclude={"id"})
            await self._col.update_one(
                {"name": doc["name"]},
                {"$setOnInsert": doc},
                upsert=True,
            )
        await logger.ainfo("Default sources seeded", count=len(DEFAULT_SOURCES))

    def _normalize(self, name: str) -> str:
        return name.replace("-", "_")

    async def get_scraper(
        self,
        source_name: str,
        overrides: Optional[dict[str, Any]] = None,
    ) -> BaseScraper:
        normalized = self._normalize(source_name)
        scraper_class = _SCRAPER_REGISTRY.get(normalized)
        if scraper_class is None:
            raise SourceNotFoundError(source_name)
        return scraper_class(self._settings, overrides or {})

    def list_active_source_names(self) -> list[str]:
        return [s.name for s in DEFAULT_SOURCES if s.status == SourceStatus.ACTIVE]
