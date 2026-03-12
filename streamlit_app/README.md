# Israel Housing Dashboard

Streamlit frontend for testing and QA. Mirrors the Next.js dashboard functionality.

## Setup

```bash
cd streamlit_app
pip install -r requirements.txt
cp .env.example .env
# Edit .env: API_URL=http://localhost:8000
```

## Run

```bash
streamlit run app.py
```

Opens at http://localhost:8501

## Run with Backend

```bash
# Terminal 1 - Backend
cd dashboard_service && .venv/bin/uvicorn app.main:app --reload --port 8000

# Terminal 2 - Streamlit
cd streamlit_app && streamlit run app.py
```

## Pages

- **Dashboard** – Welcome, Stats (Map Layers, Properties, API Status), AI placeholder
- **Map** – Search (Photon), Folium map with OpenStreetMap
- **Charts** – Placeholder with sample chart

## API Integration

- Health: `/health`
- Layers: `/api/v1/layers`
- Map Features: `/api/v1/map/features` (BBox)

If the backend is offline, the UI shows fallbacks (e.g. "Service unavailable").
