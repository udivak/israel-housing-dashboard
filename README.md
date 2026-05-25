# Israel Housing Dashboard

End-to-end platform for collecting, processing, analyzing, and predicting prices in the Israeli real-estate market. A microservices stack orchestrated by `docker compose`, with an interactive dashboard, a zoom-aware heat map, and seven trained ML models.

---

## Architecture

```
                                             ┌───────────────────────────────┐
                                             │  User (browser)               │
                                             │  http://localhost:3000        │
                                             └───────────────┬───────────────┘
                                                             │
                            ┌────────────────────────────────▼─────────────────────────────────┐
                            │  dashboard_app  (Next.js 16 + React 19 + MapLibre + deck.gl)     │
                            │  /  /map  /stats  /property/[id]  /ai  /settings                 │
                            └────────────────────────────────┬─────────────────────────────────┘
                                                             │  /api/v1/*
                                                             ▼
              ┌──────────────────────────────────────────────────────────────────────────────┐
              │  dashboard_service  (FastAPI · :8000)  ←  API gateway                        │
              │   /map/data           clusters/points by zoom (H3)                           │
              │   /properties/*       search · autocomplete · detail · similar               │
              │   /stats/*            summary · timeseries · by-region · distribution …      │
              │   /predict[/compare]  proxy + model selection + comparison                   │
              └──────┬──────────────────────────────────┬────────────────────────────┬───────┘
                     │ Motor (async Mongo)              │ httpx                      │
                     ▼                                  ▼                            │
        ┌──────────────────────────┐       ┌────────────────────────────────┐        │
        │  MongoDB (cloud / local) │       │  prediction_service (:8002)    │        │
        │   raw_records            │       │   FastAPI + LRU cache          │        │
        │   features_enriched ──┐  │       │   /models /predict /compare    │        │
        │     2dsphere idx      │  │       │                                │        │
        │     h3_r5 / r7 / r8   │  │       │   artifacts/  (bind-mount RO)  │        │
        │     text idx          │  │       │     moses/lightgbm_v1/         │        │
        └──────────────────────────┘       │     moses/stacked_v2/  (...)   │        │
                     ▲                     └────────────────────────────────┘        │
                     │ ETL / scrapers                                                │
                     │                                                               │
        ┌────────────┴───────────┐    ┌───────────────────────────────┐              │
        │  pre_processing        │    │  collector_service  (:8001)   │ ◄────────────┘
        │  (profile=batch)       │    │   FastAPI + Playwright        │
        │   profiler             │    │   sources:                    │
        │   geom backfill        │    │     odata.org.il              │
        │   normalize            │    │     Govmap (rashut)           │
        │   OSM features         │    │     CBS                       │
        │   temporal+macro       │    │     Madlan                    │
        │   load_to_mongo  ★     │    └───────────────────────────────┘
        └────────────────────────┘
```

`★` `load_to_mongo` is the pipeline that produces the `features_enriched` collection with the H3 indices powering zoom-aware clustering. It's the most important piece of the data side.

---

## Project structure

```
israel-housing-dashboard/
├── docker-compose.yml          ← unified orchestration (default + batch + qa profiles)
├── Makefile                    ← shortcuts for common commands
├── .env.example                ← environment template (copy to .env)
│
├── collector_service/          ← FastAPI · scrapers · raw_records
├── dashboard_service/          ← FastAPI · API gateway · features_enriched + stats
├── dashboard_app/              ← Next.js · map · stats · property · prediction UI
├── prediction_service/         ← FastAPI · multi-model serving · 7 trained models
├── pre_processing/             ← ETL pipelines · OSM · temporal · load_to_mongo
├── streamlit_app/              ← Streamlit QA tools
│
├── docs/                       ← documentation · diagrams · raw_records_mapping · legacy
└── pre_processing/outputs/     ← CSV/XLSX (gitignored)
```

---

## Services — who does what

