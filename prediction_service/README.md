# prediction_service

חיזוי מחירי דיור. benchmark של מודלים — כל חוקר בונה כמה מודלים, ה-leaderboard בוחר את הטוב ביותר.

## מבנה

```
prediction_service/
├── common/              ← תשתית משותפת (data, evaluate, leaderboard) — שינוי דורש הסכמה
├── models/
│   ├── moses/           ← המודלים שלי
│   └── partner/         ← המודלים של השותף
├── artifacts/           ← outputs (gitignored)
├── run.py               ← הריצה הרשמית
├── serve.py             ← FastAPI ל-champion
├── playground.py        ← לחקור את הדאטה תא-אחר-תא
├── leaderboard.json     ← source of truth
└── leaderboard.md       ← auto-generated
```

## Setup

```bash
pip install -r requirements.txt
```

## איפה לשחק עם הדאטה

**`playground.py`** — קובץ אינטראקטיבי עם תאי `# %%`. פתח ב-VS Code או PyCharm ולחץ "Run Cell" מעל כל תא.

התאים בסדר הגיוני:
1. טעינת `temporal_features.xlsx`
2. טעינת `features_osm.csv`
3. Join
4. Clean
5. Select features
6. Split
7. התפלגויות, קורלציות, scatter plots

כל תא מדפיס/מראה משהו. שנה חופשי — זה ה-scratchpad שלך.

## איך להוסיף מודל חדש

1. צור קובץ: `models/{person}/{model_name}.py`
2. כתוב 2 פונקציות:
   ```python
   def train(X_train, y_train, X_val, y_val):
       ...
       return model

   def predict(model, X):
       return model.predict(X)
   ```
3. הרץ: `python run.py {person}/{model_name}`

זהו. ה-runner ידאג לכל השאר: טעינת דאטה, metrics, leaderboard, artifacts.

## הרצה

```bash
# אימון והערכה של מודל
python run.py moses/lightgbm_v1

# תצוגת leaderboard
python -c "from common.leaderboard import show; show()"

# API
uvicorn serve:app --reload --port 8001
```

## Target

`real_price` — מחיר עסקה מנורמל-אינפלציה (CPI-adjusted). המרה ל-nominal ב-API על-ידי הכפלה ב-`real_price_factor` של התאריך המבוקש.

## Split

כרונולוגי (לא רנדומלי!):
- **train**: עסקאות עד 2024-01-01
- **val**: 2024
- **test**: מ-2025 ואילך
