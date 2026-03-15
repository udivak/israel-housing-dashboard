from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SERVICE_NAME: str = "lab1_api"
    APP_ENV: Literal["development", "staging", "production"] = "development"
    LOG_LEVEL: str = "INFO"
    API_PREFIX: str = "/api"

    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "lab1_housing"
    MONGODB_CONNECT_TIMEOUT_MS: int = 5000
    MONGODB_SERVER_SELECTION_TIMEOUT_MS: int = 5000

    SCRAPER_REQUEST_TIMEOUT_S: int = 30
    SCRAPER_MAX_RETRIES: int = 3
    SCRAPER_RETRY_WAIT_S: float = 2.0

    ODATA_IL_RESOURCE_ID: str = "5eb859da-6236-4b67-bcd1-ec4b90875739"
    ODATA_IL_BASE_URL: str = "https://www.odata.org.il"
    ODATA_IL_DOWNLOAD_TIMEOUT_S: int = 120

    CBS_BASE_URL: str = "https://api.cbs.gov.il/index/data/price"
    CBS_SERIES_IDS: str = "40010,70000,140235"
    CBS_PAGE_SIZE: int = 100
    CBS_REQUEST_DELAY_S: float = 0.3
    CBS_READ_TIMEOUT_S: int = 30
    CBS_VERIFY_SSL: bool = False
    CBS_START_PERIOD: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
