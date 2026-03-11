from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any, ClassVar

from playwright.async_api import BrowserContext, Page, async_playwright

from app.core.config import Settings, settings
from app.models.records import RetrievalMethod
from app.scrapers.base import BaseScraper, ScrapeResult
from app.scrapers.madlan_config import (
    BROWSER_CONTEXT_OPTIONS,
    CITY_SLUGS,
    FOR_SALE_URL_TEMPLATE,
    SELECTORS,
)
from app.scrapers.madlan_parser import (
    build_content_hash,
    extract_listing_card,
    extract_listing_detail,
)


class MadlanScraper(BaseScraper):
    """Playwright-based scraper for madlan.co.il for-sale property listings.

    Crawls each city in CITY_SLUGS, paginates through result pages, and
    optionally deep-crawls each listing's detail page.  Per-city and per-card
    failures are isolated: one bad city / card does not abort the whole run.
    """

    source_name: ClassVar[str] = "madlan_for_sale"
    source_url: ClassVar[str] = "https://www.madlan.co.il/for-sale/ישראל"
    retrieval_method: ClassVar[RetrievalMethod] = RetrievalMethod.BROWSER

    def __init__(self, scraper_settings: Settings = settings) -> None:
        super().__init__(scraper_settings)

    async def fetch(self) -> ScrapeResult:
        """Launch a Chromium browser, iterate over all cities, and return collected records."""
        all_records: list[dict[str, Any]] = []
        city_errors: list[str] = []

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=self.settings.MADLAN_HEADLESS)
            context = await browser.new_context(
                user_agent=self.settings.MADLAN_USER_AGENT,
                **BROWSER_CONTEXT_OPTIONS,
            )
            await self._apply_stealth(context)

            for city_slug in CITY_SLUGS:
                try:
                    city_records = await self._scrape_city(context, city_slug)
                    all_records.extend(city_records)
                    await self._logger.ainfo(
                        "City scraped",
                        city=city_slug,
                        records=len(city_records),
                    )
                except Exception as exc:
                    city_errors.append(f"{city_slug}: {exc}")
                    await self._logger.awarning(
                        "City scrape failed — skipping",
                        city=city_slug,
                        error=str(exc),
                    )

            await browser.close()

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

    # ------------------------------------------------------------------
    # City-level crawl
    # ------------------------------------------------------------------

    async def _scrape_city(
        self, context: BrowserContext, city_slug: str
    ) -> list[dict[str, Any]]:
        """Scrape all paginated result pages for a single city."""
        page = await context.new_page()
        records: list[dict[str, Any]] = []

        try:
            for page_num in range(1, self.settings.MADLAN_MAX_PAGES_PER_CITY + 1):
                url = FOR_SALE_URL_TEMPLATE.format(city_slug=city_slug)
                if page_num > 1:
                    url = f"{url}?page={page_num}"

                await page.goto(
                    url,
                    timeout=self.settings.MADLAN_PAGE_TIMEOUT_MS,
                    wait_until="networkidle",
                )

                await self._logger.adebug(
                    "Page loaded", city=city_slug, page=page_num, url=url
                )

                # Exit early when the site signals no listings exist
                if await page.locator(SELECTORS["no_results"]).count() > 0:
                    await self._logger.adebug(
                        "No results — stopping pagination", city=city_slug, page=page_num
                    )
                    break

                cards = await page.locator(SELECTORS["listing_card"]).all()
                if not cards:
                    await self._logger.adebug(
                        "Empty page — stopping pagination", city=city_slug, page=page_num
                    )
                    break

                page_records = await self._extract_cards(page, cards, city_slug)
                records.extend(page_records)

                await self._logger.adebug(
                    "Page extracted",
                    city=city_slug,
                    page=page_num,
                    cards=len(cards),
                    extracted=len(page_records),
                )

                # Stop if there is no next-page control
                has_next = await page.locator(SELECTORS["next_page"]).count() > 0
                if not has_next:
                    break

                await asyncio.sleep(self.settings.MADLAN_REQUEST_DELAY_S)
        finally:
            await page.close()

        return records

    # ------------------------------------------------------------------
    # Card-level extraction
    # ------------------------------------------------------------------

    async def _extract_cards(
        self,
        page: Page,
        cards: list,
        city_slug: str,
    ) -> list[dict[str, Any]]:
        """Extract and normalise every listing card on the current results page."""
        records: list[dict[str, Any]] = []

        for card in cards:
            try:
                card_html = await card.inner_html()
                data = extract_listing_card(card_html, SELECTORS)
                data["city_slug"] = city_slug
                data["scraped_at"] = datetime.now(UTC).isoformat()

                if self.settings.MADLAN_DETAIL_CRAWL_ENABLED and data.get("listing_url"):
                    detail = await self._fetch_detail(page, data["listing_url"])
                    data.update(detail)

                # Dedup key: use listing_id when available; fall back to
                # price + address so we still deduplicate unlabelled cards.
                hash_key: dict[str, Any] = {
                    "listing_id": data.get("listing_id"),
                    "price": data.get("price"),
                    "address": data.get("address"),
                }
                records.append(
                    {
                        "raw_payload": data,
                        "content_hash": build_content_hash(hash_key),
                    }
                )
            except Exception as exc:
                await self._logger.awarning(
                    "Card extraction failed — skipping",
                    city=city_slug,
                    error=str(exc),
                )

        return records

    # ------------------------------------------------------------------
    # Detail page crawl
    # ------------------------------------------------------------------

    async def _fetch_detail(self, page: Page, listing_url: str) -> dict[str, Any]:
        """Open a listing detail page in a new tab and extract extended fields.

        The tab is always closed in the finally block, even on timeout.
        """
        detail_page = await page.context.new_page()
        try:
            await detail_page.goto(
                listing_url,
                timeout=self.settings.MADLAN_PAGE_TIMEOUT_MS,
                wait_until="networkidle",
            )
            html = await detail_page.content()
            return extract_listing_detail(html, SELECTORS)
        finally:
            await detail_page.close()
            await asyncio.sleep(self.settings.MADLAN_REQUEST_DELAY_S)

    # ------------------------------------------------------------------
    # Anti-bot helpers
    # ------------------------------------------------------------------

    @staticmethod
    async def _apply_stealth(context: BrowserContext) -> None:
        """Apply playwright-stealth fingerprint masking if the package is installed.

        This is a best-effort enhancement: if playwright-stealth is not in the
        environment the scraper continues normally without it.
        """
        try:
            from playwright_stealth import stealth_async  # type: ignore[import-untyped]

            page = await context.new_page()
            await stealth_async(page)
            await page.close()
        except ImportError:
            pass
