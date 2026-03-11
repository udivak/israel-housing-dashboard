from typing import ClassVar

from app.core.config import Settings, settings
from app.models.records import RetrievalMethod
from app.scrapers.base import BaseScraper, ScrapeResult


class TaxAuthorityScraper(BaseScraper):
    """Israel Tax Authority real estate transactions.

    TODO: Implement real data retrieval once the API endpoint and authentication
    mechanism are confirmed with the Israel Tax Authority open data portal.
    """

    source_name: ClassVar[str] = "tax_authority_nadlan"
    source_url: ClassVar[str] = "https://www.misim.gov.il/mmdlsmk/Default.aspx"
    retrieval_method: ClassVar[RetrievalMethod] = RetrievalMethod.HTTP_GET

    def __init__(self, scraper_settings: Settings = settings) -> None:
        super().__init__(scraper_settings)

    async def fetch(self) -> ScrapeResult:
        # TODO: Implement HTTP scraping / API call to Tax Authority data source.
        # Expected fields: transaction_date, price, address, city, property_type, etc.
        raise NotImplementedError(
            "TaxAuthorityScraper.fetch() is not yet implemented. "
            "See TODO markers in this file for guidance."
        )
