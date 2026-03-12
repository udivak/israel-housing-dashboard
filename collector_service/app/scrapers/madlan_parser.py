from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from bs4 import BeautifulSoup


def extract_listing_id_from_url(url: str) -> str | None:
    """Extract Madlan's internal numeric listing ID from a listing URL.

    e.g. 'https://www.madlan.co.il/listing/123456789' -> '123456789'
    """
    if not url:
        return None
    m = re.search(r"/listing/(\d+)", url)
    return m.group(1) if m else None


def normalize_price(raw: str) -> int | None:
    """Convert a Hebrew price string to a plain integer (ILS).

    '₪1,250,000' -> 1250000
    '1.5M' -> None  (unparseable; handled safely)
    """
    if not raw:
        return None
    cleaned = re.sub(r"[^\d]", "", raw)
    return int(cleaned) if cleaned else None


def normalize_rooms(raw: str) -> float | None:
    """Extract a room count from a Hebrew label.

    '3.5 חדרים' -> 3.5
    'סטודיו' -> None
    """
    if not raw:
        return None
    m = re.search(r"(\d+(?:[.,]\d+)?)", raw)
    if not m:
        return None
    # Normalise both decimal separators to '.'
    return float(m.group(1).replace(",", "."))


def normalize_area(raw: str) -> int | None:
    """Extract floor area in m² from a Hebrew label.

    '85 מ"ר' -> 85
    """
    if not raw:
        return None
    m = re.search(r"(\d+)", raw)
    return int(m.group(1)) if m else None


def normalize_floor(raw: str) -> int | None:
    """Extract a floor number from a Hebrew label.

    'קומה 4 מתוך 8' -> 4
    'קרקע' -> 0
    'מרתף' -> -1
    '4' -> 4
    """
    if not raw:
        return None
    if "קרקע" in raw:
        return 0
    if "מרתף" in raw:
        return -1
    m = re.search(r"(-?\d+)", raw)
    return int(m.group(1)) if m else None


def safe_text(soup: BeautifulSoup, selector: str) -> str:
    """Return stripped inner text of the first matching element, or ''."""
    el = soup.select_one(selector)
    return el.get_text(strip=True) if el else ""


def extract_listing_card(card_html: str, selectors: dict[str, str]) -> dict[str, Any]:
    """Parse a single listing card HTML fragment into a normalised dict.

    All numeric fields are converted to their proper Python types.
    Missing or unparseable values are stored as None (not omitted) so that
    downstream consumers can distinguish 'not present' from 'zero'.
    """
    soup = BeautifulSoup(card_html, "lxml")

    link_el = soup.select_one(selectors["listing_link"])
    listing_url: str | None = link_el["href"] if link_el and link_el.has_attr("href") else None
    listing_id = extract_listing_id_from_url(listing_url or "")

    return {
        "listing_id": listing_id,
        "listing_url": listing_url,
        "price": normalize_price(safe_text(soup, selectors["price"])),
        "address": safe_text(soup, selectors["address"]) or None,
        "rooms": normalize_rooms(safe_text(soup, selectors["rooms"])),
        "area_sqm": normalize_area(safe_text(soup, selectors["area"])),
        "floor": normalize_floor(safe_text(soup, selectors["floor"])),
        "property_type": safe_text(soup, selectors["property_type"]) or None,
        "neighborhood": safe_text(soup, selectors["neighborhood"]) or None,
    }


def extract_listing_detail(page_html: str, selectors: dict[str, str]) -> dict[str, Any]:
    """Parse a listing detail page for extended fields not available on the card.

    Returns a dict that is merged into the card data dict in the scraper.
    """
    soup = BeautifulSoup(page_html, "lxml")

    image_urls: list[str] = [
        img["src"]
        for img in soup.select(selectors["image_gallery"])
        if img.get("src")
    ]

    return {
        "description": safe_text(soup, selectors["description"]) or None,
        "agent_name": safe_text(soup, selectors["agent_name"]) or None,
        "agent_phone": safe_text(soup, selectors["agent_phone"]) or None,
        "listing_date": safe_text(soup, selectors["listing_date"]) or None,
        "total_floors": normalize_floor(safe_text(soup, selectors["total_floors"])),
        "image_urls": image_urls,
    }


def build_content_hash(payload: dict[str, Any]) -> str:
    """Return a deterministic sha256 hex digest of the canonical JSON payload.

    Matches the hashing pattern used in odata_il.py.  The hash is computed
    over the dedup key dict (listing_id + price + address) rather than the
    full payload so that non-semantic changes (e.g. image URL rotation) do
    not create spurious new records, while real changes (price update) do.
    """
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()
