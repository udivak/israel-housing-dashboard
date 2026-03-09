# Dashboard & Map Visualization Service

Unit 2 of the distributed real-estate intelligence system. Serves geospatial data to a Next.js frontend (MapLibre/Deck.gl) via GeoJSON and high-performance Bounding Box (BBox) queries.

## Setup

### Prerequisites

- Python 3.9+
- MongoDB 4.0+ (with 2dsphere support)

### Install

```bash
cd dashboard_service
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
# Edit .env with your MONGO_URI and DB_NAME
```

### Run

```bash
# Option 1: Activate venv first, then run
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Option 2: Run directly via venv (no activation needed)
.venv/bin/uvicorn app.main:app --reload --port 8000
```

### Docker

```bash
docker build -t dashboard-service .
docker run -p 8000:8000 --env-file .env dashboard-service
```

## Architecture

### BBox Queries

The `/api/v1/map/features` endpoint uses MongoDB's `$geoWithin` with `$box` for fast spatial queries:

1. Client sends `min_lat`, `max_lat`, `min_lng`, `max_lng` and `layer_id`.
2. The service builds a box: `[[minLng, minLat], [maxLng, maxLat]]`.
3. MongoDB 2dsphere index enables efficient `$geoWithin` queries.
4. Documents with a `geometry` field (GeoJSON) inside the box are returned.
5. Results are transformed into a strict RFC 7946 `FeatureCollection`.

### Data Model

- **GeoJSON**: Documents must have a `geometry` field (Point, Polygon, etc.).
- **Indexes**: `ensure_geo_indexes()` creates `2dsphere` on `geometry` for collections: `properties`, `districts`, `parcels`.

## API Examples

### Health Check

```bash
curl http://localhost:8000/health
```

### List Layers

```bash
curl http://localhost:8000/api/v1/layers
```

### Get Features in BBox (Tel Aviv area)

```bash
curl "http://localhost:8000/api/v1/map/features?min_lat=32.05&max_lat=32.12&min_lng=34.75&max_lng=34.82&layer_id=properties"
```

### Swagger UI

Open http://localhost:8000/docs for interactive API documentation.

### Documentation Spec

See [docs/DOCUMENTATION_SPEC.md](docs/DOCUMENTATION_SPEC.md) for the full documentation specification (Hebrew).
