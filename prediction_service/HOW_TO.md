# איך להשתמש ב-prediction_service

מדריך מעשי — איך לעבוד עם השלד שיש כאן: לחקור דאטה, לבנות מודל חדש, לאמן, לקבל תוצאות ולהעלות champion ל-API.

---

## 1. התקנה ראשונית

```bash
cd prediction_service
pip install -r requirements.txt
```

ב-macOS, לפני התקנת LightGBM צריך גם:
```bash
brew install libomp
```

---

## 2. קבצי הדאטה

המערכת מצפה לשלושה קבצים — בתיקיית הריפו (`israel-housing-dashboard/`) או בתיקייה המקבילה (`data_istrael_housing/`):

| קובץ | תוכן | מקור |
|------|------|------|
| `temporal_features.xlsx` | העסקאות + macro + CBS | `pre_processing/pipelines/temporal_macro_feature_pipeline.py` |
| `features_osm.csv` | פיצ'רי OSM לפי `_id` | `pre_processing/pipelines/feature_pipeline.py` |
| `features_coords.csv` | `_id, lat, lon` | `prediction_service/scripts/extract_coords.py` |

אם אחד מהם חסר — יש log אזהרה ברור בזמן הטעינה.

### עדכון lat/lon מ-MongoDB
ריצה חד-פעמית או כשמתעדכנים נתונים חדשים:
```bash
python3 scripts/extract_coords.py
```
הוא קורא את `MONGODB_URI` מ-`pre_processing/.env`, מושך 280K רשומות בbatches, וכותב את הקובץ.

---

## 3. מבנה הקוד

```
prediction_service/
├── common/                    ← תשתית משותפת (לא לגעת בלי הסכמה)
│   ├── data.py                  טעינה, ניקוי, split. הקוד היחיד שטוען דאטה.
│   ├── evaluate.py              מטריקות (MAE, RMSE, MAPE, R²)
│   └── leaderboard.py           ניהול leaderboard.json + leaderboard.md
│
├── models/
│   ├── moses/                 ← התיקייה האישית שלי
│   │   ├── lightgbm_v1.py       baseline
│   │   ├── lightgbm_v2_log.py   log target
│   │   ├── lightgbm_tuned.py    הגרסה המכוונת
│   │   ├── lightgbm_knn.py      ניסיון KNN (לא שיפר)
│   │   ├── catboost_v1.py       CatBoost
│   │   ├── stacked_v1.py        ← champion: LGB + CatBoost
│   │   ├── stacked_v2.py        stacked עם KNN
│   │   ├── EXPERIMENTS.md       יומן הניסיונות שלי
│   │   └── OWNERS
│   │
│   └── partner/               ← התיקייה של השותף
│
├── scripts/
│   └── extract_coords.py        סקריפט שלי ל-lat/lon מ-MongoDB
│
├── artifacts/                   outputs (gitignored): model.joblib, metrics.json
├── leaderboard.json             המקור היחיד ל-results
├── leaderboard.md               auto-generated, human-readable
├── playground.py                לחקור דאטה תא-אחר-תא ב-IDE
├── colab_playground.ipynb       אותו דבר ל-Google Colab
├── run.py                       הריצה הרשמית של submission
└── serve.py                     FastAPI ל-champion
```

---

## 4. לחקור את הדאטה

### לוקאלית
פותחים את `playground.py` ב-VS Code/PyCharm ולוחצים "Run Cell" מעל כל `# %%`. כל תא נפרד — אפשר לרוץ צעד-צעד:
1. טעינת temporal
2. טעינת OSM
3. join + coverage
4. clean
5. select_features
6. split
7. התפלגויות, scatter, correlations

