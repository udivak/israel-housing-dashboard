"""Govmap autocomplete-based geocoding with Web Mercator→WGS84 conversion.

Govmap (https://www.govmap.gov.il/api) is Israel's official public mapping
service. Its `search-service/autocomplete` endpoint returns building-level
results for Hebrew addresses in Web Mercator (EPSG:3857). This module wraps
that endpoint and converts results to WGS84 (EPSG:4326).
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

import httpx
from pyproj import Transformer

GOVMAP_BASE_URL = "https://www.govmap.gov.il/api"
AUTOCOMPLETE_PATH = "search-service/autocomplete"

ISRAEL_BBOX = (29.4, 33.4, 34.2, 35.9)  # (min_lat, max_lat, min_lon, max_lon)

_DEFAULT_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}

_webmerc_to_wgs84 = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)


@dataclass(frozen=True)
class GeocodeResult:
    lat: float
    lon: float
    raw_label: str


def webmerc_to_wgs84(x: float, y: float) -> tuple[float, float]:
    """Convert Web Mercator (EPSG:3857) (x, y) → WGS84 (lon, lat)."""
    lon, lat = _webmerc_to_wgs84.transform(x, y)
    return lon, lat


def in_israel_bbox(lat: float, lon: float) -> bool:
    min_lat, max_lat, min_lon, max_lon = ISRAEL_BBOX
    return min_lat <= lat <= max_lat and min_lon <= lon <= max_lon


def build_query(street: Optional[str], city: Optional[str]) -> Optional[str]:
    """Compose a Govmap-friendly query. Returns None if too sparse to be useful."""
    street = (street or "").strip()
    city = (city or "").strip()
    if not street or not city:
        return None
    return f"{street}, {city}"


def geocode_address(
    client: httpx.Client,
    query: str,
    *,
    city: Optional[str] = None,
    timeout: float = 10.0,
) -> Optional[GeocodeResult]:
    """Geocode a single address via Govmap autocomplete.

    Uses a two-pass strategy:
    1. `isAccurate=True`  — exact match, works well for full "street house, city" queries.
    2. `isAccurate=False` — fuzzy match, returns many results; we pick the first `address`-type
       result whose text contains the city name (case-insensitive), then fall back to any
       `address`-type result if no city match is found.

    Returns None on no-result, network error, or out-of-Israel coordinate.
    """
    url = f"{GOVMAP_BASE_URL}/{AUTOCOMPLETE_PATH}"

    for is_accurate, max_results in [(True, 1), (False, 30)]:
        payload = {
            "searchText": query,
            "language": "he",
            "isAccurate": is_accurate,
            "maxResults": max_results,
        }
        try:
            resp = client.post(url, json=payload, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPError, ValueError):
            return None

        results = data.get("results") if isinstance(data, dict) else None
        if not results:
            continue

        # Filter to address-type results only (exclude settlement/region hits).
        address_results = [r for r in results if r.get("type") == "address"]
        if not address_results:
            address_results = results  # fallback: take any type

        chosen = None
        if city and not is_accurate:
            city_lower = city.lower()
            # Only accept results where text or originalText explicitly mentions the city.
            # No city match → skip this pass entirely (don't fall back to wrong city).
            for r in address_results:
                text = ((r.get("text") or "") + " " + (r.get("originalText") or "")).lower()
                if city_lower in text:
                    chosen = r
                    break
            if chosen is None:
                continue
        else:
            chosen = address_results[0]

        label = str(chosen.get("text") or chosen.get("displayText") or query)
        xy = _extract_itm(chosen)
        if xy is None:
            continue

        lon, lat = webmerc_to_wgs84(*xy)
        if not in_israel_bbox(lat, lon):
            continue
        return GeocodeResult(lat=lat, lon=lon, raw_label=label)

    return None


def _extract_itm(result: dict) -> Optional[tuple[float, float]]:
    """Return (x, y) ITM coords from a Govmap autocomplete result."""
    shape = result.get("shape", "")
    if isinstance(shape, str) and shape.startswith("POINT("):
        parts = shape[6:-1].split()
        if len(parts) == 2:
            try:
                return float(parts[0]), float(parts[1])
            except ValueError:
                pass

    x = result.get("x") or result.get("lon")
    y = result.get("y") or result.get("lat")
    if x is not None and y is not None:
        try:
            return float(x), float(y)
        except (TypeError, ValueError):
            pass
    return None


def make_client() -> httpx.Client:
    return httpx.Client(headers=_DEFAULT_HEADERS, follow_redirects=True)


def polite_sleep(seconds: float) -> None:
    if seconds > 0:
        time.sleep(seconds)
