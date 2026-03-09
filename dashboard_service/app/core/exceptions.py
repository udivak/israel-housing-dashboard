"""Custom HTTP exceptions for the Dashboard Service."""

from fastapi import HTTPException


class GeoDataNotFoundError(HTTPException):
    """Raised when no geospatial data is found for the given query."""

    def __init__(self, detail: str = "No features found for the specified bounding box") -> None:
        super().__init__(status_code=404, detail=detail)


class LayerNotFoundError(HTTPException):
    """Raised when a requested layer does not exist."""

    def __init__(self, layer_id: str) -> None:
        super().__init__(status_code=404, detail=f"Layer '{layer_id}' not found")


class InvalidBBoxError(HTTPException):
    """Raised when bounding box parameters are invalid."""

    def __init__(self, detail: str = "Invalid bounding box parameters") -> None:
        super().__init__(status_code=400, detail=detail)
