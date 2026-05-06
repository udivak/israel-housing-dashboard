"""Proxy to the prediction_service."""

from __future__ import annotations

import os
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/predict", tags=["Predict"])

PREDICTION_SERVICE_URL = os.getenv("PREDICTION_SERVICE_URL", "http://prediction_service:8002")
TIMEOUT_S = float(os.getenv("PREDICTION_SERVICE_TIMEOUT_S", "10"))


class PredictRequest(BaseModel):
    features: dict[str, Any] = Field(..., description="Feature dict matching the champion model.")


@router.post("")
async def predict(req: PredictRequest) -> dict[str, Any]:
    """Forward a prediction request to the prediction_service."""
    async with httpx.AsyncClient(timeout=TIMEOUT_S) as client:
        try:
            r = await client.post(f"{PREDICTION_SERVICE_URL}/predict", json=req.model_dump())
        except httpx.HTTPError as exc:
            raise HTTPException(502, f"prediction_service unreachable: {exc}") from exc
    if r.status_code >= 400:
        raise HTTPException(r.status_code, r.text)
    return r.json()


@router.get("/champion")
async def champion_info() -> dict[str, Any]:
    """Pass-through champion metadata (feature list, metrics)."""
    async with httpx.AsyncClient(timeout=TIMEOUT_S) as client:
        try:
            r = await client.get(f"{PREDICTION_SERVICE_URL}/champion")
        except httpx.HTTPError as exc:
            raise HTTPException(502, f"prediction_service unreachable: {exc}") from exc
    if r.status_code >= 400:
        raise HTTPException(r.status_code, r.text)
    return r.json()
