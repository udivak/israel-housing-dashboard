"""Proxy to the prediction_service (multi-model)."""

from __future__ import annotations

import os
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/predict", tags=["Predict"])

PREDICTION_SERVICE_URL = os.getenv("PREDICTION_SERVICE_URL", "http://prediction_service:8002")
TIMEOUT_S = float(os.getenv("PREDICTION_SERVICE_TIMEOUT_S", "30"))


class PredictRequest(BaseModel):
    features: dict[str, Any] = Field(..., description="Feature dict matching the chosen model.")


class CompareRequest(BaseModel):
    features: dict[str, Any]
    models: list[str] | None = None


async def _forward(method: str, path: str, **kwargs) -> Any:
    async with httpx.AsyncClient(timeout=TIMEOUT_S) as client:
        try:
            r = await client.request(method, f"{PREDICTION_SERVICE_URL}{path}", **kwargs)
        except httpx.HTTPError as exc:
            raise HTTPException(502, f"prediction_service unreachable: {exc}") from exc
    if r.status_code >= 400:
        raise HTTPException(r.status_code, r.text)
    return r.json()


@router.get("/models")
async def list_models() -> list[dict[str, Any]]:
    """List all models available in prediction_service."""
    return await _forward("GET", "/models")


@router.get("/models/{owner}/{name}")
async def get_model(owner: str, name: str) -> dict[str, Any]:
    return await _forward("GET", f"/models/{owner}/{name}")


@router.post("")
async def predict(
    req: PredictRequest,
    model: str | None = Query(None, description="owner/name; defaults to champion"),
) -> dict[str, Any]:
    """Run prediction with a single (chosen) model."""
    params = {"model": model} if model else {}
    return await _forward("POST", "/predict", json=req.model_dump(), params=params)


@router.post("/compare")
async def predict_compare(req: CompareRequest) -> dict[str, Any]:
    """Run prediction across multiple models and return a comparison."""
    return await _forward("POST", "/predict/compare", json=req.model_dump())
