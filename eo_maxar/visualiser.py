from datetime import datetime
from typing import Any

import ipyleaflet

from eo_maxar.config import settings
from eo_maxar.models import STACCollection, STACItem, TileJSON


class MapVisualizer:
    """Handles the creation of ipyleaflet maps for visualizing geospatial data."""

    def _create_base_map(
        self, bounds: list[float], zoom: int = 8, overrides: dict | None = None
    ) -> ipyleaflet.Map:
        """Creates a default ipyleaflet map centered on the given bounds."""
        default_kwargs = {
            "center": [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2],
            "zoom": zoom,
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

        feature_collection = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [bbox[0], bbox[1]],
                                [bbox[2], bbox[1]],
                                [bbox[2], bbox[3]],
                                [bbox[0], bbox[3]],
                                [bbox[0], bbox[1]],
                            ]
                        ],
                    },
                    "properties": {"is_main": bbox == main_bbox},
                }
                for bbox in collection.extent.spatial.bbox
            ],
        }

        def style_callback(feature: dict) -> dict:
            if feature["properties"]["is_main"]:
                return {
                    "fillOpacity": 0,
                    "weight": 2,
                    "color": "black",
                    "dashArray": "5, 5",
                }
            return {"fillOpacity": 0.1, "weight": 1, "color": "blue"}

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
            raise ValueError("Item list cannot be empty.")  # noqa: RUF100, TRY003

        m = self._create_base_map(items[0].bbox, overrides=map_kwargs)

        def style_callback(feature: dict) -> dict:
            item_dt = datetime.fromisoformat(
                feature["properties"]["datetime"].replace("Z", "+00:00")
            )

            style: dict[str, Any] = {"fillOpacity": 0.5, "weight": 0.2}

            if item_dt < event_date:
                style["fillColor"] = "blue"  # Pre-event
            else:
                style["fillColor"] = "red"  # Post-event
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
