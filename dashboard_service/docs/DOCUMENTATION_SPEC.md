# מסמך מפרט דוקומנטציה – Dashboard & Map Visualization Service

## 1. מטרת המסמך

מסמך זה מגדיר את מבנה הדוקומנטציה, התוכן והפורמט של שירות Dashboard & Map Visualization (יחידה 2 במערכת המידע הנדל"ני).

---

## 2. מבנה הדוקומנטציה

### 2.1 קובץ README.md (שורש הפרויקט)

| סעיף | תוכן | חובה |
|------|------|------|
| 1. תיאור | שם המודול, תפקיד, הקשר במערכת (יחידה 2) | כן |
| 2. דרישות מקדימות | Python 3.9+, MongoDB 4.0+ (2dsphere) | כן |
| 3. התקנה | `pip install`, `cp .env.example .env` | כן |
| 4. הרצה | uvicorn (כולל venv) | כן |
| 5. Docker | build, run | כן |
| 6. ארכיטקטורה | BBox queries, איך עובד `$geoWithin` | כן |
| 7. דוגמאות API | curl לכל endpoint | כן |
| 8. Swagger | קישור ל־`/docs` | כן |

### 2.2 דוקומנטציה טכנית (API docs)

| סעיף | תוכן | חובה |
|------|------|------|
| 1. תיאור כללי | OpenAPI `title`, `description`, `version` | כן |
| 2. Endpoints | כל endpoint עם docstring | כן |
| 3. פרמטרים | Query params, validation | כן |
| 4. תגובות | 200, 400, 404 | כן |
| 5. דוגמאות | Request/Response לדוגמה | כן |

---

## 3. מפרט Endpoints

### 3.1 GET /health

| שדה | ערך |
|-----|-----|
| **תיאור** | Health check ל־load balancers ו־monitoring |
| **מענה** | `{"status": "ok", "service": "dashboard-map-service"}` |
| **קוד סטטוס** | 200 |
| **דוגמת curl** | `curl http://localhost:8000/health` |

### 3.2 GET /api/v1/layers

| שדה | ערך |
|-----|-----|
| **תיאור** | רשימת שכבות מפה עם מטא־דאטה לעיצוב (MapLibre/Deck.gl) |
| **מענה** | `list[LayerConfig]` |
| **קוד סטטוס** | 200 |
| **דוגמת curl** | `curl http://localhost:8000/api/v1/layers` |

### 3.3 GET /api/v1/map/features

| שדה | ערך |
|-----|-----|
| **תיאור** | GeoJSON FeatureCollection לפי BBox |
| **פרמטרים** | `min_lat`, `max_lat`, `min_lng`, `max_lng`, `layer_id` |
| **מענה** | GeoJSON FeatureCollection (RFC 7946) |
| **קודי סטטוס** | 200, 400 (BBox לא תקין), 404 (שכבה לא קיימת) |
| **דוגמת curl** | `curl "http://localhost:8000/api/v1/map/features?min_lat=32.05&max_lat=32.12&min_lng=34.75&max_lng=34.82&layer_id=properties"` |

---

## 4. מפרט מודלים

### 4.1 GeoJSON (RFC 7946)

| מודל | שדות | תיאור |
|------|------|-------|
| **Point** | `type`, `coordinates` [lng, lat] | נקודה |
| **LineString** | `type`, `coordinates` | קו |
| **Polygon** | `type`, `coordinates` | פוליגון |
| **MultiPoint** | `type`, `coordinates` | מספר נקודות |
| **MultiLineString** | `type`, `coordinates` | מספר קווים |
| **MultiPolygon** | `type`, `coordinates` | מספר פוליגונים |
| **Feature** | `type`, `geometry`, `properties`, `id` | Feature בודד |
| **FeatureCollection** | `type`, `features` | אוסף Features |

### 4.2 LayerConfig

| שדה | טיפוס | ברירת מחדל | תיאור |
|-----|--------|------------|-------|
| `id` | str | — | מזהה שכבה |
| `name` | str | — | שם תצוגה |
| `type` | fill \| line \| circle \| symbol | fill | סוג שכבה ב־MapLibre |
| `color` | str | #3388ff | צבע hex |
| `source` | str | — | אוסף MongoDB |
| `min_zoom` | float \| null | null | רמת zoom מינימלית |
| `max_zoom` | float \| null | null | רמת zoom מקסימלית |
| `opacity` | float | 0.8 | שקיפות (0–1) |

### 4.3 BBoxQueryParams

| שדה | טיפוס | אילוצים | תיאור |
|-----|--------|----------|-------|
| `min_lat` | float | -90..90 | קו רוחב דרומי |
| `max_lat` | float | -90..90, ≥ min_lat | קו רוחב צפוני |
| `min_lng` | float | -180..180 | קו אורך מערבי |
| `max_lng` | float | -180..180, ≥ min_lng | קו אורך מזרחי |
| `layer_id` | str | min_length=1 | מזהה שכבה |

---

## 5. מפרט שגיאות

| Exception | קוד | מתי |
|-----------|-----|-----|
| `InvalidBBoxError` | 400 | פרמטרי BBox לא תקינים |
| `LayerNotFoundError` | 404 | `layer_id` לא קיים |
| `GeoDataNotFoundError` | 404 | אין נתונים גאו־מרחביים |

---

## 6. מפרט תצורה

| משתנה סביבה | ברירת מחדל | תיאור |
|--------------|------------|-------|
| `MONGO_URI` | mongodb://localhost:27017 | כתובת MongoDB |
| `DB_NAME` | israel_housing | שם מסד הנתונים |

---

## 7. מפרט ארכיטקטורה

### 7.1 זרימת BBox Query

1. Client שולח `min_lat`, `max_lat`, `min_lng`, `max_lng`, `layer_id`
2. ולידציה ב־`BBoxQueryParams`
3. בדיקת קיום השכבה ב־`LayerService`
4. שאילתת MongoDB: `{"geometry": {"$geoWithin": {"$box": [[minLng, minLat], [maxLng, maxLat]]}}}`
5. המרת תוצאות ל־GeoJSON FeatureCollection

### 7.2 אינדקסים

- `2dsphere` על שדה `geometry` באוספים: `properties`, `districts`, `parcels`
- נוצרים אוטומטית ב־startup (`ensure_geo_indexes`)

### 7.3 מבנה שכבות

- `layer_id` = שם אוסף MongoDB
- שכבות ברירת מחדל: `properties`, `districts`
- הגדרות שכבות באוסף `layer_configs`

---

## 8. פורמט דוקומנטציה בקוד

### 8.1 Docstrings

- **מודולים:** תיאור קצר של תפקיד המודול
- **מחלקות:** תיאור תפקיד המחלקה
- **פונקציות:** תיאור, פרמטרים, ערך החזרה, חריגות

### 8.2 OpenAPI

- `summary` לכל endpoint
- `description` עם Markdown
- `responses` לכל קוד סטטוס
- דוגמאות Request/Response ב־`description`

---

## 9. קבצי דוקומנטציה

| קובץ | מיקום | תוכן |
|------|--------|------|
| README.md | dashboard_service/ | התקנה, הרצה, ארכיטקטורה, דוגמאות |
| DOCUMENTATION_SPEC.md | dashboard_service/docs/ | מפרט דוקומנטציה (מסמך זה) |
| .env.example | dashboard_service/ | משתני סביבה |

---

## 10. כלים

| כלי | שימוש |
|-----|--------|
| Swagger UI | `/docs` – דוקומנטציה אינטראקטיבית |
| ReDoc | `/redoc` – דוקומנטציה אלטרנטיבית (FastAPI) |
| OpenAPI JSON | `/openapi.json` – סכמה לייצוא |
