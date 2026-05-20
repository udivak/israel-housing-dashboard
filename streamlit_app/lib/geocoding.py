"""Photon geocoding API for place search."""

from typing import Any, Optional

import requests

PHOTON_API = "https://photon.komoot.io/api"

# Israel bounding box (lon1,lat1,lon2,lat2) and centroid for location bias.
_ISRAEL_BBOX = "34.2,29.5,35.9,33.3"
_ISRAEL_LAT = 31.7
_ISRAEL_LON = 34.9


def search_places(
    query: str,
    limit: int = 8,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
) -> list:
    """Search places via Photon API, biased to Israel."""
    if not query or not query.strip():
        return []

    params = {
        "q": query.strip(),
        "limit": limit,
        "lang": "he",
        "bbox": _ISRAEL_BBOX,
        "lat": lat if lat is not None else _ISRAEL_LAT,
        "lon": lon if lon is not None else _ISRAEL_LON,
    }

    headers = {"User-Agent": "IsraelHousingDashboard/1.0"}
    r = requests.get(f"{PHOTON_API}/", params=params, headers=headers, timeout=10)
    r.raise_for_status()
    data = r.json()
    return data.get("features", [])


def format_address(feature: dict[str, Any]) -> str:
    """Format address from Photon feature properties."""
    p = feature.get("properties", {})
    parts = [
        p.get("name"),
        p.get("street"),
        p.get("district"),
        p.get("county"),
        p.get("state"),
        p.get("country"),
    ]
    return ", ".join(str(x) for x in parts if x) or "Unknown"
