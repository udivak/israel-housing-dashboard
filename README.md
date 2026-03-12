# Israel Housing Dashboard

פלטפורמת הנדסת נתונים לאיסוף, אחסון והצגת נתוני שוק הדיור בישראל ממקורות open-data מרובים.

---

## ארכיטקטורה

המערכת מורכבת מחמישה שירותים רצים בקונטיינרים:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Docker Network                                 │
│                                                                             │
│  ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────────┐ │
│  │  dashboard_app   │     │  streamlit_app   │     │   collector_service  │ │
│  │  (Next.js:3000) │     │  (Streamlit:8501)│     │   (FastAPI:8001)     │ │
│  └────────┬────────┘     └────────┬────────┘     └──────────┬──────────┘ │
│           │                        │                          │            │
│           │ NEXT_PUBLIC_API_URL    │ API_URL                   │            │
│           ▼                        ▼                          ▼            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    dashboard_service (FastAPI:8000)                  │   │
│  │              API גאו-מרחבי: שכבות מפה, GeoJSON, חיפוש               │   │
│  └───────────────────────────────────────────┬─────────────────────────┘   │
│                                              │                              │
│                                              ▼                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         MongoDB (:27017)                              │   │
│  │  raw_records, properties, districts, parcels, scrape_jobs, sources   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

**זרימת נתונים:**
- **collector_service** – שולף נתונים ממקורות חיצוניים (odata.org.il, madlan, CBS, Govmap) ומכניס ל-MongoDB
- **dashboard_service** – קורא מ-MongoDB ומגיש API גאו-מרחבי (שכבות, GeoJSON)
- **dashboard_app** – פרונטאנד Next.js, קורא ל-dashboard_service מהדפדפן
- **streamlit_app** – פרונטאנד Streamlit לבדיקות, קורא ל-dashboard_service מהשרת

---

## מבנה הפרויקט

```
israel-housing-dashboard/
├── docker-compose.yml      # אורקסטרציה של כל השירותים
├── .env.example            # משתני סביבה – העתק ל-.env
├── collector_service/      # איסוף נתונים – scrapers, jobs, Playwright
├── dashboard_service/      # FastAPI – API גאו-מרחבי
├── dashboard_app/          # Next.js – דשבורד, מפה, חיפוש
└── streamlit_app/          # Streamlit – לבדיקות ו-QA
```

---

## הרצה מהירה (Docker Compose)

**דרישות:** Docker ו-Docker Compose מותקנים.

### שלב 1: הכנת סביבה

```bash
# מהתיקייה הראשית של הפרויקט
cp .env.example .env
```

הקובץ `.env` מכיל כבר ערכי ברירת מחדל. ערוך לפי הצורך (למשל `ODATA_IL_RESOURCE_ID`).

### שלב 2: הרצת כל השירותים

```bash
docker compose up --build
```

בפעם הראשונה יבנה את כל התמונות (כדקה–שתיים). בהרצות הבאות:

```bash
docker compose up
```

### שלב 3: גישה לשירותים

| שירות | URL | תיאור |
|-------|-----|-------|
| **דשבורד (Next.js)** | http://localhost:3000 | פרונטאנד ראשי, מפה, חיפוש |
| **Streamlit** | http://localhost:8501 | פרונטאנד לבדיקות |
| **Dashboard API** | http://localhost:8000 | API גאו-מרחבי |
| **Swagger (Dashboard)** | http://localhost:8000/docs | תיעוד API |
| **Collector API** | http://localhost:8001 | API איסוף נתונים |
| **Swagger (Collector)** | http://localhost:8001/docs | תיעוד Collector |
| **MongoDB** | localhost:27017 | מסד נתונים |

### פקודות שימושיות

```bash
# הרצה ברקע
docker compose up -d

# עצירה
docker compose down

# צפייה בלוגים
docker compose logs -f

# לוגים של שירות ספציפי
docker compose logs -f dashboard_service
```

---

## הרצה ללא Docker (פיתוח מקומי)

אם מעדיפים להריץ ללא קונטיינרים:

### 1. MongoDB

```bash
docker run -d -p 27017:27017 --name mongodb mongo:7
```

