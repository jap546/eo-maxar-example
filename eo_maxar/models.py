from typing import Any

from pydantic import BaseModel, Field


class SpatialExtent(BaseModel):
    """Defines the spatial bounding box of a collection."""

    bbox: list[list[float]]


class TemporalExtent(BaseModel):
    """Defines the temporal interval of a collection."""

    interval: list[list[str | None]]


class Extent(BaseModel):
    """Combines spatial and temporal extents."""

    spatial: SpatialExtent
    temporal: TemporalExtent


class STACLink(BaseModel):
    """Represents a link in a STAC object."""

    rel: str
    href: str
    type: str | None = None
    title: str | None = None


class STACCollection(BaseModel):
    """Represents a STAC collection with detailed, validated fields."""

    id: str
    title: str
    description: str | None = None
    extent: Extent
    links: list[STACLink]
    item_assets: dict[str, Any] = Field(alias="item_assets", default={})


class STACItem(BaseModel):
    """
    Represents a STAC item, conforming to the GeoJSON Feature spec.
    """

    type: str = "Feature"
    stac_version: str
    id: str
    bbox: list[float]
    geometry: dict[str, Any] | None
    properties: dict[str, Any]
    assets: dict[str, Any]
    links: list[STACLink]
    collection: str


class TileJSON(BaseModel):
    """Represents the TileJSON response from the raster API."""

    tilejson: str
    name: str | None = None
    tiles: list[str]
    minzoom: int
    maxzoom: int
    bounds: list[float]


class MosaicRegisterResponse(BaseModel):
    """Response model for a registered mosaic search."""

    id: str
