"""Client for dashboard_service API."""

import os
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()
_API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")


def _get(path: str) -> dict[str, Any]:
    url = f"{_API_URL}{path}" if path.startswith("/") else f"{_API_URL}/{path}"
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return r.json()


def fetch_health() -> dict[str, Any]:
    """GET /health"""
    return _get("/health")


def fetch_layers() -> list[dict[str, Any]]:
    """GET /api/v1/layers"""
    return _get("/api/v1/layers")


def fetch_map_features(
    min_lat: float,
    max_lat: float,
    min_lng: float,
    max_lng: float,
    layer_id: str,
) -> dict[str, Any]:
    """GET /api/v1/map/features with BBox params"""
    params = {
        "min_lat": min_lat,
        "max_lat": max_lat,
        "min_lng": min_lng,
        "max_lng": max_lng,
        "layer_id": layer_id,
    }
    url = f"{_API_URL}/api/v1/map/features"
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    return r.json()
