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
make geocode               # שדרוג קואורדינטות הנכסים לרמת כתובת (Govmap) — ארוך
make geocode-dry           # תצוגה מקדימה (50 רשומות, ללא כתיבה)
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

### 🚨 איך מודל חדש מופיע ב-API ובדשבורד

ה-API מציג **רק** מודלים שיש להם artifact בפועל ב-`prediction_service/artifacts/<owner>/<name>/model.joblib`. הוספת קוד מודל ב-`prediction_service/models/<owner>/<name>.py` **לא מספיקה** — צריך גם לאמן ולשמור.

**שלב 1 — אימון (אצל החוקר):**
```bash
cd prediction_service
python run.py udi/nn_v3        # מאמן + שומר ל-artifacts/udi/nn_v3/
python run.py udi/blend_v1
# וכו'
```
זה יוצר:
- `artifacts/udi/nn_v3/model.joblib`
- `artifacts/udi/nn_v3/metrics.json`
- `artifacts/udi/nn_v3/run_metadata.json`

**שלב 2 — שיתוף ה-artifact** (כי `prediction_service/.gitignore` חוסם `artifacts/` ו-`*.joblib`):

האפשרויות (לפי סדר פשטות):

**א. push ל-git עם force-add** (מהיר, פחות אלגנטי לקבצים גדולים):
```bash
cd prediction_service
git add -f artifacts/udi/
git commit -m "models: add udi/<name> artifact"
git push
```
ושותפים: `git pull` ואז `docker compose restart prediction_service`.

**ב. שיתוף ידני** (Drive / Dropbox / S3):
המאמן מעלה את התיקייה `artifacts/udi/<name>/` לשירות שיתוף, השותף מוריד ושם תחת `prediction_service/artifacts/udi/<name>/` במחשבו, ואז `docker compose restart prediction_service`.

**ג. Git LFS** (לטווח ארוך, מומלץ לקבצים גדולים):
```bash
brew install git-lfs
git lfs install
cd prediction_service
git lfs track "artifacts/**/*.joblib"
git add .gitattributes artifacts/udi/
git commit -m "models: udi artifacts via LFS"
git push
```

**שלב 3 — אימות:**
```bash
docker compose restart prediction_service
make models                                 # רואים את המודל החדש?
curl http://localhost:8000/api/v1/predict/models | jq '.[] | .id'
```
המודל יופיע גם ב-`/ai`, גם בדרופדאון של `/property/[id]`, וגם ב-`/predict/compare`.

**שלב 4 — בחירת champion** (אופציונלי):
```bash
make champion MODEL=udi/nn_v4
# מעדכן CHAMPION_MODEL ב-.env ועושה restart
```

### למה ה-artifacts לא ב-git כברירת מחדל

`prediction_service/.gitignore` חוסם `artifacts/` ו-`*.joblib` כי קבצי מודל הם binary blobs (5MB-500MB+), משתנים בכל אימון, ומנפחים את ה-history. זה תקני בפרויקטי ML. הפתרון הנכון לטווח ארוך הוא **Git LFS** (אופציה ג') או **registry** (MLflow / S3 / DVC).

---

## גיאוקודינג ברמת כתובת (Govmap)

ב-`normalized_records` השדות `lat`/`lon` מגיעים כברירת מחדל מ-**parcel centroid** של גוש-חלקה ([get_geom_by_block.py](pre_processing/pipelines/get_geom_by_block.py)) — דיוק של ~100–300 מטר, וכל הדירות באותו גוש נופלות על נקודה אחת על המפה. ה-pipeline `geocode_addresses.py` משדרג את הקואורדינטות לרמת **בניין** מול Govmap, מסמן `coord_source="address"`, ומשמר את התוצאות ב-collection `geocode_cache`.

```bash
make geocode-dry           # 50 רשומות, ללא כתיבה — לוודא הגדרות
make geocode               # ריצה מלאה
.venv/bin/python pre_processing/pipelines/geocode_addresses.py --limit 1000   # batch קטן
```

**מאפיינים:**
- **Idempotent + resumable** — ה-query מסנן `coord_source != "address"`, אז אפשר לעצור (`kill PID`) ולהמשיך מאוחר יותר בלי לאבד עבודה.
- **Cache לפי `street+city`** — ~63K כתובות ייחודיות מכסות ~295K רשומות (יחס ~4.6×). אחרי שכתובת נכנסה ל-`geocode_cache`, רשומות עתידיות עם אותה כתובת לא קוראות שוב ל-Govmap.
- **ארוך** — הסקריפט סדרתי עם `polite_sleep=0.3s` בין קריאות Govmap. בקצב ~2 it/s זה **~9 שעות** לפעם הראשונה (אומדן הגג של tqdm ~42h מטעה — הוא לא מביא בחשבון את ה-cache). מומלץ להריץ ברקע: `nohup .venv/bin/python pre_processing/pipelines/geocode_addresses.py > geocode.log 2>&1 &`
- **Atlas storage** — דורש מקום ב-cluster של `MONGODB_NORMALIZED_URI`. אם ה-cluster מלא, אפשר לפנות מקום במחיקת ה-DB `sample_mflix` של Atlas (demo dataset, לא בשימוש) דרך Data Explorer.
- **שדות מתעדכנים** — `lat`, `lon`, `coord_source="address"`, `coord_label`, `coord_updated_at`. `normalize_data.py` משתמש ב-aggregation-pipeline `$cond` כדי לא לדרוס קואורדינטות ברמת כתובת בריצות נורמליזציה הבאות.
- **Frontend** — [DeckOverlay.tsx](dashboard_app/components/map/DeckOverlay.tsx) משתמש ב-`coord_source` כדי לשנות רדיוס ו-opacity: `address` = מלא וחד, `parcel_centroid` = קטן ודהוי.

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
