import logging

import httpx

from eo_maxar.config import settings
from eo_maxar.models import (
    MosaicRegisterResponse,
    STACCollection,
    STACItem,
    TileJSON,
)

logger = logging.getLogger(__name__)


class APIClient:
    """Client for interacting with the STAC and Raster APIs."""

    def __init__(self) -> None:
        self.http_client = httpx.Client()

    def __enter__(self) -> "APIClient":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def get_all_collections(self) -> list[str]:
        """Fetch all collection names from the STAC API, handling pagination."""
        url: str | None = f"{settings.stac_api_url}/collections"
        collection_ids: list[str] = []

        while url:
            try:
                response = self.http_client.get(url)
                response.raise_for_status()
                data = response.json()
                collection_ids.extend(c["id"] for c in data.get("collections", []))
                next_link = next(
                    (
                        link["href"]
                        for link in data.get("links", [])
                        if link["rel"] == "next"
                    ),
                    None,
                )
                url = next_link
            except httpx.RequestError as e:
                logger.error("An error occurred while requesting %s.", e.request.url)
                raise

        return collection_ids

    def get_collection(self, collection_id: str) -> STACCollection:
        """Retrieve and validate metadata for a specific STAC collection."""
        url = f"{settings.stac_api_url}/collections/{collection_id}"
        response = self.http_client.get(url)
        response.raise_for_status()
        return STACCollection.model_validate_json(response.text)

    def get_collection_items(self, collection_id: str) -> list[STACItem]:
        """Retrieve all STAC items for a collection, handling pagination."""
        url: str | None = f"{settings.stac_api_url}/collections/{collection_id}/items"
        params: dict | None = {"limit": settings.pagination_limit}
        all_items: list[dict] = []

        while url:
            response = self.http_client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            all_items.extend(data["features"])
            next_link = next(
                (link for link in data["links"] if link["rel"] == "next"),
                None,
            )
            url = next_link["href"] if next_link else None
            params = None  # Only pass params on first request

        return [STACItem.model_validate(item) for item in all_items]

    def register_mosaic(
        self, collection_id: str, bbox: list[float], filter_args: dict, name: str
    ) -> str:
        """Register a mosaic search with the raster API and return its search ID."""
        url = f"{settings.raster_api_url}/searches/register"
        base_filter = {
            "op": "and",
            "args": [
                {"op": "in", "args": [{"property": "collection"}, [collection_id]]},
                filter_args,
            ],
        }
        payload = {
            "filter-lang": "cql2-json",
            "filter": base_filter,
            "sortby": [{"field": "tile:clouds_percent", "direction": "asc"}],
            "metadata": {"name": name, "bounds": bbox},
        }
        response = self.http_client.post(url, json=payload)
        response.raise_for_status()
        validated_response = MosaicRegisterResponse.model_validate_json(response.text)
        return validated_response.id

    def get_tilejson(self, search_id: str, asset: str | None = None) -> TileJSON:
        """Fetch TileJSON metadata for a registered mosaic search."""
        url = f"{settings.raster_api_url}/searches/{search_id}/{settings.tilejson_path}"
        params = {
            "assets": asset or settings.default_asset,
            "minzoom": settings.min_zoom,
            "maxzoom": settings.max_zoom,
        }
        response = self.http_client.get(url, params=params)
        response.raise_for_status()
        return TileJSON.model_validate_json(response.text)

    def get_item_tilejson(
        self, collection_id: str, item_id: str, asset: str | None = None
    ) -> TileJSON:
        """Fetch TileJSON metadata for a single STAC item."""
        url = (
            f"{settings.raster_api_url}/collections/{collection_id}"
            f"/items/{item_id}/{settings.tilejson_path}"
        )
        params = {
            "assets": asset or settings.default_asset,
            "minzoom": settings.min_zoom,
            "maxzoom": settings.max_zoom,
        }
        response = self.http_client.get(url, params=params)
        response.raise_for_status()
        return TileJSON.model_validate_json(response.text)

    def close(self) -> None:
        """Closes the HTTP client session."""
        self.http_client.close()
