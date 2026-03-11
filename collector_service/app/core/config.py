from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SERVICE_NAME: str = "collector_service"
    APP_ENV: Literal["development", "staging", "production"] = "development"
    LOG_LEVEL: str = "INFO"
    API_V1_PREFIX: str = "/api/v1"

    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "israel_housing"
    MONGODB_CONNECT_TIMEOUT_MS: int = 5000
    MONGODB_SERVER_SELECTION_TIMEOUT_MS: int = 5000

    SCRAPER_REQUEST_TIMEOUT_S: int = 30
    SCRAPER_MAX_RETRIES: int = 3
    SCRAPER_RETRY_WAIT_S: float = 2.0

    ODATA_IL_RESOURCE_ID: str = "5eb859da-6236-4b67-bcd1-ec4b90875739"
    ODATA_IL_BASE_URL: str = "https://www.odata.org.il"

    # Madlan scraper
    MADLAN_BASE_URL: str = "https://www.madlan.co.il"
    MADLAN_HEADLESS: bool = True
    MADLAN_MAX_PAGES_PER_CITY: int = 10
    MADLAN_CONCURRENCY: int = 1
    MADLAN_PAGE_TIMEOUT_MS: int = 30000
    MADLAN_REQUEST_DELAY_S: float = 2.0
    MADLAN_DETAIL_CRAWL_ENABLED: bool = True
    MADLAN_USER_AGENT: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
