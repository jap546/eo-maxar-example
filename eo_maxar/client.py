import httpx

from eo_maxar.config import settings
from eo_maxar.models import (
    MosaicRegisterResponse,
    STACCollection,
    STACItem,
    TileJSON,
)


class APIClient:
    """Client for interacting with the STAC and Raster APIs."""

    def __init__(self) -> None:
        self.http_client = httpx.Client()

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
                print(f"An error occurred while requesting {e.request.url!r}.")
                return []

        return collection_ids

    def get_collection(self, collection_id: str) -> STACCollection:
        """Retrieve and validate metadata for a specific STAC collection."""
        url: str | None = f"{settings.stac_api_url}/collections/{collection_id}"
        response = self.http_client.get(url)
        response.raise_for_status()
        return STACCollection.model_validate_json(response.content)  # type: ignore  # noqa: PGH003, RUF100

    def get_collection_items(self, collection_id: str) -> list[STACItem]:
        """Retrieve all STAC items for a collection, handling pagination."""
        items_url: str | None = (
            f"{settings.stac_api_url}/collections/{collection_id}/items"
        )
        all_items = []
        x = 0
        while items_url:
            if x == 0:
                response = self.http_client.get(items_url, params={"limit": 100})
            else:
                response = self.http_client.get(items_url)
            response.raise_for_status()
            items = response.json()
            all_items.extend(items["features"])
            next_link_obj = next(
                filter(lambda link: link["rel"] == "next", items["links"]), None
            )
            items_url = next_link_obj["href"] if next_link_obj else None
            x += 1

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
        validated_response = MosaicRegisterResponse.model_validate_json(
            response.content
        )
        return validated_response.id  # type: ignore # noqa: PGH003, RUF100

    def get_tilejson(self, search_id: str, asset: str = "visual") -> TileJSON:
        """Fetch TileJSON metadata for a registered mosaic search."""
        url = f"{settings.raster_api_url}/searches/{search_id}/{settings.tilejson_path}"
        params = {"assets": asset, "minzoom": 12, "maxzoom": 22}
        response = self.http_client.get(url, params=params)
        response.raise_for_status()
        return TileJSON.model_validate_json(response.content)  # type: ignore # noqa: PGH003, RUF100

    def get_item_tilejson(
        self, collection_id: str, item_id: str, asset: str = "visual"
    ) -> TileJSON:
        """Fetch TileJSON metadata for a single STAC item."""
        url = f"{settings.raster_api_url}/collections/{collection_id}/items/{item_id}/{settings.tilejson_path}"  # noqa: E501
        params = {"assets": asset, "minzoom": 12, "maxzoom": 22}
        response = self.http_client.get(url, params=params)
        response.raise_for_status()
        return TileJSON.model_validate_json(response.content)  # type: ignore # noqa: PGH003, RUF100

    def close(self) -> None:
        """Closes the HTTP client session."""
        self.http_client.close()
