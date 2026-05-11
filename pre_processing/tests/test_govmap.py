"""Unit tests for the Govmap geocoding helpers — no network calls."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from lib.govmap import (  # noqa: E402
    GeocodeResult,
    _extract_itm,
    build_query,
    geocode_address,
    in_israel_bbox,
    webmerc_to_wgs84,
)


# Known reference: Rothschild 1, Tel Aviv — verified from live Govmap response.
# Web Mercator (EPSG:3857) coordinates returned by Govmap autocomplete.
TEL_AVIV_WM_X = 3870469.14
TEL_AVIV_WM_Y = 3771587.62
TEL_AVIV_LAT = 32.063
TEL_AVIV_LON = 34.769


def test_webmerc_to_wgs84_round_trip_tel_aviv():
    lon, lat = webmerc_to_wgs84(TEL_AVIV_WM_X, TEL_AVIV_WM_Y)
    assert abs(lat - TEL_AVIV_LAT) < 0.01
    assert abs(lon - TEL_AVIV_LON) < 0.01


def test_in_israel_bbox():
    assert in_israel_bbox(32.08, 34.78)  # Tel Aviv
    assert in_israel_bbox(29.55, 34.95)  # Eilat
    assert not in_israel_bbox(40.0, 34.78)  # too far north
    assert not in_israel_bbox(32.08, 50.0)  # too far east
    assert not in_israel_bbox(0.0, 0.0)


def test_build_query():
    assert build_query("רוטשילד 1", "תל אביב") == "רוטשילד 1, תל אביב"
    assert build_query("", "תל אביב") is None
    assert build_query("רוטשילד 1", "") is None
    assert build_query(None, "תל אביב") is None
    assert build_query("  ", "תל אביב") is None


def test_extract_itm_from_point_shape():
    res = {"shape": "POINT(179885 663870)"}
    assert _extract_itm(res) == (179885.0, 663870.0)


def test_extract_itm_from_xy_fallback():
    res = {"x": "179885", "y": "663870"}
    assert _extract_itm(res) == (179885.0, 663870.0)


def test_extract_itm_handles_missing():
    assert _extract_itm({}) is None
    assert _extract_itm({"shape": "garbage"}) is None
    assert _extract_itm({"shape": "POINT(abc xyz)"}) is None


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _FakeClient:
    def __init__(self, payload):
        self._payload = payload
        self.calls = 0

    def post(self, url, json=None, timeout=None):  # noqa: A002 - matches httpx signature
        self.calls += 1
        return _FakeResponse(self._payload)


def test_geocode_address_happy_path():
    payload = {
        "results": [
            {"text": "Rothschild 1, Tel Aviv", "shape": f"POINT({TEL_AVIV_WM_X} {TEL_AVIV_WM_Y})"},
        ]
    }
    client = _FakeClient(payload)
    result = geocode_address(client, "רוטשילד 1, תל אביב")
    assert isinstance(result, GeocodeResult)
    assert abs(result.lat - TEL_AVIV_LAT) < 0.01
    assert abs(result.lon - TEL_AVIV_LON) < 0.01
    assert client.calls == 1


def test_geocode_address_empty_results():
    client = _FakeClient({"results": []})
    assert geocode_address(client, "nowhere") is None


def test_geocode_address_rejects_out_of_israel():
    # Coordinates that transform to outside the Israel bbox.
    payload = {"results": [{"shape": "POINT(0 0)"}]}
    client = _FakeClient(payload)
    assert geocode_address(client, "anywhere") is None


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
