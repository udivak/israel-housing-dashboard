import hashlib
import json
from typing import Any

COLUMN_MAP: dict[str, str] = {
    # odata.org.il / Tax Authority XLSX column names
    "DEALDATE": "transaction_date",
    "DEALDATETIME": "transaction_datetime",
    "FULLADRESS": "full_address",
    "DISPLAYADRESS": "display_address",
    "GUSH": "block",
    "DEALNATUREDESCRIPTION": "property_type",
    "ASSETROOMNUM": "rooms",
    "FLOORNO": "floor",
    "DEALAMOUNT": "price",
    "NEWPROJECTTEXT": "new_project_text",
    "PROJECTNAME": "project_name",
    "BUILDINGYEAR": "building_year",
    "YEARBUILT": "year_built",
    "BUILDINGFLOORS": "building_floors",
    "KEYVALUE": "key_value",
    "TYPE": "type",
    "POLYGON_ID": "polygon_id",
    "TREND_IS_NEGATIVE": "trend_is_negative",
    "TREND_FORMAT": "trend_format",
    "city_name": "city",
    "street": "street",
    # Govmap JSON field names
    "dealAmount": "price",
    "dealDate": "transaction_date",
    "propertyTypeDescription": "property_type",
    "assetArea": "area_sqm",
    "floorNumber": "floor",
    "addressDescription": "full_address",
    "objectid": "object_id",
    "dealNatureDescription": "property_type",
    "assetRoomNum": "rooms",
    "newProjectText": "new_project_text",
    "projectName": "project_name",
    "buildingYear": "building_year",
    "buildingFloors": "building_floors",
    "polygonId": "polygon_id",
}


def normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    """Map raw API/XLSX field names to canonical schema field names."""
    return {COLUMN_MAP.get(k, k): v for k, v in row.items()}


def content_hash(payload: dict[str, Any]) -> str:
    """Deterministic SHA-256 of a dict, used for deduplication."""
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()
