from datetime import datetime
from functools import cached_property
from typing import Literal

import ipyleaflet

from eo_maxar.client import APIClient
from eo_maxar.models import STACCollection, STACItem, TileJSON
from eo_maxar.visualiser import MapVisualizer


class MaxarCollection:
    """A high-level interface to interact with a specific Maxar STAC collection."""

    def __init__(
        self,
        collection_id: str,
        client: APIClient | None = None,
        visualizer: MapVisualizer | None = None,
    ):
        self.collection_id = collection_id
        self._client = client or APIClient()
        self._visualizer = visualizer or MapVisualizer()

    @classmethod
    def create(cls, collection_id: str) -> "MaxarCollection":
        """Create a MaxarCollection with default client and visualizer.

        Args:
            collection_id: The STAC collection identifier.

        Returns:
            A fully wired MaxarCollection instance.
        """
        return cls(
            collection_id=collection_id,
            client=APIClient(),
            visualizer=MapVisualizer(),
        )

    @cached_property
    def info(self) -> STACCollection:
        """Lazily fetches and caches the collection's metadata."""
        return self._client.get_collection(self.collection_id)

    @cached_property
    def items(self) -> list[STACItem]:
        """Lazily fetches and caches all items within the collection."""
        return self._client.get_collection_items(self.collection_id)

    def collection_bbox_map(self, map_kwargs: dict | None = None) -> ipyleaflet.Map:
        """Creates a map showing the footprints of the entire collection."""
        return self._visualizer.create_collection_footprints_map(self.info, map_kwargs)

    def pre_post_map(self, event_date: datetime, map_kwargs: dict | None = None) -> ipyleaflet.Map:
        """Creates a map showing pre-event (blue) and post-event (red) item footprints."""
        return self._visualizer.create_pre_post_event_map(self.items, event_date, map_kwargs)

    def single_cog_map(
        self, item_id: str, asset: str | None = None, map_kwargs: dict | None = None
    ) -> ipyleaflet.Map:
        """Creates a map displaying a single Cloud Optimized GeoTIFF (COG)."""
        tilejson = self._client.get_item_tilejson(self.collection_id, item_id, asset)
        return self._visualizer.create_tile_map(tilejson, map_kwargs)

    def _get_mosaic_tilejson(
        self,
        bbox: list[float],
        event_date: datetime,
        period: Literal["pre", "post"],
    ) -> TileJSON:
        """Helper to register and fetch TileJSON for a mosaic.

        Args:
            bbox: Bounding box [min_lon, min_lat, max_lon, max_lat].
            event_date: The event date to filter imagery by.
            period: ``"pre"`` for images before the event, ``"post"`` for after.

        Returns:
            TileJSON metadata for the registered mosaic.
        """
        if period == "pre":
            op, name = "lt", "Pre-event"
        else:
            op, name = "ge", "Post-event"

        event_date_str = event_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        filter_args = {"op": op, "args": [{"property": "datetime"}, event_date_str]}
        search_id = self._client.register_mosaic(self.collection_id, bbox, filter_args, name)
        return self._client.get_tilejson(search_id)

    def pre_event_mosaic_map(
        self, bbox: list[float], event_date: datetime, map_kwargs: dict | None = None
    ) -> ipyleaflet.Map:
        """Creates a map of a pre-event mosaic for a given bounding box."""
        tilejson = self._get_mosaic_tilejson(bbox, event_date, "pre")
        return self._visualizer.create_tile_map(tilejson, map_kwargs)

    def post_event_mosaic_map(
        self, bbox: list[float], event_date: datetime, map_kwargs: dict | None = None
    ) -> ipyleaflet.Map:
        """Creates a map of a post-event mosaic for a given bounding box."""
        tilejson = self._get_mosaic_tilejson(bbox, event_date, "post")
        return self._visualizer.create_tile_map(tilejson, map_kwargs)

    def mosaic_split_map(
        self, bbox: list[float], event_date: datetime, map_kwargs: dict | None = None
    ) -> ipyleaflet.Map:
        """Creates a split-view map comparing pre- and post-event mosaics."""
        pre_tilejson = self._get_mosaic_tilejson(bbox, event_date, "pre")
        post_tilejson = self._get_mosaic_tilejson(bbox, event_date, "post")
        return self._visualizer.create_split_map(pre_tilejson, post_tilejson, map_kwargs)
