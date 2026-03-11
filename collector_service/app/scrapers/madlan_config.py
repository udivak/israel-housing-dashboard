from __future__ import annotations

BASE_URL = "https://www.madlan.co.il"
FOR_SALE_URL_TEMPLATE = BASE_URL + "/for-sale/{city_slug}"

# All city slugs extracted from sitemap /for-sale/{city}-ישראל entries.
# "ישראל" (national) is intentionally omitted — city-level slugs give finer
# control, enable resumable crawls, and avoid pagination limits on a single
# massive result set.  Add new cities here as they appear in the sitemap.
CITY_SLUGS: list[str] = [
    "חיפה-ישראל",
    "ירושלים-ישראל",
    "חולון-ישראל",
    "תל-אביב-יפו-ישראל",
    "רמת-גן-ישראל",
    "פתח-תקווה-ישראל",
    "ראשון-לציון-ישראל",
    "אשדוד-ישראל",
    "באר-שבע-ישראל",
    "נתניה-ישראל",
    "בני-ברק-ישראל",
    "אשקלון-ישראל",
    "חדרה-ישראל",
    "רחובות-ישראל",
    "בת-ים-ישראל",
    "כפר-סבא-ישראל",
    "הרצליה-ישראל",
    "רמת-השרון-ישראל",
    "גבעתיים-ישראל",
    "רעננה-ישראל",
    "מודיעין-מכבים-רעות-ישראל",
    "לוד-ישראל",
    "רמלה-ישראל",
    "קריית-גת-ישראל",
    "עכו-ישראל",
    "נצרת-ישראל",
    "טבריה-ישראל",
    "צפת-ישראל",
    "אילת-ישראל",
    "קריית-אונו-ישראל",
    "יהוד-ישראל",
    "אור-יהודה-ישראל",
    "גבעת-שמואל-ישראל",
    "הוד-השרון-ישראל",
    "אלעד-ישראל",
    "ראש-העין-ישראל",
    "ביתר-עילית-ישראל",
    "מעלה-אדומים-ישראל",
    "ביתר-ישראל",
]

# CSS / ARIA selectors.
# All selectors are centralised here so DOM changes only require a single-file
# edit.  data-testid attributes are preferred over class names because React
# may change hashed class names between deployments.
SELECTORS: dict[str, str] = {
    # Results page — listing cards
    "listing_card": "[data-testid='feed-item']",
    "listing_link": "a[href*='/listing/']",
    "price": "[data-testid='price']",
    "address": "[data-testid='address']",
    "rooms": "[data-testid='rooms']",
    "area": "[data-testid='floor-size']",
    "floor": "[data-testid='floor']",
    "property_type": "[data-testid='asset-classification']",
    "neighborhood": "[data-testid='neighborhood']",
    # Results page — navigation
    "next_page": "button[aria-label='הבא'], a[aria-label='הבא']",
    "no_results": "[data-testid='no-results']",
    # Detail page — extended fields
    "description": "[data-testid='description']",
    "agent_name": "[data-testid='agent-name']",
    "agent_phone": "[data-testid='agent-phone']",
    "listing_date": "[data-testid='listing-date']",
    "image_gallery": "[data-testid='image-gallery'] img",
    "total_floors": "[data-testid='total-floors']",
}

# Playwright BrowserContext kwargs.
# These values mimic a real Israeli user and reduce fingerprinting signals.
BROWSER_CONTEXT_OPTIONS: dict = {
    "viewport": {"width": 1440, "height": 900},
    "locale": "he-IL",
    "timezone_id": "Asia/Jerusalem",
    "java_script_enabled": True,
}