או שימוש ב-Atlas – עדכן `MONGO_URI` ב-.env.

### 2. Backend (dashboard_service)

```bash
cd dashboard_service
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
.venv/bin/uvicorn app.main:app --reload --port 8000
```

### 3. Frontend (dashboard_app)

```bash
cd dashboard_app
npm install
cp .env.example .env.local
# ערוך .env.local: NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

### 4. Streamlit (אופציונלי)

```bash
cd streamlit_app
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
# ערוך .env: API_URL=http://localhost:8000
.venv/bin/streamlit run app.py
```

### 5. Collector (אופציונלי)

להרצת collector + MongoDB בלבד:

```bash
cd collector_service
cp .env.example .env
docker compose up --build
```

---

## שירותים – פירוט

| שירות | טכנולוגיה | פורט | תפקיד |
|-------|-----------|------|-------|
| **mongo** | MongoDB 7 | 27017 | מסד נתונים משותף |
| **collector_service** | FastAPI, Python 3.12, Playwright | 8001 | איסוף נתונים ממקורות חיצוניים |
| **dashboard_service** | FastAPI, Python 3.11 | 8000 | API גאו-מרחבי, שכבות מפה, GeoJSON |
| **dashboard_app** | Next.js 16, React 19 | 3000 | פרונטאנד ראשי |
| **streamlit_app** | Streamlit | 8501 | פרונטאנד לבדיקות |

---

## מקורות נתונים

| שם | סטטוס | תיאור |
|----|-------|-------|
| `odata_il_nadlan` | פעיל | עסקאות נדל"ן – odata.org.il (ZIP → CSV) |
| `tax_authority_nadlan` | פעיל | עסקאות נדל"ן – Govmap (רשות המיסים) |
| `cbs_housing` | פעיל | מדדי מחירי דיור ושכר דירה – הלמ"ס |
| `madlan_for_sale` | פעיל | מודעות למכירה – madlan.co.il (Playwright) |

---

## משתני סביבה

הקובץ `.env.example` מכיל את כל המשתנים. העתק ל-`.env` וערוך:

| משתנה | ברירת מחדל | תיאור |
|-------|------------|-------|
| `MONGODB_URI` / `MONGO_URI` | `mongodb://mongo:27017` | חיבור MongoDB (ב-Docker: `mongo` = שם השירות) |
| `MONGODB_DB_NAME` / `DB_NAME` | `israel_housing` | שם מסד הנתונים |
| `ODATA_IL_RESOURCE_ID` | (UUID) | מזהה משאב ב-odata.org.il |
| `MADLAN_HEADLESS` | `true` | Playwright במצב headless |
| `SCRAPER_*` | — | timeout, retries, delays |

---

## Collector Service — API Reference

כל ה-endpoints מתחילים ב-`/api/v1`. מבנה תשובה:

```json
{
  "success": true,
  "data": { ... },
  "message": ""
}
```

### Health

- **GET /health** – Liveness (`{ "status": "ok" }`)
- **GET /ready** – Readiness (בודק חיבור MongoDB)

### Collection

- **POST /api/v1/collect/source/{source_name}** – הפעלת job לאיסוף ממקור בודד
- **POST /api/v1/collect/all** – הפעלת איסוף מכל המקורות

### Jobs

- **GET /api/v1/jobs** – רשימת jobs (עם pagination)
- **GET /api/v1/jobs/{job_id}** – פרטי job
- **GET /api/v1/jobs/all** – כל ה-jobs (עד 1000)

### Sources

- **GET /api/v1/sources** – רשימת מקורות רשומים
- **GET /api/v1/collections/status** – סיכום הרצה אחרונה לכל מקור

Swagger מלא: http://localhost:8001/docs

---

## Architecture (collector_service)

```
collector_service/app/
├── api/routes/       # health, collect, jobs, sources
├── core/              # Config, logging, exceptions
├── db/                # Mongo client, repositories
├── models/            # Pydantic models
├── scrapers/          # odata_il, madlan, cbs, govmap
├── services/          # CollectionService, SourceRegistry
└── main.py
```
