from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SERVICE_NAME: str = "collector_service"
    APP_ENV: Literal["development", "staging", "production"] = "development"
    LOG_LEVEL: str = "INFO"
    API_PREFIX: str = "/api"

    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "israel_housing"
    MONGODB_CONNECT_TIMEOUT_MS: int = 5000
    MONGODB_SERVER_SELECTION_TIMEOUT_MS: int = 5000

    SCRAPER_REQUEST_TIMEOUT_S: int = 30
    SCRAPER_MAX_RETRIES: int = 3
    SCRAPER_RETRY_WAIT_S: float = 2.0

    ODATA_IL_RESOURCE_ID: str = "5eb859da-6236-4b67-bcd1-ec4b90875739"
    ODATA_IL_BASE_URL: str = "https://www.odata.org.il"
    ODATA_IL_DOWNLOAD_TIMEOUT_S: int = 120

    # Madlan scraper
    MADLAN_BASE_URL: str = "https://www.madlan.co.il"
    MADLAN_HEADLESS: bool = True
    MADLAN_MAX_PAGES_PER_CITY: int = 10
    MADLAN_CONCURRENCY: int = 1
    MADLAN_PAGE_TIMEOUT_MS: int = 60000
    MADLAN_REQUEST_DELAY_S: float = 2.0
    MADLAN_DETAIL_CRAWL_ENABLED: bool = True
    MADLAN_USER_AGENT: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    # CBS (Central Bureau of Statistics) scraper
    CBS_BASE_URL: str = "https://api.cbs.gov.il/index/data/price"
    CBS_SERIES_IDS: str = "40010,70000,140235"
    CBS_PAGE_SIZE: int = 100
    CBS_REQUEST_DELAY_S: float = 0.3
    CBS_READ_TIMEOUT_S: int = 30
    CBS_VERIFY_SSL: bool = False   # api.cbs.gov.il uses a self-signed intermediate CA
    CBS_START_PERIOD: str = ""     # e.g. "01-2020"; empty = fetch full history

    # Govmap / Tax Authority scraper
    GOVMAP_BASE_URL: str = "https://www.govmap.gov.il/api"
    GOVMAP_DEAL_TYPE: int = 2               # 2=resale (yad shniya), 1=new construction
    GOVMAP_RADIUS_M: int = 2000             # polygon search radius per city centre (metres)
    GOVMAP_PAGE_LIMIT: int = 100            # deals per page
    GOVMAP_MAX_POLYGONS_PER_CITY: int = 50  # max street polygons queried per city
    GOVMAP_REQUEST_DELAY_S: float = 0.3     # polite delay between polygon requests
    GOVMAP_READ_TIMEOUT_S: int = 60

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
