"""
geo_utils.py
============
Utility פונקציות גיאוגרפיות — נטולות תלות ב-Mongo או ב-env vars, בטוח לייבא
מכל מקום (כולל סקריפטי backfill).

מאחסן:
  - CITY_CENTROIDS: מילון של 54 ערים ישראליות גדולות → (lat, lon).
  - reverse_geocode_city(lat, lon): מחזיר את שם העיר הקרובה ביותר.

הרשימה מבוססת על NADLAN_CITIES ב-collector_service/app/scrapers/nadlan_gov.py
(הערים שה-scraper סרק) + שמות קנוניים. ה-centroids מ-Photon (osm_value=city/town,
country=Israel).
"""
from __future__ import annotations

import math

# (lat, lon) — מסודר לפי גודל אוכלוסייה משוערך.
CITY_CENTROIDS: dict[str, tuple[float, float]] = {
    "תל אביב -יפו":        (32.0853, 34.7818),  # spelling aligned with odata_il_nadlan
    "ירושלים":             (31.7788, 35.2258),
    "חיפה":                (32.8191, 34.9984),
    "באר שבע":             (31.2457, 34.7925),
    "ראשון לציון":         (31.9636, 34.8101),
    "פתח תקווה":           (32.0906, 34.8765),
    "אשדוד":               (31.7957, 34.6489),
    "נתניה":               (32.3137, 34.8668),
    "בני ברק":             (32.0874, 34.8324),
    "רמת גן":              (32.0687, 34.8247),
    "בת ים":               (32.0155, 34.7505),
    "רחובות":              (31.8921, 34.8005),
    "אשקלון":              (31.6653, 34.5650),
    "חולון":               (32.0193, 34.7804),
    "הרצלייה":             (32.1656, 34.8469),  # spelling aligned with odata_il_nadlan (double yud)
    "כפר סבא":             (32.1802, 34.9153),
    "חדרה":                (32.4370, 34.9198),
    "מודיעין-מכבים-רעות":  (31.9086, 35.0069),
    "לוד":                 (31.9489, 34.8885),
    "רמלה":                (31.9280, 34.8623),
    "קרית גת":             (31.6094, 34.7712),  # canonical spelling (ktiv chaser) — matches odata/tax_authority
    "עכו":                 (32.9148, 35.0823),
    "נצרת":                (32.7066, 35.3048),
    "טבריה":               (32.7939, 35.5329),
    "צפת":                 (32.9707, 35.4996),
    "אילת":                (29.5540, 34.9453),
    "קרית אונו":           (32.0592, 34.8594),  # canonical (ktiv chaser)
    "יהוד":                (32.0332, 34.8908),
    "אור יהודה":           (32.0270, 34.8630),
    "גבעת שמואל":          (32.0769, 34.8525),
    "הוד השרון":           (32.1499, 34.8851),
    "אלעד":                (32.0501, 34.9522),
    "ראש העין":            (32.0953, 34.9533),
    "רמת השרון":           (32.1397, 34.8359),
    "גבעתיים":             (32.0730, 34.8113),
    "רעננה":               (32.1860, 34.8678),
    "ביתר עילית":          (31.6991, 35.1043),
    "מעלה אדומים":         (31.7706, 35.2987),
    "עפולה":               (32.6076, 35.2891),
    "כרמיאל":              (32.9159, 35.2934),
    "נהריה":               (33.0149, 35.1017),
    "דימונה":              (31.0709, 35.0412),
    "טמרה":                (32.8548, 35.1967),
    "שפרעם":               (32.8064, 35.1713),
    "נתיבות":              (31.4214, 34.5884),
    "אופקים":              (31.3068, 34.6182),
    "קרית שמונה":          (33.2121, 35.5716),  # canonical (ktiv chaser)
    "קרית מוצקין":         (32.8391, 35.0804),
    "קרית ביאליק":         (32.8367, 35.0893),
    "קרית ים":             (32.8467, 35.0702),
    "מגדל העמק":           (32.6766, 35.2413),
    "יקנעם":               (32.6605, 35.1086),
    "זכרון יעקב":          (32.5730, 34.9512),
    "חצור הגלילית":        (32.9792, 35.5433),
}


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


def reverse_geocode_city(
    lat: float | None,
    lon: float | None,
    max_km: float = 25.0,
) -> str | None:
    """
    Resolve `(lat, lon)` to the nearest city in :data:`CITY_CENTROIDS`.

    Returns ``None`` when input is missing or the nearest centroid is further
    than ``max_km`` (so points outside our coverage don't get misassigned).

    Used by `normalize_nadlan_gov()` כתחליף ל-`SETTLEMENT_ID_TO_NAME` השבור
    (ראה FEATURES_TEST.md §8.5 — הטבלה תייגה 51K רשומות עם שם עיר שגוי).
    """
    if lat is None or lon is None:
        return None
    best_name: str | None = None
    best_dist = float("inf")
    for name, (clat, clon) in CITY_CENTROIDS.items():
        d = _haversine_km(lat, lon, clat, clon)
        if d < best_dist:
            best_dist = d
            best_name = name
    if best_name is not None and best_dist <= max_km:
        return best_name
    return None
