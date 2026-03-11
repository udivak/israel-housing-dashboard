from typing import ClassVar

from app.core.config import Settings, settings
from app.models.records import RetrievalMethod
from app.scrapers.base import BaseScraper, ScrapeResult


class CBSScraper(BaseScraper):
    """Central Bureau of Statistics (CBS) housing statistics.

    TODO: Implement data retrieval from the CBS open data API.
    The CBS API is available at https://www.cbs.gov.il/he/pages/default.aspx
    and provides housing price indices and construction statistics.
    """

    source_name: ClassVar[str] = "cbs_housing"
    source_url: ClassVar[str] = "https://www.cbs.gov.il/he/pages/default.aspx"
    retrieval_method: ClassVar[RetrievalMethod] = RetrievalMethod.HTTP_GET

    def __init__(self, scraper_settings: Settings = settings) -> None:
        super().__init__(scraper_settings)

    async def fetch(self) -> ScrapeResult:
        # TODO: Implement CBS API call.
        # Expected datasets: housing price index, building permits, construction completions.
        raise NotImplementedError(
            "CBSScraper.fetch() is not yet implemented. "
            "See TODO markers in this file for guidance."
        )