### ב-Colab
מעלים את `colab_playground.ipynb` ל-[colab.research.google.com](https://colab.research.google.com). הקוד inline שם — לא צריך לcloneב-Colab.

---

## 5. בניית מודל חדש — צעד-אחר-צעד

### א. צור קובץ חדש
תחת `models/{שלך}/`. שם הקובץ = שם המודל. למשל `models/moses/xgboost_v1.py`.

### ב. כתוב 2 פונקציות
זה החוזה היחיד שכל מודל חייב לקיים:

```python
def train(X_train, y_train, X_val, y_val):
    """מקבל את הדאטה המפוצלת. חוזר את המודל המאומן."""
    ...
    return model

def predict(model, X):
    """מקבל את ה-model שהוחזר ו-X חדש. חוזר ndarray של תחזיות (real_price)."""
    ...
    return y_pred
```

### ג. דוגמה מינימלית — XGBoost
```python
"""XGBoost basic — דוגמה."""
import numpy as np
import xgboost as xgb

def train(X_train, y_train, X_val, y_val):
    yt = np.log1p(y_train)
    yv = np.log1p(y_val)
    model = xgb.XGBRegressor(
        n_estimators=2000, learning_rate=0.03, max_depth=8,
        early_stopping_rounds=50, tree_method="hist",
        random_state=42, n_jobs=-1,
    )
    # XGBoost לא מטפל native ב-pandas categorical:
    X_train_num = X_train.select_dtypes(exclude="category")
    X_val_num = X_val.select_dtypes(exclude="category")
    model.fit(X_train_num, yt, eval_set=[(X_val_num, yv)], verbose=200)
    return model

def predict(model, X):
    X_num = X.select_dtypes(exclude="category")
    return np.expm1(model.predict(X_num))
```

### ד. הרץ
```bash
python3 run.py moses/xgboost_v1
```

ה-runner ייקח על עצמו את כל השאר:
1. טעינת דאטה (אותו pipeline משותף — אין לך מה להגדיר).
2. קריאה ל-`train()` שלך עם `X_train, y_train, X_val, y_val`.
3. קריאה ל-`predict(model, X_test)`.
4. חישוב metrics דרך `common.evaluate`.
5. שמירת המודל ל-`artifacts/moses/xgboost_v1/model.joblib`.
6. עדכון `leaderboard.json` + `leaderboard.md`.

### ה. תיעוד הניסיון
פתח את `models/moses/EXPERIMENTS.md` והוסף שורה לטבלה + פסקה קצרה על מה ניסית.

---

## 6. הוספת hyperparameter search

הדרך הנקייה — כתוב סקריפט נפרד שמריץ כמה קונפיגים, ואז שמור את הטוב ביותר כקובץ מודל:

```python
# experimental: my_grid_search.py (לא חלק מ-models/)
import numpy as np
import lightgbm as lgb
from common.data import load_data
from common.evaluate import compute_metrics

X_train, y_train, X_val, y_val, X_test, y_test = load_data()

configs = [
    {"name": "deep", "num_leaves": 255, "lr": 0.03},
    {"name": "shallow", "num_leaves": 63, "lr": 0.05},
]

for c in configs:
    model = lgb.LGBMRegressor(...)
    ...
    print(c["name"], compute_metrics(y_test, y_pred))
```

אחרי שמצאת את הזוכה, צור `models/moses/lightgbm_tuned_v2.py` עם הקונפיג הזה ורוץ דרך `run.py`.

---

## 7. הצגת leaderboard

```bash
python3 -c "from common.leaderboard import show; show()"
```

או פתח את `leaderboard.md` שמתעדכן אוטומטית.

---

## 8. API — הגשת champion לפרודקשן

`serve.py` הוא FastAPI שטוען model אחד ב-startup. בקובץ יש משתנה:
```python
CHAMPION = "moses/stacked_v1"  # ← לשנות ידנית כשבוחרים champion חדש
```

הרצה:
```bash
uvicorn serve:app --reload --port 8001
```

או דרך Docker:
```bash
docker compose up prediction_api
```

ה-endpoints:
- `GET /health` — בדיקת חיים + המודל הנטען
- `POST /predict` — JSON עם features → תחזית

---

## 9. כללי הוגנות (חשוב)

1. **אל תיגע ב-`common/`** בלי הסכמה של שני החוקרים. שינוי שם משפיע על כל המודלים בעבר.
2. **`leaderboard.json` נערך רק על-ידי `run.py`**. אין לערוך ידנית.
3. **אותו seed (42)** לכל הריצות. אם בודקים יציבות — 3 seeds ואממוצע.
4. **אסור לחשב feature על בסיס כל הדאטה** (כולל test). כל feature engineering — רק על `X_train`. אם צריך פיצ'ר שמושפע מהtarget (כמו KNN), לחשב ב-out-of-fold.
5. **קוד שלך → תיקייה שלך**. אסור לערוך מודל של השותף.

---

## 10. Troubleshooting

### `KeyError: 'lat'`
חסר `features_coords.csv`. הרץ:
```bash
python3 scripts/extract_coords.py
```

### LightGBM נופל עם `Library not loaded: libomp.dylib` (macOS)
```bash
brew install libomp
```

### MongoDB connection timeout
ה-URI ב-`pre_processing/.env` מצביע ל-Atlas (cloud). אם אין אינטרנט או ה-URI לא תקף — `extract_coords.py` ייכשל. אפשר לדלג עליו, אבל KNN feature לא יעבוד.

### `pandas dtypes must be int, float or bool` ב-LightGBM
פיצ'ר הוא object/string במקום category. ודא ש-`select_features` הופך אותו ב-`CATEGORICAL_COLS`.

### `noTimeout cursors are disallowed` (Atlas free tier)
ה-script כבר מטפל בזה — שולף ב-batches עם `_id` cursor. אם אתה כותב script חדש, אל תשתמש ב-`no_cursor_timeout=True`.

---

## 11. רעיונות לשיפור עתידי

- **5-seed CV** — לוודא שה-MAPE לא תלוי ב-seed המקרי.
- **Target encoding ידני על `city`** עם K-fold — לפעמים מנצח את ה-categorical native.
- **פיצ'רים חיצוניים** — איכות דירה, מצב, תמונות מ-yad2/madlan. שיפור פוטנציאלי גדול.
- **Split כרונולוגי** — לחזור אליו כשיש מספיק דאטה היסטורי של nadlan_gov.
- **A/B בין champions** — לרוץ 2 מודלים במקביל ב-API ולהשוות בפועל.