| Service | Stack | Port | Role |
|---------|-------|------|------|
| `mongo` | MongoDB 7 | 27017 (internal) | Database — local container or Atlas |
| `collector_service` | FastAPI · Playwright | 8001 | Scraping external sources → `raw_records` |
| `pre_processing` | Python · pandas · h3 · geopandas | — | ETL: `raw_records` → `features_enriched` |
| `prediction_service` | FastAPI · LRU model cache | 8002 (internal) | Multi-model ML serving |
| `dashboard_service` | FastAPI · Motor · httpx | 8000 | API gateway — exposed to the frontend |
| `dashboard_app` | Next.js 16 · MapLibre · deck.gl · recharts | 3000 | UI — map · stats · properties · prediction |
| `streamlit_app` | Streamlit | 8501 | Optional QA tool |

---

## Quick start

```bash
# 1. environment template
cp .env.example .env
# edit MONGO_URI to point at Atlas, or keep the default to use the in-container Mongo

# 2. bring the stack up
make up                # = docker compose up --build -d

# 3. (one-time) load features_enriched
make load-mongo        # runs from local Python — works against Atlas too
# or
make preprocess        # runs the full ETL pipeline inside Docker

# 4. open
open http://localhost:3000           # dashboard
open http://localhost:8000/docs      # API Swagger UI
```

Map page looks empty? Most likely you haven't loaded `features_enriched` yet — run `make load-mongo`.

---

## Makefile commands

```bash
make help                  # list every target
make up                    # bring the stack up
make down                  # stop everything
make logs                  # tail logs for all services
make logs-dashboard        # only dashboard_service
make health                # health check across services
make models                # list available prediction models
make champion MODEL=moses/stacked_v2   # switch champion (no rebuild needed)
make preprocess            # batch ETL
make geocode               # upgrade property coordinates to address-level (Govmap) — long-running
make geocode-dry           # dry-run preview (50 records, no writes)
make streamlit             # launch QA tool
make clean                 # stop and delete volumes (wipes data)
```

---

## Data sources

| Source | Status | Description |
|--------|--------|-------------|
| `nadlan_gov` | active | Gush/chelka real-estate transactions (Govmap) |
| `odata_il_nadlan` | active | Real-estate transactions ZIP→CSV (odata.org.il) |
| `tax_authority_nadlan` | active | Real-estate transactions from the Tax Authority |
| `madlan_for_sale` | active | For-sale listings (madlan.co.il, via Playwright) |
| `cbs_housing` | active | Housing price index and rent index (CBS) |

---

## Dashboard — what you'll see

**`/`** — Landing
- Live KPI hero (listings, median price, ₪/m², best-model R²)
- Mini map preview with hottest / best-value / trending-up city spotlights
- Model garden (all seven models, R² + MAE side by side)
- Inline 10-second prediction with a real address
- "Under the hood" explainer of the pipeline

**`/map`** — Interactive map
- H3 hexagons at low zoom, individual points at high zoom — automatic transition
- Cyan-to-violet color ramp on `avg_price_per_sqm` per cell
- Filters: city, neighborhood, price, rooms, area, date, property type, source
- KPI strip above the map: transactions · avg price · ₪/m² · cities in data
- Address search (Photon geocoder) + click a point to open the detail panel

**`/stats`** — Statistics
- Timeseries — pick month / quarter / year
- Top cities & neighborhoods by ₪/m²
- Histograms of price / ₪/m² / rooms / area / year-built
- Heating cities (YoY ₪/m² change)
- Monthly seasonality
- Breakdowns by source and by property type

**`/property/[id]`** — Property page
- Header + KPIs (area, rooms, floor, age, …)
- Focused mini-map
- 8 similar properties within an 800m radius
- **Price prediction**: pick a single model, or run a multi-model comparison (consensus = median, spread, stddev across all seven)

**`/ai`** — Prediction playground
- Same model-tile grid as the landing
- Manual feature playground with model selector and "compare all" mode

---

## Prediction — multi-model

Seven trained models live under `prediction_service/artifacts/moses/`:
`lightgbm_v1`, `lightgbm_v2_log`, `lightgbm_tuned`, `lightgbm_knn`, `catboost_v1`, `stacked_v1`, `stacked_v2`.

Models load lazily (LRU cache, default size 8). You can list them at `/api/v1/predict/models`. Switching the champion does not require a rebuild:

```bash
make champion MODEL=moses/stacked_v2
```

