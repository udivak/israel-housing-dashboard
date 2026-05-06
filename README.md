# Israel Housing Dashboard

פלטפורמה לאיסוף, עיבוד, ניתוח וניבוי של מחירי שוק הנדל"ן בישראל. מערכת מיקרו-שירותים תחת `docker compose` עם דשבורד אינטראקטיבי, מפת חום היררכית ו-7 מודלי ML מאומנים.

---

## ארכיטקטורה

```
                                             ┌───────────────────────────────┐
                                             │  המשתמש (דפדפן)               │
                                             │  http://localhost:3000        │
                                             └───────────────┬───────────────┘
                                                             │
                            ┌────────────────────────────────▼─────────────────────────────────┐
                            │  dashboard_app  (Next.js 16 + React 19 + MapLibre + deck.gl)     │
                            │  /map  /stats  /property/[id]                                    │
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

`★` `load_to_mongo` הוא ה-pipeline שמייצר את ה-collection `features_enriched` עם H3 indices לקלסטרינג זום-מודע. הוא הקלף החשוב ביותר במערכת.

---

## מבנה הפרויקט

```
israel-housing-dashboard/
├── docker-compose.yml          ← אורקסטרציה מאוחדת (default + batch + qa profiles)
├── Makefile                    ← קיצורים לפקודות נפוצות
├── .env.example                ← תבנית סביבה (העתק ל-.env)
│
├── collector_service/          ← FastAPI · scrapers · raw_records
├── dashboard_service/          ← FastAPI · API gateway · features_enriched + stats
├── dashboard_app/              ← Next.js · map · stats · property · prediction UI
├── prediction_service/         ← FastAPI · multi-model serving · 7 trained models
├── pre_processing/             ← ETL pipelines · OSM · temporal · load_to_mongo
├── streamlit_app/              ← Streamlit QA tools
│
├── docs/                       ← תיעוד · diagrams · raw_records_mapping · legacy
└── pre_processing/outputs/     ← CSV/XLSX (gitignored)
```

---

## שירותים — מי עושה מה

| שירות | טכנולוגיה | פורט | תפקיד |
|-------|-----------|------|-------|
| `mongo` | MongoDB 7 | 27017 (פנימי) | מסד נתונים — לוקאלי או Atlas |
| `collector_service` | FastAPI · Playwright | 8001 | scraping למקורות חיצוניים → `raw_records` |
| `pre_processing` | Python · pandas · h3 · geopandas | — | ETL: `raw_records` → `features_enriched` |
| `prediction_service` | FastAPI · LRU model cache | פנימי 8002 | multi-model ML serving |
| `dashboard_service` | FastAPI · Motor · httpx | 8000 | API gateway — חשוף ל-frontend |
| `dashboard_app` | Next.js 16 · MapLibre · deck.gl · recharts | 3000 | UI — מפה · סטטיסטיקות · נכסים · ניבוי |
| `streamlit_app` | Streamlit | 8501 | כלי QA אופציונלי |

---

## הרצה מהירה

```bash
# 1. תבנית סביבה
cp .env.example .env
# ערוך MONGO_URI ל-Atlas או השאר את הברירת המחדל ל-Mongo בקונטיינר

# 2. הרמת המערכת
make up                # = docker compose up --build -d

# 3. (חד-פעמי) טעינת features_enriched
make load-mongo        # מ-Python מקומי, מתאים גם ל-Atlas
# או
make preprocess        # מריץ את ה-pipeline המלא ב-Docker

# 4. גישה
open http://localhost:3000           # דשבורד
open http://localhost:8000/docs      # Swagger של ה-API
```

מצב MapPage רואים ריק? סביר שעדיין לא טענת את `features_enriched`. הרץ `make load-mongo`.

---

## פקודות ה-Makefile

```bash
make help                  # רשימת כל הפקודות
make up                    # הרמת המערכת
make down                  # עצירה
make logs                  # לוגים של כולם
make logs-dashboard        # רק dashboard_service
make health                # בדיקת בריאות לכל השירותים
make models                # רשימת מודלים זמינים ל-prediction
make champion MODEL=moses/stacked_v2   # החלפת champion (ללא rebuild)
make preprocess            # batch ETL
make streamlit             # QA tool
make clean                 # עצירה + מחיקת volumes (מוחק נתונים)
```

---

## מקורות נתונים

| מקור | סטטוס | תיאור |
|------|-------|-------|
| `nadlan_gov` | פעיל | עסקאות נדל״ן גוש/חלקה (Govmap) |
| `odata_il_nadlan` | פעיל | עסקאות נדל״ן ZIP→CSV (odata.org.il) |
| `tax_authority_nadlan` | פעיל | עסקאות נדל״ן רשות המסים |
| `madlan_for_sale` | פעיל | מודעות למכירה (madlan.co.il, Playwright) |
| `cbs_housing` | פעיל | מדדי מחירי דיור ושכר דירה (CBS) |

---

## הדשבורד — מה רואים

**`/map`** — מפה אינטראקטיבית
- Hexagons (H3) בזום נמוך, נקודות בודדות בזום גבוה — מעבר אוטומטי
- צבע diverging לפי `avg_price_per_sqm` בכל אזור
- סינון לפי עיר/שכונה/מחיר/חדרים/שטח/תאריך/סוג נכס/מקור
- KPI strip מעל המפה: עסקאות · מחיר ממוצע · ₪/m² · ערים בנתונים
- חיפוש כתובת (Photon geocoder) + click על נקודה לפתיחת פאנל פרטים

**`/stats`** — סטטיסטיקות
- Timeseries לבחירה של חודש/רבעון/שנה
- Top ערים/שכונות לפי ₪/m²
- Histogram של מחיר/₪/m²/חדרים/שטח/שנת בנייה
- ערים מתחממות (YoY) — שנה לאחור
- עונתיות חודשית
- פילוח לפי מקור ולפי סוג נכס

**`/property/[id]`** — דף נכס
- כותרת + KPIs (שטח, חדרים, קומה, גיל, ...)
- מפה ממוקדת
- 8 נכסים דומים ברדיוס 800m
- **ניבוי מחיר**: בחירת מודל בודד מהרשימה, או "השוואת מודלים" (consensus = median, spread, stddev בין 7 המודלים)

---

## ניבוי — Multi-Model

7 מודלים מאומנים ב-`prediction_service/artifacts/moses/`:
`lightgbm_v1`, `lightgbm_v2_log`, `lightgbm_tuned`, `lightgbm_knn`, `catboost_v1`, `stacked_v1`, `stacked_v2`.

מודלים נטענים עצלים (LRU cache, default 8). רואים אותם דרך `/api/v1/predict/models`. החלפת champion ללא rebuild:

```bash
make champion MODEL=moses/stacked_v2
```

**API:**
```bash
# מודל בודד (defaults to champion)
curl -X POST http://localhost:8000/api/v1/predict \
  -H 'Content-Type: application/json' \
  -d '{"features": {"area_sqm": 80, "rooms": 3, ...}}'

