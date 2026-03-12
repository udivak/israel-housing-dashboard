# Collector Service

Ingests Israeli housing market data from multiple open-data sources into MongoDB.

## Quick Start

```bash
# Copy env template
cp .env.example .env

# Start the full stack (MongoDB + service)
docker compose up --build
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

## API Overview

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness probe |
| GET | `/ready` | Readiness probe (pings MongoDB) |
| POST | `/api/v1/collect/source/{name}` | Trigger single source collection |
| POST | `/api/v1/collect/all` | Trigger all active sources |
| GET | `/api/v1/jobs/{job_id}` | Poll job status |
| GET | `/api/v1/jobs` | List jobs (`limit`, `offset`, `status`) |
| GET | `/api/v1/sources` | List registered sources |
| GET | `/api/v1/collections/status` | Latest job summary per source |

## Running Locally (without Docker)

```bash
pip install -r requirements.txt

# MongoDB must be running at MONGODB_URI
uvicorn app.main:app --reload --port 8000
```

## Data Sources

| Name | Status | Description |
|------|--------|-------------|
| `odata_il_nadlan` | Active | Real estate transactions from odata.org.il (ZIP → CSV) |
| `tax_authority_nadlan` | Active | Real estate transactions from the Israel Tax Authority via Govmap API |
| `cbs_housing` | Active | Housing price indices and rent statistics from the Central Bureau of Statistics |
| `madlan_for_sale` | Active | Live for-sale property listings scraped from madlan.co.il (Playwright) |

## Architecture

```
app/
├── api/routes/      # FastAPI routers (health, collect, jobs, sources)
├── core/            # Config (pydantic-settings), structured logging, exceptions
├── db/
│   ├── mongo.py     # PyMongo async client + index creation
│   └── repositories/  # Raw records, jobs, sources, pipeline logs
├── models/          # Pydantic models (records, jobs, sources, API envelope)
├── scrapers/        # BaseScraper ABC + concrete implementations
├── services/        # CollectionService (job lifecycle) + SourceRegistry
└── main.py          # FastAPI app with lifespan, middleware, CORS
```

## Environment Variables

See `.env.example` for all available configuration options.

Key variables:

- `MONGODB_URI` — MongoDB connection string
- `MONGODB_DB_NAME` — Database name (default: `israel_housing`)
- `APP_ENV` — `development` | `staging` | `production` (affects log format)
- `SCRAPER_REQUEST_TIMEOUT_S` — HTTP timeout for scrapers
- `SCRAPER_MAX_RETRIES` — Retry attempts on transient failures
