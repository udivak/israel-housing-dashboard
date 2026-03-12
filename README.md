# Israel Housing Dashboard

A data engineering platform that collects, stores, and serves Israeli housing market data from multiple open-data sources.

## Services

| Service | Description | Port |
|---------|-------------|------|
| `collector_service` | Ingests housing data from open-data APIs into MongoDB | `8000` |
| `dashboard_service` | Geospatial API for map layers and GeoJSON features | `8000` |
| `dashboard_app` | Next.js frontend – dashboard, map, search | `3000` |
| `streamlit_app` | Streamlit frontend for testing/QA | `8501` |

---

## הרצה – כל הפקודות

### 1. Backend (dashboard_service)

```bash
cd dashboard_service
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
# ערוך .env: MONGO_URI, DB_NAME
.venv/bin/uvicorn app.main:app --reload --port 8000
```

- **URL:** http://localhost:8000
- **Swagger:** http://localhost:8000/docs
- **דרוש:** MongoDB פעיל (localhost:27017 או Atlas)

### 2. Frontend (dashboard_app)

```bash
cd dashboard_app
npm install
cp .env.example .env.local
# ערוך .env.local: NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

- **URL:** http://localhost:3000
- **מפה:** http://localhost:3000/map

### 3. Streamlit (לבדיקות וטסטים)

```bash
cd streamlit_app
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
# ערוך .env: API_URL=http://localhost:8000
.venv/bin/streamlit run app.py
```

- **URL:** http://localhost:8501

### 4. Collector Service (Docker)

```bash
cd collector_service
cp .env.example .env
docker compose up --build
```

- **API:** http://localhost:8000
- **Swagger:** http://localhost:8000/docs

### 5. MongoDB (Docker)

```bash
docker run -d -p 27017:27017 --name mongodb mongo:latest
```

### 6. הרצה מלאה (2 טרמינלים)

```bash
# טרמינל 1 – Backend
cd dashboard_service && .venv/bin/uvicorn app.main:app --reload --port 8000

# טרמינל 2 – Frontend (Next.js)
cd dashboard_app && npm run dev

# או Streamlit
cd streamlit_app && .venv/bin/streamlit run app.py
```

## מבנה הפרויקט

```
israel-housing-dashboard/
├── collector_service/   # Data collection – scrapers, jobs
├── dashboard_service/   # FastAPI – API גאו-מרחבי
├── dashboard_app/       # Next.js – דשבורד, מפה, חיפוש
├── streamlit_app/       # Streamlit – לבדיקות וטסטים
└── README.md
```

## קישורים

| שירות | URL |
|-------|-----|
| Frontend (Next.js) | http://localhost:3000 |
| Streamlit | http://localhost:8501 |
| Backend API | http://localhost:8000 |
| Swagger | http://localhost:8000/docs |

---

## Collector Service — API Reference

All data endpoints are prefixed with `/api/v1`. Every response shares the same envelope:

```json
{
  "success": true,
  "data": { ... },
  "message": ""
}
```

Errors follow:

```json
{
  "success": false,
  "error_code": "JOB_NOT_FOUND",
  "message": "Job abc123 not found",
  "details": {}
}
```

---

### Health

#### `GET /health`

Liveness probe — returns `200 OK` immediately if the process is alive.

```json
{ "status": "ok" }
```

---

#### `GET /ready`

Readiness probe — pings MongoDB before responding.

**200 OK**
```json
{ "status": "ready" }
```

**503 Service Unavailable**
```json
{ "status": "unavailable", "detail": "MongoDB unreachable" }
```

---

### Collection

#### `POST /api/v1/collect/source/{source_name}` → `202 Accepted`

Triggers a background scrape job for a single named source.

**Path parameter**

| Param | Type | Description |
|-------|------|-------------|
| `source_name` | `string` | Registered source name (e.g. `odata_il_nadlan`) |

**Response**
```json
{
  "success": true,
  "data": {
    "job_id": "6613a2f4e2b4a1c9d0f3e811",
    "message": "Job accepted"
  },
  "message": "Collection job accepted for source: odata_il_nadlan"
}
```

---

#### `POST /api/v1/collect/all` → `202 Accepted`

Triggers a background scrape job for **all active sources** in parallel.

**Response**
```json
{
  "success": true,
  "data": {
    "job_id": "6613a2f4e2b4a1c9d0f3e812",
    "message": "Job accepted"
  },
  "message": "Collection job accepted for all active sources"
}
```

> Use the returned `job_id` with the Jobs endpoints to track progress.

---

### Jobs

#### `GET /api/v1/jobs` — List jobs (paginated)

**Query parameters**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `status` | `string` | — | Filter by status: `pending` `running` `completed` `failed` `partial` |
| `limit` | `integer` | `20` | Max results (1–100) |
| `offset` | `integer` | `0` | Pagination offset |

**Response**
```json
{
  "success": true,
  "data": [
    {
      "id": "6613a2f4e2b4a1c9d0f3e811",
      "source_name": "odata_il_nadlan",
      "status": "completed",
      "created_at": "2025-04-08T10:00:00Z",
      "started_at": "2025-04-08T10:00:01Z",
      "completed_at": "2025-04-08T10:02:14Z",
      "records_inserted": 4820,
      "records_skipped": 132,
      "error_message": null,
      "sub_job_ids": []
    }
  ],
  "message": ""
}
```

---

#### `GET /api/v1/jobs/all` — List all jobs (no pagination)

Returns up to 1000 most recent jobs. Use `/api/v1/jobs` with pagination for production use.

---

#### `GET /api/v1/jobs/{job_id}` — Get single job

**Path parameter**

| Param | Type | Description |
|-------|------|-------------|
| `job_id` | `string` | MongoDB ObjectId of the job |

**200 OK**
```json
{
  "success": true,
  "data": {
    "id": "6613a2f4e2b4a1c9d0f3e811",
    "source_name": "odata_il_nadlan",
    "status": "running",
    "created_at": "2025-04-08T10:00:00Z",
    "started_at": "2025-04-08T10:00:01Z",
    "completed_at": null,
    "records_inserted": 0,
    "records_skipped": 0,
    "error_message": null,
    "sub_job_ids": []
  },
  "message": ""
}
```

**404 Not Found**
```json
{
  "success": false,
  "error_code": "JOB_NOT_FOUND",
  "message": "Job 6613a2f4e2b4a1c9d0f3e811 not found"
}
```

**Job status lifecycle:**
```
pending → running → completed
                 ↘ failed
                 ↘ partial