# מודל ספציפי
curl -X POST 'http://localhost:8000/api/v1/predict?model=moses/catboost_v1' ...

# השוואת כל המודלים
curl -X POST http://localhost:8000/api/v1/predict/compare \
  -H 'Content-Type: application/json' \
  -d '{"features": {...}}'
```

---

## Strategy של clustering מפה

| Zoom | אסטרטגיה | H3 res | גודל תא | תצוגה |
|------|-----------|--------|---------|-------|
| 0–8 | clusters | 5 | ~8.5km | תצוגת ארץ — hexagons גדולים |
| 9–11 | clusters | 7 | ~1.2km | תצוגת עיר |
| 12–13 | clusters | 8 | ~460m | תצוגת שכונה |
| 14+ | points | — | — | נקודות בודדות, capped 2000 |

האגרגציה כולה ב-Mongo (`$group` על שדה מאונדקס) — מילישניות גם על 279k רשומות.

---

## פיצ'רים ב-`features_enriched`

~88 features המאוחדים מ-3 מקורות:

- **תכונות נכס**: price, area_sqm, rooms, floor, building_floors, year_built, city, neighborhood, deal_nature, transaction_date, ...
- **מקרו-כלכלי**: cpi_general, prime_rate, gdp_growth, unemployment, usd_ils, real_interest_rate, housing_cpi_gap, real_price, ...
- **OSM מרחבי** (50+): מרחקים (water/beach/road/school/park/...), POI counts ברדיוסים, ratios של שימושי קרקע (green/commercial/industrial/residential), ...
- **גיאו**: `geometry` (GeoJSON Point) + `h3_r5/r7/r8` לקלסטרינג

מפורט ב-[docs/raw_records_mapping.json](docs/raw_records_mapping.json).

---

## Endpoints — סיכום

```
GET  /api/v1/map/data?bbox+zoom+filters         clusters או points
GET  /api/v1/properties/search?...&page&size    חיפוש עם 9 filters
GET  /api/v1/properties/autocomplete?q          ערים/שכונות/רחובות
GET  /api/v1/properties/{id}                    פרטי נכס
GET  /api/v1/properties/{id}/similar?radius     נכסים דומים בקרבת מקום

GET  /api/v1/stats/summary                      KPIs
GET  /api/v1/stats/timeseries?granularity       מחיר ממוצע לאורך זמן
GET  /api/v1/stats/by-region?level&metric       top regions
GET  /api/v1/stats/distribution?field&bins      histogram
GET  /api/v1/stats/yoy-by-city                  ערים מתחממות
GET  /api/v1/stats/source-breakdown             פילוח לפי מקור
GET  /api/v1/stats/property-type-breakdown      פילוח לפי סוג נכס
GET  /api/v1/stats/seasonality                  עסקאות לפי חודש

GET  /api/v1/predict/models                     רשימת מודלים
GET  /api/v1/predict/models/{owner}/{name}      metadata של מודל
POST /api/v1/predict?model=...                  ניבוי
POST /api/v1/predict/compare                    השוואת מודלים
```

Swagger מלא: http://localhost:8000/docs

---

## Stack טכני

| שכבה | טכנולוגיות |
|------|------------|
| Frontend | Next.js 16 · React 19 · TypeScript · Tailwind v4 · MapLibre GL · deck.gl 9 · TanStack Query · Zustand · Recharts |
| Backend | FastAPI · Motor (async Mongo) · httpx · Pydantic v2 · h3 |
| ML | LightGBM · CatBoost · XGBoost · scikit-learn · joblib |
| Data | MongoDB 7 (2dsphere + text + h3 indices) · pandas · geopandas · shapely |
| Infra | Docker · Docker Compose · Playwright |

---

## פיתוח לוקאלי בלי Docker

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

## רישיון

פרויקט אקדמי / מחקר.
