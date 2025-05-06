from typing import Any

from pydantic import BaseModel


class Collection(BaseModel):
    """Represents selected information from a single Maxar STAC collection."""

    id: str
    title: str
    description: str | None
    extent: dict[str, Any]
    links: list[dict[str, Any]] | None


class Item(BaseModel):
    """Represents selected information from a single STAC item from a collection."""

    id: str
    bbox: list[float]
    properties: dict
    assets: dict[str, Any]
