"""
FastAPI — multi-model prediction service.

הטעינה lazy: מודל נטען בקריאה הראשונה ונשמר ב-LRU cache.
המשתמש בוחר ב-UI איזה מודל להריץ; אם לא בחר, נופלים ל-CHAMPION_MODEL.

הרצה לוקלית:
    uvicorn serve:app --reload --port 8002
"""

from __future__ import annotations

import os

# macOS: lightgbm/xgboost/catboost/torch each bundle their own OpenMP runtime.
# Loading several in one process aborts with "OMP: Error #15"; allowing the
# duplicate (KMP_DUPLICATE_LIB_OK) then *deadlocks* at the OMP fork barrier when
# torch meets the tree libs. Pinning OMP to a single thread removes the worker
# pool (and the barrier) — and is free for 1-row inference. Must run before any of
# those libs are first imported (they load lazily when models are unpickled).
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")

import importlib
import json
import logging
import math
import statistics
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from common.serving import build_serving_frame

ROOT = Path(__file__).resolve().parent
ARTIFACTS_DIR = Path(os.getenv("ARTIFACTS_DIR", str(ROOT / "artifacts")))
CHAMPION = os.getenv("CHAMPION_MODEL", "moses/lightgbm_v1")
MODEL_CACHE_SIZE = int(os.getenv("MODEL_CACHE_SIZE", "8"))

logger = logging.getLogger("prediction_service")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))


class PredictRequest(BaseModel):
    features: dict[str, Any] = Field(..., description="Feature dict matching the model.")


class PredictResponse(BaseModel):
    predicted_log_price: float
    predicted_price: float
    model: str


class CompareRequest(BaseModel):
    features: dict[str, Any]
    models: list[str] | None = Field(
        default=None,
        description="Models to compare. If omitted/empty, runs all available models.",
    )


class CompareItem(BaseModel):
    model: str
    predicted_log_price: float | None = None
    predicted_price: float | None = None
    error: str | None = None


class CompareResponse(BaseModel):
    items: list[CompareItem]
    consensus_price: float | None = None
    spread_price: float | None = None  # max - min across successful models
    stddev_price: float | None = None


class ModelInfo(BaseModel):
    id: str
    owner: str
    name: str
    metrics: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None
    n_features: int | None = None


app = FastAPI(title="Housing Price Prediction Service", version="2.0.0")


# ---------------------------------------------------------------------------
# Model loading & caching
# ---------------------------------------------------------------------------


def _model_dir(model_id: str) -> Path:
    return ARTIFACTS_DIR / model_id


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


@lru_cache(maxsize=MODEL_CACHE_SIZE)
def _load_model(model_id: str) -> Any:
    path = _model_dir(model_id) / "model.joblib"
    if not path.exists():
        raise FileNotFoundError(f"Model artifact not found: {path}")
    model = joblib.load(path)
    logger.info("Loaded model=%s type=%s", model_id, type(model).__name__)
    return model


def _list_available_models() -> list[ModelInfo]:
    if not ARTIFACTS_DIR.exists():
        return []
    out: list[ModelInfo] = []
    for owner_dir in sorted(p for p in ARTIFACTS_DIR.iterdir() if p.is_dir()):
        for model_dir in sorted(p for p in owner_dir.iterdir() if p.is_dir()):
            artifact = model_dir / "model.joblib"
            if not artifact.exists():
                continue
            mid = f"{owner_dir.name}/{model_dir.name}"
            metadata = _read_json(model_dir / "run_metadata.json")
            metrics = _read_json(model_dir / "metrics.json")
            out.append(
                ModelInfo(
                    id=mid,
                    owner=owner_dir.name,
                    name=model_dir.name,
                    metrics=metrics,
                    metadata=metadata,
                    n_features=(metadata or {}).get("n_features"),
                )
            )
    return out


def _data_version(model_id: str) -> str:
    """moses/* models train on data.py (v1); udi/* on data_v2.py (v2)."""
    return "v1" if model_id.split("/", 1)[0] == "moses" else "v2"


