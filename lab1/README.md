# Lab 1 — Israeli Real Estate Data: Ingestion, EDL, and Exploration

**Authors:** Ehud Vaknin (209479088) and Moshe Bercovich (206676850)

---

## Overview

Lab 1 covers the first milestone of the Israel Housing Dashboard project. It consists of two parts that work together:

1. **A data-collection backend** — a FastAPI service that scrapes raw Israeli housing data from two public sources and persists it in MongoDB.
2. **An EDL/EDA notebook** (`EDL_Lab_1.ipynb`) — a Jupyter notebook that loads those raw records, applies full EDL (Extraction, Data Loading) techniques, cleans the data, and produces canonical analytical tables ready for feature engineering and modeling.

---

## Data Sources

| Source | Type | Retrieval method | Granularity |
|---|---|---|---|
| [odata.org.il — Nadlan transactions](https://www.odata.org.il/dataset/84f2bc2d-87a0-474e-a3ea-63d7bb9b5447) | Real-estate transaction records | ZIP download → XLSX parse | Transaction-level |
| [CBS Housing Price Index API](https://api.cbs.gov.il/index/data/price) | Macro price-change indicators | Paginated HTTP GET | Quarterly |

Both sources share a common ingestion envelope schema stored in MongoDB:

```
_id, source_name, source_url, ingested_at, retrieval_method,
raw_payload, parsing_status, content_hash, schema_version, tags, job_id
```

OData records additionally carry a `geometry` field with WGS-84 coordinates.

---

## Repository Structure

```
lab1/
├── app/                        # FastAPI scraping service
│   ├── api/routes/             # REST endpoints: /collect, /records, /jobs
│   ├── db/                     # MongoDB connection + repositories
│   ├── models/                 # Pydantic models (records, jobs, sources, API)
│   ├── scrapers/               # Scraper implementations
│   │   ├── base.py             # BaseScraper ABC + ScrapeResult
│   │   ├── odata_il.py         # ZIP/XLSX scraper for odata.org.il
│   │   ├── cbs.py              # Paginated REST scraper for CBS API
│   │   └── _utils.py           # content_hash, normalize_row helpers
│   ├── services/               # CollectionService, SourceRegistry
│   ├── core/                   # Config, logging, exceptions
│   └── main.py                 # FastAPI app entry point
├── gui/                        # Optional desktop GUI
├── EDL_Lab_1.ipynb             # Main analysis notebook
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Multi-stage Docker image (Python 3.12-slim)
├── docker-compose.yml          # API + MongoDB services
└── .env.local                  # Local environment variable template
```

---

## Backend Service

### Running with Docker Compose

```bash
cp .env.local .env          # fill in any required overrides
docker compose up --build
```

The API is available at `http://localhost:8001`. Interactive docs at `/docs` and `/redoc`.

MongoDB is accessible on the internal Docker network only. To expose it for tools like MongoDB Compass, edit `docker-compose.yml` and add `"27018:27017"` under the `mongo` service ports.

### Running Locally (without Docker)

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

Requires a running MongoDB instance. Set the connection URI in `.env`.

### Key Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Service health check |
| `POST` | `/api/v1/collect` | Trigger a collection job for a source |
| `GET` | `/api/v1/records` | Query stored raw records |
| `GET` | `/api/v1/jobs` | List collection jobs and their status |

### Environment Variables

| Variable | Description |
|---|---|
| `MONGO_URI` | MongoDB connection string |
| `ODATA_IL_BASE_URL` | Base URL for odata.org.il |
| `ODATA_IL_RESOURCE_ID` | UUID of the Nadlan dataset resource |
| `ODATA_IL_DOWNLOAD_TIMEOUT_S` | Download timeout in seconds |

---

## Notebook (`EDL_Lab_1.ipynb`)

The notebook is self-contained and designed to run on Google Colab. Place the two JSON exports in `/content/` before running:

```
israel_housing.raw_records_odata_il_nadlan.json   (250 records)
israel_housing.raw_records._cbs_housing.json      (250 records)
```

### Notebook Sections

| Section | Description |
|---|---|
| 1. Environment setup | Library imports (`numpy`, `pandas`, `matplotlib`, `plotly`) |
| 2. Inspect raw envelope | Print and validate ingestion envelope keys for both sources |
| 3. Flatten raw payloads | `flatten_raw_records()` — unpack `raw_payload` + geometry into a flat DataFrame |
| 4. Schema discovery & profiling | Column dtypes, value counts, cardinality per source |
| 5. Initial data-quality observations | Null rates, unexpected types, anomalies |
| 6. Standardize column names | Snake_case normalization of all field names |
| 7. Type conversion rules | Parse dates, strip currency formatting, cast numerics |
| 8. Normalize Hebrew floor labels | Map textual Hebrew floor names (e.g., "שלוש עשרה") to integer values |
| 9. Canonical transaction table | Build `transactions` DataFrame with typed, clean columns |
| 10. Canonical market indicator table | Build `market_index` DataFrame from CBS records |
| 11. Missing values analysis | Per-column null rates with heatmap visualization |
| 12. Duplicate detection | Hash-based duplicate check on canonical tables |
| 13. Domain validation | Business rule checks (price > 0, valid date range, floor ≥ 0, etc.) |
| 14. Transaction-level EDA | Price distributions, city breakdowns, property-type analysis, geo scatter |
| 15. CBS quarterly trend exploration | Time-series of `percent_change` and `current_base` index |
| 16. Enrich transactions with CBS | Left-join transactions to CBS quarter-level indicators by year/quarter |
| 17. Data quality notes & limitations | Known gaps: missing area (m²), macro-only CBS data, partial Hebrew normalization |
| 18. Export normalized datasets | Write `clean_transactions.csv`, `clean_market_index.csv`, `transactions_enriched.csv` to `outputs/` |
| 19. Summary | High-level recap of what was accomplished |

### Output Files

After running all cells the `outputs/` folder will contain:

| File | Contents |
|---|---|
| `clean_transactions.csv` | Typed, cleaned OData transaction records |
| `clean_market_index.csv` | Typed, cleaned CBS quarterly indicators |
| `transactions_enriched.csv` | Transactions joined with CBS quarter-level fields |

---

## Dependencies

```
fastapi, uvicorn, pymongo[async], pydantic, pydantic-settings,
httpx, structlog, python-dotenv, openpyxl, tenacity, requests, certifi
```

Notebook additionally requires: `numpy`, `pandas`, `matplotlib`, `plotly`

---

## Known Limitations

- The current sample is limited to **250 records per source**, intended for initial profiling only.
- Transaction records lack apartment **area in square meters**, a key real-estate predictor.
- CBS data is national macro-level only; no regional breakdown is available in the current sample.
- Hebrew categorical fields (`property_type`, `DEALNATURE`) need fuller normalization dictionaries.
- The notebook focuses on EDL and preprocessing — modeling and feature engineering are out of scope for this milestone.
