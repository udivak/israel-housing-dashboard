# Israel Housing Dashboard

Next.js frontend for the real estate intelligence platform. Runs independently from dashboard_service.

## Setup

```bash
cd dashboard_app
npm install
cp .env.example .env.local
# Edit .env.local: NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Run

```bash
npm run dev
```

Opens at http://localhost:3000

## Run with Backend

```bash
# Terminal 1 - Backend
cd dashboard_service && .venv/bin/uvicorn app.main:app --reload --port 8000

# Terminal 2 - Frontend
cd dashboard_app && npm run dev
```

## Map & Search

- **Map:** MapLibre GL with OpenStreetMap tiles, centered on Israel
- **Search:** Photon (Komoot) – free geocoding for streets, cities, addresses. No API key required.
- Navigate to `/map` to use the map with search.

## API Integration

- **Health:** `/health` – connection status
- **Layers:** `/api/v1/layers` – map layers (shown in StatsCards)
- **Map Features:** `/api/v1/map/features` – GeoJSON by BBox (for future integration)

If the backend is offline, the UI shows fallbacks (e.g. "Service unavailable") without crashing.
