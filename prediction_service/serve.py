"""
FastAPI — מגיש את ה-champion model.

    uvicorn serve:app --reload --port 8001

כשבוחרים champion חדש: לשנות את CHAMPION ולבנות image חדש.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent
CHAMPION = "moses/lightgbm_v1"  # ← לשנות ידנית כשבוחרים זוכה


class Features(BaseModel):
    """הסכמה של ה-input. להתאים לפיצ'רים בפועל אחרי האימון הראשון."""
    # TODO: למלא לאחר שיש feature list סופי
    area_sqm: float
    rooms: float | None = None
    # ... שאר הפיצ'רים
    extra: dict[str, Any] = {}


app = FastAPI(title="Housing price prediction")
_model = None


@app.on_event("startup")
def _load_model():
    global _model
    path = ROOT / "artifacts" / CHAMPION / "model.joblib"
    if not path.exists():
        print(f"⚠️  Model not found: {path}  (run `python run.py {CHAMPION}` first)")
        return
    _model = joblib.load(path)
    print(f"✅ Loaded champion: {CHAMPION}")


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": _model is not None, "champion": CHAMPION}


@app.post("/predict")
def predict(features: Features):
    if _model is None:
        raise HTTPException(503, "Model not loaded")
    df = pd.DataFrame([{**features.model_dump(exclude={"extra"}), **features.extra}])
    y_pred = _model.predict(df)
    return {"predicted_real_price": float(y_pred[0]), "champion": CHAMPION}
