"""
FastAPI — מגיש את ה-champion model.

הרצה לוקלית:
    uvicorn serve:app --reload --port 8002

ב-Docker רץ אוטומטית עם החלפת champion דרך CHAMPION_MODEL env var.
"""

from __future__ import annotations

import logging
import math
import os
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent
CHAMPION = os.getenv("CHAMPION_MODEL", "moses/lightgbm_v1")
ARTIFACTS_DIR = Path(os.getenv("ARTIFACTS_DIR", str(ROOT / "artifacts")))

logger = logging.getLogger("prediction_service")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))


class PredictRequest(BaseModel):
    features: dict[str, Any] = Field(
        ...,
        description="Feature dict; keys must match model's expected feature names.",
    )


class PredictResponse(BaseModel):
    predicted_log_price: float
    predicted_price: float
    champion: str


app = FastAPI(title="Housing Price Prediction Service", version="1.0.0")
_model: Any | None = None
_feature_names: list[str] | None = None


@app.on_event("startup")
def _load_model() -> None:
    global _model, _feature_names
    path = ARTIFACTS_DIR / CHAMPION / "model.joblib"
    if not path.exists():
        logger.warning("Model not found at %s — service will return 503 on /predict", path)
        return
    _model = joblib.load(path)
    # Try common attributes for feature lists across sklearn-style estimators.
    for attr in ("feature_name_", "feature_names_in_", "feature_names_"):
        names = getattr(_model, attr, None)
        if names is not None:
            _feature_names = list(names)
            break
    logger.info("Loaded champion=%s features=%s", CHAMPION, len(_feature_names or []))


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "model_loaded": _model is not None,
        "champion": CHAMPION,
        "n_features": len(_feature_names) if _feature_names else None,
    }


@app.get("/champion")
def champion_info() -> dict[str, Any]:
    if _model is None:
        raise HTTPException(503, "Model not loaded")
    metadata_path = ARTIFACTS_DIR / CHAMPION / "run_metadata.json"
    metrics_path = ARTIFACTS_DIR / CHAMPION / "metrics.json"
    out: dict[str, Any] = {"champion": CHAMPION, "feature_names": _feature_names}
    if metadata_path.exists():
        import json
        out["metadata"] = json.loads(metadata_path.read_text())
    if metrics_path.exists():
        import json
        out["metrics"] = json.loads(metrics_path.read_text())
    return out


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest) -> PredictResponse:
    if _model is None:
        raise HTTPException(503, "Model not loaded")

    df = pd.DataFrame([req.features])
    if _feature_names is not None:
        missing = [c for c in _feature_names if c not in df.columns]
        for col in missing:
            df[col] = None
        df = df[_feature_names]

    try:
        y_pred = _model.predict(df)
    except Exception as exc:
        logger.exception("Prediction failed")
        raise HTTPException(400, f"Prediction failed: {exc}") from exc

    log_price = float(y_pred[0])
    return PredictResponse(
        predicted_log_price=log_price,
        predicted_price=math.exp(log_price),
        champion=CHAMPION,
    )
