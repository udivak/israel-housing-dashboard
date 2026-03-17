import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar, Literal, Optional

import structlog

from app.core.config import Settings, settings
from app.models.records import RetrievalMethod


@dataclass
class ScrapeResult:
    source_name: str
    records: list[dict[str, Any]]
    status: Literal["success", "failed", "empty"]
    error: Optional[str] = None
    duration_ms: int = 0
    records_count: int = 0


@dataclass
class RetryConfig:
    max_attempts: int = 3
    wait_min_s: float = 1.0
    wait_max_s: float = 10.0
    multiplier: float = 2.0


class BaseScraper(ABC):
    source_name: ClassVar[str]
    source_url: ClassVar[str]
    retrieval_method: ClassVar[RetrievalMethod]

    def __init__(self, scraper_settings: Settings = settings) -> None:
        self.settings = scraper_settings
        self._logger = structlog.get_logger(self.__class__.__name__).bind(
            source_name=self.source_name
        )

    @abstractmethod
    async def fetch(self) -> ScrapeResult:
        """Perform the actual data retrieval. Override in subclasses."""

    async def run(self) -> ScrapeResult:
        """Public entry point: timing + structured logging + retry around fetch()."""
        start = time.monotonic()
        await self._logger.ainfo("Scraper run starting")
        try:
            result = await self._fetch_with_retry()
            result.duration_ms = int((time.monotonic() - start) * 1000)
            result.records_count = len(result.records)
            await self._logger.ainfo(
                "Scraper run finished",
                status=result.status,
                records=result.records_count,
                duration_ms=result.duration_ms,
            )
            return result
        except Exception as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            await self._logger.aerror("Scraper run failed", error=str(exc), duration_ms=duration_ms)
            return ScrapeResult(
                source_name=self.source_name,
                records=[],
                status="failed",
                error=str(exc),
                duration_ms=duration_ms,
            )

    async def _fetch_with_retry(self) -> ScrapeResult:
        attempt = 0
        last_exc: Optional[Exception] = None
        max_attempts = self.settings.SCRAPER_MAX_RETRIES
        wait_s = self.settings.SCRAPER_RETRY_WAIT_S

        while attempt < max_attempts:
            try:
                return await self.fetch()
            except Exception as exc:
                attempt += 1
                last_exc = exc
                if attempt < max_attempts:
                    import asyncio

                    delay = wait_s * (2 ** (attempt - 1))
                    await self._logger.awarning(
                        "Fetch attempt failed, retrying",
                        attempt=attempt,
                        delay_s=delay,
                        error=str(exc),
                    )
                    await asyncio.sleep(delay)

        raise last_exc  # type: ignore[misc]
