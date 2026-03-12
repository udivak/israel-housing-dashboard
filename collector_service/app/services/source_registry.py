from typing import Optional, Type

from pymongo.asynchronous.database import AsyncDatabase

from app.core.config import Settings, settings as global_settings
from app.core.exceptions import SourceNotFoundError
from app.core.logging import get_logger
from app.db.repositories.sources import SourcesRepository
from app.models.source import SourceDefinition, SourceStatus
from app.scrapers.base import BaseScraper
from app.scrapers.cbs import CBSScraper
from app.scrapers.madlan import MadlanScraper
from app.scrapers.odata_il import OdataILScraper
from app.scrapers.tax_authority import TaxAuthorityScraper

logger = get_logger(__name__)

_SCRAPER_REGISTRY: dict[str, Type[BaseScraper]] = {
    OdataILScraper.source_name: OdataILScraper,
    TaxAuthorityScraper.source_name: TaxAuthorityScraper,
    CBSScraper.source_name: CBSScraper,
    MadlanScraper.source_name: MadlanScraper,
}

DEFAULT_SOURCES: list[SourceDefinition] = [
    SourceDefinition(
        name="odata_il_nadlan",
        display_name="odata.org.il — Real Estate Transactions",
        description="Real estate transaction data from the Israeli open data portal",
        status=SourceStatus.ACTIVE,
        source_url=(
            "https://www.odata.org.il/dataset/84f2bc2d-87a0-474e-a3ea-63d7bb9b5447"
            "/resource/5eb859da-6236-4b67-bcd1-ec4b90875739/download/.zip"
        ),
        tags=["real-estate", "transactions"],
    ),
    SourceDefinition(
        name="tax_authority_nadlan",
        display_name="Israel Tax Authority Transactions",
        description="Real estate transaction data from the Israeli Tax Authority via Govmap API",
        status=SourceStatus.ACTIVE,
        source_url="https://www.govmap.gov.il/api",
        tags=["real-estate", "transactions", "tax-authority"],
    ),
    SourceDefinition(
        name="cbs_housing",
        display_name="CBS Housing Statistics",
        description="Housing price indices and rent statistics from the Central Bureau of Statistics",
        status=SourceStatus.ACTIVE,
        source_url="https://api.cbs.gov.il/index/data/price",
        tags=["housing", "statistics", "cbs", "price-index"],
    ),
    SourceDefinition(
        name="madlan_for_sale",
        display_name="Madlan — For Sale Listings",
        description="Live for-sale property listings scraped from madlan.co.il",
        status=SourceStatus.ACTIVE,
        source_url="https://www.madlan.co.il/for-sale/ישראל",
        tags=["real-estate", "listings", "madlan", "for-sale"],
    ),
]


class SourceRegistry:
    def __init__(self, db: AsyncDatabase, scraper_settings: Settings = global_settings) -> None:
        self._repo = SourcesRepository(db)
        self._settings = scraper_settings

    async def seed_default_sources(self) -> None:
        for source in DEFAULT_SOURCES:
            await self._repo.upsert(source.model_dump(exclude={"id"}))
        await logger.ainfo("Default sources seeded", count=len(DEFAULT_SOURCES))

    def _normalize_source_name(self, name: str) -> str:
        """Allow URL-friendly hyphenated names to match underscored registry names."""
        return name.replace("-", "_")

    async def get_scraper(self, source_name: str) -> BaseScraper:
        normalized = self._normalize_source_name(source_name)

        # Guard: refuse to run scrapers for sources still in PLANNED status.
        # This surfaces a clean 501 instead of burning retry budget on a stub.
        source_doc = await self._repo.get_by_name(normalized)
        if source_doc is not None and source_doc.get("status") == SourceStatus.PLANNED:
            raise NotImplementedError(
                f"Source '{source_name}' is in PLANNED status and has no active implementation yet."
            )

        scraper_class = _SCRAPER_REGISTRY.get(normalized)
        if scraper_class is None:
            if source_doc is None:
                raise SourceNotFoundError(source_name)
            raise NotImplementedError(
                f"Source '{source_name}' is registered but has no scraper implementation yet."
            )
        return scraper_class(self._settings)

    async def list_sources(self, limit: int = 100, offset: int = 0) -> list[dict]:
        return await self._repo.list_sources(limit=limit, offset=offset)

    async def count_sources(self) -> int:
        return await self._repo.count()

    def list_active_source_names(self) -> list[str]:
        return [
            s.name for s in DEFAULT_SOURCES if s.status == SourceStatus.ACTIVE
        ]