**API:**
```bash
# default model (champion)
curl -X POST http://localhost:8000/api/v1/predict \
  -H 'Content-Type: application/json' \
  -d '{"features": {"area_sqm": 80, "rooms": 3, ...}}'

# explicit model
curl -X POST 'http://localhost:8000/api/v1/predict?model=moses/catboost_v1' ...

# compare every model
curl -X POST http://localhost:8000/api/v1/predict/compare \
  -H 'Content-Type: application/json' \
  -d '{"features": {...}}'
```

### 🚨 How a new model shows up in the API and dashboard

The API only exposes models that have an actual artifact under `prediction_service/artifacts/<owner>/<name>/model.joblib`. Adding the model code at `prediction_service/models/<owner>/<name>.py` is **not enough** — you also have to train and persist it.

**Step 1 — train (on the researcher's machine):**
```bash
cd prediction_service
python run.py udi/nn_v3        # trains and writes to artifacts/udi/nn_v3/
python run.py udi/blend_v1
# etc.
```
This produces:
- `artifacts/udi/nn_v3/model.joblib`
- `artifacts/udi/nn_v3/metrics.json`
- `artifacts/udi/nn_v3/run_metadata.json`

**Step 2 — share the artifact** (`prediction_service/.gitignore` blocks `artifacts/` and `*.joblib` by default):

Options, in order of simplicity:

**a. Force-add to git** (quick, not great for large files):
```bash
cd prediction_service
git add -f artifacts/udi/
git commit -m "models: add udi/<name> artifact"
git push
```
Teammates: `git pull` then `docker compose restart prediction_service`.

**b. Out-of-band sharing** (Drive / Dropbox / S3):
The trainer uploads `artifacts/udi/<name>/` to the share, the consumer downloads and places it at the same path under `prediction_service/artifacts/udi/<name>/`, then `docker compose restart prediction_service`.

**c. Git LFS** (recommended long-term for large binaries):
```bash
brew install git-lfs
git lfs install
cd prediction_service
git lfs track "artifacts/**/*.joblib"
git add .gitattributes artifacts/udi/
git commit -m "models: udi artifacts via LFS"
git push
```

**Step 3 — verify:**
```bash
docker compose restart prediction_service
make models                                 # is the new model listed?
curl http://localhost:8000/api/v1/predict/models | jq '.[] | .id'
```
The model will surface on `/ai`, in the model dropdown on `/property/[id]`, and in `/predict/compare`.

**Step 4 — promote it to champion** (optional):
```bash
make champion MODEL=udi/nn_v4
# updates CHAMPION_MODEL in .env and restarts the service
```

### Why artifacts aren't in git by default

`prediction_service/.gitignore` excludes `artifacts/` and `*.joblib` because model files are binary blobs (5MB–500MB+), change with every training run, and would bloat history. This is the standard pattern for ML repos. The right long-term fix is either **Git LFS** (option c above) or a dedicated **registry** (MLflow / S3 / DVC).

---

## Address-level geocoding (Govmap)

By default `normalized_records.lat`/`lon` come from the **parcel centroid** of the gush-chelka pair ([get_geom_by_block.py](pre_processing/pipelines/get_geom_by_block.py)) — roughly ±100–300m accurate, and every apartment in the same parcel collapses to one point on the map. The `geocode_addresses.py` pipeline upgrades coordinates to **building level** via Govmap, stamps `coord_source="address"`, and caches results in the `geocode_cache` collection.

```bash
make geocode-dry           # 50 records, no writes — sanity-check settings
make geocode               # full run
.venv/bin/python pre_processing/pipelines/geocode_addresses.py --limit 1000   # smaller batch
```

**Characteristics:**
- **Idempotent and resumable** — the source query filters `coord_source != "address"`, so you can `kill PID` mid-run and resume later without losing work.
- **Cache keyed on `street+city`** — ~63K unique addresses cover ~295K records (a ~4.6× hit ratio). Once an address lands in `geocode_cache`, future records with the same address skip Govmap entirely.
- **Slow by design** — the script is serial with `polite_sleep=0.3s` between Govmap calls. At ~2 it/s that's **~9 hours** on a cold cache (tqdm's ~42h upper estimate is misleading because it doesn't account for the cache). Run it in the background: `nohup .venv/bin/python pre_processing/pipelines/geocode_addresses.py > geocode.log 2>&1 &`
- **Atlas storage** — needs room on the cluster pointed to by `MONGODB_NORMALIZED_URI`. If the cluster is full, you can reclaim space by dropping Atlas's `sample_mflix` demo DB (unused) via Data Explorer.
- **Fields written** — `lat`, `lon`, `coord_source="address"`, `coord_label`, `coord_updated_at`. `normalize_data.py` uses a `$cond` aggregation step so subsequent normalization passes don't overwrite address-level coordinates.
- **Frontend rendering** — [DeckOverlay.tsx](dashboard_app/components/map/DeckOverlay.tsx) reads `coord_source` to vary radius and opacity: `address` = full size and crisp, `parcel_centroid` = smaller and dimmer.

---

## Map clustering strategy

| Zoom | Strategy | H3 res | Cell size | Display |
|------|----------|--------|-----------|---------|
| 0–8 | clusters | 5 | ~8.5km | country-level — large hexagons |
| 9–11 | clusters | 7 | ~1.2km | city-level |
| 12–13 | clusters | 8 | ~460m | neighborhood-level |
| 14+ | points | — | — | individual points, capped at 2000 |

Aggregation runs entirely in Mongo (`$group` on an indexed field) — millisecond response even at 279K records.

---

## Features in `features_enriched`

~88 features unified from three sources:

- **Property attributes**: price, area_sqm, rooms, floor, building_floors, year_built, city, neighborhood, deal_nature, transaction_date, …
- **Macro-economic**: cpi_general, prime_rate, gdp_growth, unemployment, usd_ils, real_interest_rate, housing_cpi_gap, real_price, …
- **OSM spatial features** (50+): distances (water/beach/road/school/park/…), POI counts at various radii, land-use ratios (green/commercial/industrial/residential), …
- **Geo**: `geometry` (GeoJSON Point) plus `h3_r5/r7/r8` for clustering

Full mapping in [docs/raw_records_mapping.json](docs/raw_records_mapping.json).

---

## Endpoints — summary

```
GET  /api/v1/map/data?bbox+zoom+filters         clusters or points
GET  /api/v1/properties/search?...&page&size    search across 9 filters
GET  /api/v1/properties/autocomplete?q          cities / neighborhoods / streets
GET  /api/v1/properties/{id}                    property detail
GET  /api/v1/properties/{id}/similar?radius     nearby comparable sales

GET  /api/v1/stats/summary                      KPIs
GET  /api/v1/stats/timeseries?granularity       average price over time
GET  /api/v1/stats/by-region?level&metric       top regions
GET  /api/v1/stats/distribution?field&bins      histogram
GET  /api/v1/stats/yoy-by-city                  heating cities
GET  /api/v1/stats/source-breakdown             breakdown by source
GET  /api/v1/stats/property-type-breakdown      breakdown by property type
GET  /api/v1/stats/seasonality                  transactions by month

GET  /api/v1/predict/models                     list of models
GET  /api/v1/predict/models/{owner}/{name}      model metadata
POST /api/v1/predict?model=...                  prediction
POST /api/v1/predict/compare                    multi-model comparison
```

Full Swagger UI: http://localhost:8000/docs

---

## Tech stack

| Layer | Technologies |
|-------|--------------|
| Frontend | Next.js 16 · React 19 · TypeScript · Tailwind v4 · MapLibre GL · deck.gl 9 · TanStack Query · Zustand · Recharts |
| Backend | FastAPI · Motor (async Mongo) · httpx · Pydantic v2 · h3 |
| ML | LightGBM · CatBoost · XGBoost · scikit-learn · joblib |
| Data | MongoDB 7 (2dsphere + text + h3 indices) · pandas · geopandas · shapely |
| Infra | Docker · Docker Compose · Playwright |

---

## Local development without Docker

```bash
# Backend
cd dashboard_service
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
MONGO_URI=mongodb+srv://... .venv/bin/uvicorn app.main:app --reload --port 8000

# Frontend
cd dashboard_app
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev

# Prediction
cd prediction_service
.venv/bin/uvicorn serve:app --reload --port 8002
```

---

## License

Academic / research project.