```

---

### Sources

#### `GET /api/v1/sources` — List registered sources

**Query parameters**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | `integer` | `20` | Max results (1–100) |
| `offset` | `integer` | `0` | Pagination offset |

**Response**
```json
{
  "success": true,
  "data": {
    "sources": [
      {
        "id": "6613a2f4e2b4a1c9d0f3e800",
        "name": "odata_il_nadlan",
        "display_name": "odata.org.il — Real Estate Transactions",
        "description": "ZIP archive of all real estate transactions from odata.org.il",
        "status": "active",
        "source_url": "https://www.odata.org.il",
        "tags": ["transactions", "nadlan"]
      }
    ],
    "total": 3,
    "limit": 20,
    "offset": 0
  },
  "message": ""
}
```

Source statuses: `active` | `planned` | `disabled`

---

#### `GET /api/v1/collections/status` — Latest run summary per source

Returns one status entry per registered source showing the outcome of its most recent scrape job.

**Query parameters**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | `integer` | `20` | Max results (1–100) |
| `offset` | `integer` | `0` | Pagination offset |

**Response**
```json
{
  "success": true,
  "data": [
    {
      "source_name": "odata_il_nadlan",
      "display_name": "odata.org.il — Real Estate Transactions",
      "status": "active",
      "last_job_status": "completed",
      "last_job_id": "6613a2f4e2b4a1c9d0f3e811",
      "last_run_at": "2025-04-08T10:02:14Z",
      "last_records_inserted": 4820
    }
  ],
  "message": ""
}
```

---

## Data Sources

| Name | Status | Description |
|------|--------|-------------|
| `odata_il_nadlan` | ✅ Active | Real estate transactions — odata.org.il (ZIP → CSV) |
| `tax_authority_nadlan` | ✅ Active | Real estate transactions via the Govmap public API (Israel Tax Authority) |
| `cbs_housing` | ✅ Active | Housing price indices and rent stats from the Central Bureau of Statistics |
| `madlan_for_sale` | ✅ Active | Live for-sale listings scraped from madlan.co.il (Playwright headless) |

---

## Architecture

```
collector_service/
└── app/
    ├── api/routes/          # FastAPI routers
    │   ├── health.py        #   GET /health, GET /ready
    │   ├── collect.py       #   POST /api/v1/collect/...
    │   ├── jobs.py          #   GET  /api/v1/jobs/...
    │   └── sources.py       #   GET  /api/v1/sources, /collections/status
    ├── core/                # Config (pydantic-settings), logging, exceptions
    ├── db/
    │   ├── mongo.py         # PyMongo async client + index creation
    │   └── repositories/    # jobs, sources, records, pipeline logs
    ├── models/              # Pydantic models — ScrapeJob, SourceDefinition, StandardResponse
    ├── scrapers/            # BaseScraper ABC + odata_il, madlan, cbs, govmap
    ├── services/            # CollectionService (job lifecycle) + SourceRegistry
    └── main.py              # FastAPI app, lifespan, middleware, CORS
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_ENV` | `development` | `development` \| `staging` \| `production` |
| `LOG_LEVEL` | `INFO` | Python log level |
| `MONGODB_URI` | `mongodb://localhost:27017` | MongoDB connection string |
| `MONGODB_DB_NAME` | `israel_housing` | Target database |
| `SCRAPER_REQUEST_TIMEOUT_S` | `30` | HTTP timeout per request |
| `SCRAPER_MAX_RETRIES` | `3` | Retry attempts on transient failures |
| `SCRAPER_RETRY_WAIT_S` | `2.0` | Wait between retries (seconds) |
| `ODATA_IL_RESOURCE_ID` | — | Resource UUID on odata.org.il |
| `MADLAN_MAX_PAGES_PER_CITY` | `10` | Listing pages to scrape per city |
| `MADLAN_HEADLESS` | `true` | Run Playwright in headless mode |

See `.env.example` for the full list of variables.
