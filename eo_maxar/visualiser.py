from datetime import datetime
from typing import Any

import ipyleaflet

from eo_maxar.config import settings
from eo_maxar.geojson import bboxes_to_feature_collection
from eo_maxar.models import STACCollection, STACItem, TileJSON

# Map style constants
_MAIN_BBOX_STYLE: dict[str, Any] = {
    "fillOpacity": 0,
    "weight": 2,
    "color": "black",
    "dashArray": "5, 5",
}
_FEATURE_STYLE: dict[str, Any] = {"fillOpacity": 0.1, "weight": 1, "color": "blue"}
_PRE_EVENT_COLOR = "blue"
_POST_EVENT_COLOR = "red"
_PRE_POST_BASE_STYLE: dict[str, Any] = {"fillOpacity": 0.5, "weight": 0.2}


class MapVisualizer:
    """Handles the creation of ipyleaflet maps for visualizing geospatial data."""

    def _create_base_map(
        self,
        bounds: list[float],
        zoom: int | None = None,
        overrides: dict | None = None,
    ) -> ipyleaflet.Map:
        """Creates a default ipyleaflet map centered on the given bounds."""
        min_lon, min_lat, max_lon, max_lat = bounds
        default_kwargs: dict[str, Any] = {
            "center": [(min_lat + max_lat) / 2, (min_lon + max_lon) / 2],
            "zoom": zoom if zoom is not None else settings.default_zoom,
            "layout": settings.map_layout,
        }
        if overrides:
            default_kwargs.update(overrides)
        return ipyleaflet.Map(**default_kwargs)

    def create_tile_map(
        self, tilejson: TileJSON, map_kwargs: dict | None = None
    ) -> ipyleaflet.Map:
        """Creates a map with a single TileLayer from a TileJSON model."""
        bounds = tilejson.bounds
        m = self._create_base_map(bounds, overrides=map_kwargs)
        tile_layer = ipyleaflet.TileLayer(
            url=tilejson.tiles[0],
            min_zoom=tilejson.minzoom,
            max_zoom=tilejson.maxzoom,
            bounds=[[bounds[1], bounds[0]], [bounds[3], bounds[2]]],
        )
        m.add(tile_layer)
        return m

    def create_split_map(
        self,
        left_tilejson: TileJSON,
        right_tilejson: TileJSON,
        map_kwargs: dict | None = None,
    ) -> ipyleaflet.Map:
        """Creates a split map to compare two TileJSON layers."""
        left_bounds = left_tilejson.bounds
        m = self._create_base_map(left_bounds, overrides=map_kwargs)

        left_layer = ipyleaflet.TileLayer(url=left_tilejson.tiles[0])
        right_layer = ipyleaflet.TileLayer(url=right_tilejson.tiles[0])

        split_control = ipyleaflet.SplitMapControl(
            left_layer=left_layer, right_layer=right_layer
        )
        m.add(split_control)
        return m

    def create_collection_footprints_map(
        self, collection: STACCollection, map_kwargs: dict | None = None
    ) -> ipyleaflet.Map:
        """Creates a map visualizing the bounding boxes of a collection's spatial extent."""  # noqa: E501
        main_bbox = collection.extent.spatial.bbox[0]
        m = self._create_base_map(main_bbox, overrides=map_kwargs)

        feature_collection = bboxes_to_feature_collection(
            collection.extent.spatial.bbox, main_bbox
        )

        def style_callback(feature: dict) -> dict:
            if feature["properties"]["is_main"]:
                return _MAIN_BBOX_STYLE
            return _FEATURE_STYLE

        geo_json_layer = ipyleaflet.GeoJSON(
            data=feature_collection, style_callback=style_callback
        )
        m.add(geo_json_layer)
        return m

    def create_pre_post_event_map(
        self,
        items: list[STACItem],
        event_date: datetime,
        map_kwargs: dict | None = None,
    ) -> ipyleaflet.Map:
        """Creates a map styling STAC item footprints based on an event date."""
        if not items:
            raise ValueError("Item list cannot be empty.")

        m = self._create_base_map(items[0].bbox, overrides=map_kwargs)

        def style_callback(feature: dict) -> dict:
            item_dt = datetime.fromisoformat(
                feature["properties"]["datetime"].replace("Z", "+00:00")
            )
            style: dict[str, Any] = dict(_PRE_POST_BASE_STYLE)
            style["fillColor"] = (
                _PRE_EVENT_COLOR if item_dt < event_date else _POST_EVENT_COLOR
            )
            return style

        geojson_data = {
            "type": "FeatureCollection",
            "features": [item.model_dump(by_alias=True) for item in items],
        }
        geo_json_layer = ipyleaflet.GeoJSON(
            data=geojson_data, style_callback=style_callback
        )
        m.add(geo_json_layer)
        return m
