# Israel Housing Dashboard

Real estate intelligence platform – Next.js frontend + FastAPI backend.

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

### 4. הרצה מלאה (2 טרמינלים)

```bash
# טרמינל 1 – Backend
cd dashboard_service && .venv/bin/uvicorn app.main:app --reload --port 8000

# טרמינל 2 – Frontend (Next.js)
cd dashboard_app && npm run dev

# או Streamlit
cd streamlit_app && .venv/bin/streamlit run app.py
```

### 5. MongoDB (Docker)

```bash
docker run -d -p 27017:27017 --name mongodb mongo:latest
```

### 6. Backend ב-Docker

```bash
cd dashboard_service
docker build -t dashboard-service .
docker run -p 8000:8000 --env-file .env dashboard-service
```

## מבנה הפרויקט

```
israel-housing-dashboard/
├── dashboard_app/      # Next.js – דשבורד, מפה, חיפוש
├── dashboard_service/  # FastAPI – API גאו-מרחבי
├── streamlit_app/      # Streamlit – לבדיקות וטסטים
└── README.md
```

## קישורים

| שירות        | URL                    |
|-------------|------------------------|
| Frontend (Next.js) | http://localhost:3000  |
| Streamlit   | http://localhost:8501  |
| Backend API | http://localhost:8000  |
| Swagger     | http://localhost:8000/docs |