@lru_cache(maxsize=1)
def _base_columns() -> dict[str, list[str] | None]:
    """Per-data-version base feature lists, proxied from a full-base Class-A model.

    Models with an internal feature builder (KNN etc.) are fed this base frame and
    append their own engineered columns inside predict(); see common.serving.
    """
    out: dict[str, list[str] | None] = {"v1": None, "v2": None}
    try:
        out["v1"] = list(_load_model("moses/lightgbm_tuned").feature_name_)
    except Exception:
        logger.exception("Could not load v1 base schema (moses/lightgbm_tuned)")
    try:
        out["v2"] = list(_load_model("udi/xgboost_v1").feature_names_in_)
    except Exception:
        logger.exception("Could not load v2 base schema (udi/xgboost_v1)")
    return out


def _predict_one(model_id: str, features: dict[str, Any]) -> float:
    owner, name = model_id.split("/", 1)
    # Importing the model module also runs the @register_model decorators that
    # populate the NN class registry used by load_bundle().
    mod = importlib.import_module(f"models.{owner}.{name}")
    artifact = _load_model(model_id)

    base_cols = _base_columns().get(_data_version(model_id))
    df = build_serving_frame(artifact, features, base_columns=base_cols)

    raw = float(np.asarray(mod.predict(artifact, df)).ravel()[0])

    # Some models predict raw price in ILS rather than log-price.
    # Normalise to log-price so the API contract is consistent.
    # Log of realistic Israeli apartment prices (1M-10M ILS) is 13.8-16.1; raw
    # prices are always > 100, so this threshold cleanly separates the two cases.
    if raw > 100:
        raw = math.log(raw)

    return raw


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/health")
def health() -> dict[str, Any]:
    available = _list_available_models()
    return {
        "status": "ok",
        "champion": CHAMPION,
        "available_models": [m.id for m in available],
        "cache_size": MODEL_CACHE_SIZE,
    }


@app.get("/models", response_model=list[ModelInfo])
def list_models() -> list[ModelInfo]:
    return _list_available_models()


@app.get("/models/{owner}/{name}", response_model=ModelInfo)
def get_model_info(owner: str, name: str) -> ModelInfo:
    mid = f"{owner}/{name}"
    for m in _list_available_models():
        if m.id == mid:
            return m
    raise HTTPException(404, f"Model {mid} not found")


@app.post("/predict", response_model=PredictResponse)
def predict(
    req: PredictRequest,
    model: str = Query(default=CHAMPION, description="owner/name; defaults to CHAMPION_MODEL"),
) -> PredictResponse:
    try:
        log_price = _predict_one(model, req.features)
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except Exception as exc:
        logger.exception("Prediction failed")
        raise HTTPException(400, f"Prediction failed: {exc}") from exc
    return PredictResponse(
        predicted_log_price=log_price,
        predicted_price=math.exp(log_price),
        model=model,
    )


@app.post("/predict/compare", response_model=CompareResponse)
def predict_compare(req: CompareRequest) -> CompareResponse:
    models = req.models or [m.id for m in _list_available_models()]
    if not models:
        raise HTTPException(404, "No models available")

    items: list[CompareItem] = []
    successful_prices: list[float] = []
    for mid in models:
        try:
            log_price = _predict_one(mid, req.features)
            price = math.exp(log_price)
            items.append(CompareItem(model=mid, predicted_log_price=log_price, predicted_price=price))
            successful_prices.append(price)
        except Exception as exc:
            items.append(CompareItem(model=mid, error=str(exc)))

    consensus = stddev = spread = None
    if successful_prices:
        consensus = float(statistics.median(successful_prices))
        spread = max(successful_prices) - min(successful_prices)
        stddev = float(statistics.pstdev(successful_prices)) if len(successful_prices) > 1 else 0.0

    return CompareResponse(
        items=items,
        consensus_price=consensus,
        spread_price=spread,
        stddev_price=stddev,
    )
