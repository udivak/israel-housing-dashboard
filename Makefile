SHELL := /bin/bash
.DEFAULT_GOAL := help

# Auto-load .env so targets that run scripts directly (e.g. load-mongo) get
# the same vars docker-compose sees.
ifneq (,$(wildcard .env))
include .env
export
endif

help:                          ## הצגת רשימת הפקודות
	@grep -E '^[a-zA-Z_.-]+:.*?##' $(MAKEFILE_LIST) | awk -F':.*?##' '{printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# -----------------------------------------------------------------------------
# Stack lifecycle
# -----------------------------------------------------------------------------
up:                            ## הרצת כל השירותים (default profile)
	docker compose up --build -d

down:                          ## עצירה
	docker compose down

restart:                       ## restart לכל השירותים
	docker compose restart

logs:                          ## לוגים של כל השירותים
	docker compose logs -f

ps:                            ## סטטוס שירותים
	docker compose ps

clean:                         ## עצירה + מחיקת volumes (זהירות — מוחק נתונים)
	docker compose down -v

# -----------------------------------------------------------------------------
# Service-specific logs
# -----------------------------------------------------------------------------
logs-dashboard:                ## לוגים של dashboard_service
	docker compose logs -f dashboard_service

logs-collector:                ## לוגים של collector_service
	docker compose logs -f collector_service

logs-predict:                  ## לוגים של prediction_service
	docker compose logs -f prediction_service

logs-app:                      ## לוגים של dashboard_app
	docker compose logs -f dashboard_app

# -----------------------------------------------------------------------------
# Batch / QA profiles
# -----------------------------------------------------------------------------
preprocess:                    ## הרצת ה-pipeline המלא של pre_processing
	docker compose --profile batch up --build pre_processing

load-mongo:                    ## טעינת features_enriched ל-Mongo (לוקלית)
	@if [ ! -d .venv ]; then python3 -m venv .venv && .venv/bin/pip install -r pre_processing/requirements.txt; fi
	.venv/bin/python -m pre_processing.pipelines.load_to_mongo

geocode:                       ## שדרוג קואורדינטות הנכסים לרמת כתובת (Govmap)
	@if [ ! -d .venv ]; then python3 -m venv .venv && .venv/bin/pip install -r pre_processing/requirements.txt; fi
	.venv/bin/python pre_processing/pipelines/geocode_addresses.py $(ARGS)

geocode-dry:                   ## תצוגה מקדימה של geocoding ללא כתיבה ל-DB
	@if [ ! -d .venv ]; then python3 -m venv .venv && .venv/bin/pip install -r pre_processing/requirements.txt; fi
	.venv/bin/python pre_processing/pipelines/geocode_addresses.py --dry-run --limit 50

streamlit:                     ## הרצת streamlit_app (QA)
	docker compose --profile qa up --build streamlit_app

# -----------------------------------------------------------------------------
# Health / smoke
# -----------------------------------------------------------------------------
health:                        ## בדיקת בריאות לכל השירותים
	@curl -fs http://localhost:8000/health | jq . || echo "dashboard_service DOWN"
	@curl -fs http://localhost:8001/health | jq . || echo "collector_service DOWN"
	@curl -fs http://localhost:3000 -o /dev/null && echo "dashboard_app: ok" || echo "dashboard_app DOWN"

models:                        ## רשימת מודלים זמינים ב-prediction_service
	@curl -fs http://localhost:8000/api/v1/predict/models | jq .

# -----------------------------------------------------------------------------
# Frontend dev
# -----------------------------------------------------------------------------
dev-app:                       ## הרצת dashboard_app בפיתוח (npm)
	cd dashboard_app && npm run dev

build-app:                     ## בניית dashboard_app
	cd dashboard_app && npm run build

# -----------------------------------------------------------------------------
# Champion model swap
# -----------------------------------------------------------------------------
champion:                      ## החלפת champion: make champion MODEL=moses/stacked_v2
	@if [ -z "$(MODEL)" ]; then echo "Usage: make champion MODEL=owner/name"; exit 1; fi
	@grep -v '^CHAMPION_MODEL=' .env > .env.tmp && mv .env.tmp .env
	@echo "CHAMPION_MODEL=$(MODEL)" >> .env
	docker compose restart prediction_service
	@echo "Champion now: $(MODEL)"
