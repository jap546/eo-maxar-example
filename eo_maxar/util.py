import json
from datetime import datetime
from typing import Any, Optional

import httpx
import ipyleaflet
from pydantic import BaseModel

from eo_maxar.constants import (
    MAP_LAYOUT,
    RASTER_ENDPOINT,
    STAC_ENDPOINT,
    TILEJSON_ENDPOINT,
)


class Item(BaseModel):
    """Represents a single item in a collection."""

    id: str
    bbox: list[float]
    properties: dict
    assets: dict[str, Any]


class Collection(BaseModel):
    """Represents a single collection of items."""

    id: str
    title: str
    description: Optional[str]
    extent: dict[str, Any]
    links: Optional[list[dict[str, Any]]]


def get_collections() -> list[str]:
    """Fetch collection names from the STAC API."""
    response = httpx.get(f"{STAC_ENDPOINT}/collections")
    collections = response.json()
    return [c["id"] for c in collections["collections"]]


class MaxarCollection(BaseModel):
    """Represents a Maxar Open Data collection.

    Attributes:
    -----------
    collection_id (str):
        Maxar Open Data collection to work with.
    """

    collection_id: Optional[str]

    def get_collection_info(self) -> Collection:
        """Fetch information about a specific collection.

        Returns:
        --------
        Collection: specific information from Maxar collections.
        """
        response = httpx.get(f"{STAC_ENDPOINT}/collections/{self.collection_id}")
        collection_data = response.json()
        return Collection.model_validate(collection_data)

    def get_collection_items(self) -> list[Item]:
        """Fetch all items in the collection.

        Returns:
        --------
        List[Items]: all items from a collection.
        """
        item_results = []

        url = f"{STAC_ENDPOINT}/collections/{self.collection_id}/items"
        x = 0
        while True:
            if x == 0:
                items = httpx.get(url, params={"limit": 100}).json()
            else:
                items = httpx.get(url).json()

            item_results.extend(items["features"])
            next_link = list(filter(lambda link: link["rel"] == "next", items["links"]))
            if next_link:
                url = next_link[0]["href"]
            else:
                break
            x += 1
        return item_results

    def get_main_bbox(self) -> list:
        """Helper function to get main bbox of collection.

        Returns:
        --------
        list: list of bbox coordinates of collection.
        """
        return self.get_collection_info().extent["spatial"]["bbox"][0]

    def get_temporal_extent(self) -> list:
        """Helper function to get temporal extent of collection.

        Returns:
        --------
        list: all temporal event information.
        """
        return self.get_collection_info().extent["temporal"]["interval"]

    def collection_bbox_map(
        self,
        map_kwargs: Optional[dict] = None,
    ) -> ipyleaflet.Map:
        """Create a map displaying the bounding box of the collection.

        Returns:
        --------
        ipyleaflet.Map: interactive map of collection bounding box geometries.
        """
        collection_info = self.get_collection_info()
        geojson = {
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
                    "properties": {},
                }
                for bbox in collection_info.extent["spatial"]["bbox"]
            ],
        }

        bounds = collection_info.extent["spatial"]["bbox"][0]

        if map_kwargs:
            m = ipyleaflet.Map(**map_kwargs)
        else:
            m = ipyleaflet.Map(
                center=((bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2),
                zoom=7,
                layout=MAP_LAYOUT,
            )

        def style_function(feature: dict) -> dict:
            """Takes feature dictionary and styles by main bbox vs item.

            Returns:
            --------
            dict: styling to be applied for each bbox geometry.
            """
            if feature["geometry"]["coordinates"] == [
                [
                    [bounds[0], bounds[1]],
                    [bounds[2], bounds[1]],
                    [bounds[2], bounds[3]],
                    [bounds[0], bounds[3]],
                    [bounds[0], bounds[1]],
                ]
            ]:
                return {
                    "fillOpacity": 0,
                    "weight": 2,
                    "color": "#000000",
                    "dashArray": "10,5",
                }
            return {
                "fillOpacity": 0.1,
                "weight": 0.5,
                "fillColor": "#0000ff",
            }

        geo_json = ipyleaflet.GeoJSON(data=geojson, style_callback=style_function)
        m.add_layer(geo_json)
        return m

    def pre_post_map(self, items: list[dict], event_date: datetime) -> ipyleaflet.Map:
        """Create a map that visualises items based on pre/post-event date.

        Returns:
        --------
        ipyleaflet.Map: item collections styled by pre-post event.
        """
        collection_info = self.get_collection_info()

        bounds = collection_info.extent["spatial"]["bbox"][0]

        m = ipyleaflet.Map(
            center=((bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2),
            zoom=7,
            layout=MAP_LAYOUT,
        )

        def style_function(feature: dict) -> dict:
            """Style the features based on the datetime of the item.

            Returns:
            --------
            dict: styling to be applied for each bbox geometry.
            """
            d = datetime.strptime(
                feature["properties"]["datetime"], "%Y-%m-%dT%H:%M:%SZ"
            )
            return {
                "fillOpacity": 0.5,
                "weight": 0.1,
                "fillColor": "#0000ff" if d < event_date else "#ff0000",
            }

        geo_json = ipyleaflet.GeoJSON(
            data={
                "type": "FeatureCollection",
                "features": items,
            },
            style_callback=style_function,
        )
        m.add_layer(geo_json)
        return m

    def single_cog_map(
        self,
        items: list[dict],
        item_id: str,
        asset: str = "visual",
        map_kwargs: Optional[dict] = None,
    ) -> ipyleaflet.Map:
        """Create a map for a single COG (Cloud Optimized GeoTIFF).

        Arguments:
        ----------
        items (list[dict]):
            list of dictionary collection Items.

        item_id (str):
            item_id to filter by.

        asset (str):
            relevant asset to map (e.g. visual)

        map_kwargs (Optional[dict]):
            Optional map kwargs to pass to ipyleaflet.Map instance.

        Returns:
            --------
            ipyleaflet.Map: map showing single COG file.
        """
        item = next(item for item in items if item["id"] == item_id)

        tilejson = httpx.get(
            f"{RASTER_ENDPOINT}/collections/{self.collection_id}/items/{item_id}/{TILEJSON_ENDPOINT}",
            params={"assets": asset, "minzoom": 12, "maxzoom": 22},
        ).json()

        bounds = tilejson["bounds"]

        if map_kwargs:
            m = ipyleaflet.Map(**map_kwargs)
        else:
            m = ipyleaflet.Map(
                center=((bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2),
                zoom=12,
                layout=MAP_LAYOUT,
            )

        geo_json = ipyleaflet.GeoJSON(
            data=item,
            style={"opacity": 1, "dashArray": "9", "fillOpacity": 0.0, "weight": 4},
        )
        m.add_layer(geo_json)

        tiles = ipyleaflet.TileLayer(
            url=tilejson["tiles"][0],
            min_zoom=tilejson["minzoom"],
            max_zoom=tilejson["maxzoom"],
            bounds=[[bounds[1], bounds[0]], [bounds[3], bounds[2]]],
        )
        m.add_layer(tiles)
        return m

    def mosaic_map(  # noqa: PLR0913
        self,
        items: list[dict],
        bbox: list[float],
        event_date: datetime,
        asset: str = "visual",
        *,
        pre_event: bool,
        add_item_bounds: bool = False,
        map_kwargs: Optional[dict] = None,
    ) -> ipyleaflet.Map:
        """Create a mosaic map for the collection pre/post-event.

        Arguments:
        ----------
        items (list[dict]):
            list of dictionary collection Items.

        bbox (list[float]):
            bounding box extents to create the mosaic for.

        event_date (datetime):
            date to create the mosaic before or after.

        asset (str):
            relevant asset to map (e.g. visual)

        pre_event (bool):
            pre or post event flag.

        add_item_bounds: (bool)
            add item bbox geometry, defaults to False.

        map_kwargs (Optional[dict]):
            Optional map kwargs to pass to ipyleaflet.Map instance.

        Returns:
            --------
            ipyleaflet.Map: map showing mosaic of individual COGs.
        """
        event_date_str = event_date.strftime("%Y-%m-%dT%H:%M:%SZ")

        if pre_event:
            filtered_items = list(
                filter(
                    lambda item: datetime.strptime(
                        item["properties"]["datetime"], "%Y-%m-%dT%H:%M:%SZ"
                    )
                    < event_date,
                    items,
                )
            )
        else:
            filtered_items = list(
                filter(
                    lambda item: datetime.strptime(
                        item["properties"]["datetime"], "%Y-%m-%dT%H:%M:%SZ"
                    )
                    >= event_date,
                    items,
                )
            )

        mosaic = httpx.post(
            f"{RASTER_ENDPOINT}/searches/register",
            data=json.dumps(
                {
                    "filter-lang": "cql2-json",
                    "filter": {
                        "op": "and",
                        "args": [
                            {
                                "op": "in",
                                "args": [
                                    {"property": "collection"},
                                    [self.collection_id],
                                ],
                            },
                            {
                                "op": "lt" if pre_event else "ge",
                                "args": [
                                    {"property": "datetime"},
                                    event_date_str,
                                ],
                            },
                        ],
                    },
                    "sortby": [{"field": "tile:clouds_percent", "direction": "asc"}],
                    "metadata": {
                        "name": "Pre event" if pre_event else "Post event",
                        "bounds": bbox,
                    },
                }
            ),
        ).json()

        search_id = mosaic["id"]
        tilejson = httpx.get(
            f"{RASTER_ENDPOINT}/searches/{search_id}/{TILEJSON_ENDPOINT}",
            params={"assets": asset, "minzoom": 12, "maxzoom": 22},
        ).json()

        bounds = tilejson["bounds"]
        if map_kwargs:
            m = ipyleaflet.Map(**map_kwargs)
        else:
            m = ipyleaflet.Map(
                center=((bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2),
                zoom=12,
                layout=MAP_LAYOUT,
            )

        tiles = ipyleaflet.TileLayer(
            url=tilejson["tiles"][0],
            min_zoom=tilejson["minzoom"],
            max_zoom=tilejson["maxzoom"],
            bounds=[[bounds[1], bounds[0]], [bounds[3], bounds[2]]],
        )
        m.add_layer(tiles)

        if add_item_bounds:
            geo_json = ipyleaflet.GeoJSON(
                data={"type": "FeatureCollection", "features": filtered_items},
                style={"fillOpacity": 0, "weight": 1},
            )
            m.add_layer(geo_json)
        return m

    def mosaic_split_map(  # noqa: PLR0913
        self,
        items: list[dict],
        bbox: list[float],
        event_date: datetime,
        asset: str = "visual",
        *,
        add_item_bounds: bool = False,
        map_kwargs: Optional[dict] = None,
    ) -> ipyleaflet.Map:
        """Create a mosaic map for the collection pre/post-event with split map.

        Arguments:
        ----------
        items (list[dict]):
            list of dictionary collection Items.

        bbox (list[float]):
            bounding box extents to create the mosaic for.

        event_date (datetime):
            date to create the pre and post event mosaics.

        asset (str):
            relevant asset to map (e.g. visual)

        add_item_bounds: (bool)
            add item bbox geometry, defaults to False.

        map_kwargs (Optional[dict]):
            Optional map kwargs to pass to ipyleaflet.Map instance.

        Returns:
            --------
            ipyleaflet.Map: split map showing pre/post mosaic of individual COGs.
        """
        event_date_str = event_date.strftime("%Y-%m-%dT%H:%M:%SZ")

        mosaic_pre = httpx.post(
            f"{RASTER_ENDPOINT}/searches/register",
            data=json.dumps(
                {
                    "filter-lang": "cql2-json",
                    "filter": {
                        "op": "and",
                        "args": [
                            {
                                "op": "in",
                                "args": [
                                    {"property": "collection"},
                                    [self.collection_id],
                                ],
                            },
                            {
                                "op": "lt",
                                "args": [
                                    {"property": "datetime"},
                                    event_date_str,
                                ],
                            },
                        ],
                    },
                    "sortby": [{"field": "tile:clouds_percent", "direction": "asc"}],
                    "metadata": {
                        "name": "Pre event",
                        "bounds": bbox,
                    },
                }
            ),
        ).json()

        search_id_pre = mosaic_pre["id"]
        tilejson_pre = httpx.get(
            f"{RASTER_ENDPOINT}/searches/{search_id_pre}/{TILEJSON_ENDPOINT}",
            params={"assets": asset, "minzoom": 12, "maxzoom": 22},
        ).json()

        mosaic_post = httpx.post(
            f"{RASTER_ENDPOINT}/searches/register",
            data=json.dumps(
                {
                    "filter-lang": "cql2-json",
                    "filter": {
                        "op": "and",
                        "args": [
                            {
                                "op": "in",
                                "args": [
                                    {"property": "collection"},
                                    [self.collection_id],
                                ],
                            },
                            {
                                "op": "ge",
                                "args": [
                                    {"property": "datetime"},
                                    event_date_str,
                                ],
                            },
                        ],
                    },
                    "sortby": [{"field": "tile:clouds_percent", "direction": "asc"}],
                    "metadata": {
                        "name": "Post event",
                        "bounds": bbox,
                    },
                }
            ),
        ).json()

        search_id_post = mosaic_post["id"]
        tilejson_post = httpx.get(
            f"{RASTER_ENDPOINT}/searches/{search_id_post}/{TILEJSON_ENDPOINT}",
            params={"assets": asset, "minzoom": 12, "maxzoom": 22},
        ).json()

        bounds = tilejson_pre["bounds"]

        if map_kwargs:
            m = ipyleaflet.Map(**map_kwargs)
        else:
            m = ipyleaflet.Map(
                center=((bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2),
                zoom=12,
                layout=MAP_LAYOUT,
            )

        before_layer = ipyleaflet.TileLayer(
            url=tilejson_pre["tiles"][0],
            min_zoom=tilejson_pre["minzoom"],
            max_zoom=tilejson_pre["maxzoom"],
            bounds=[[bounds[1], bounds[0]], [bounds[3], bounds[2]]],
        )

        bounds_post = tilejson_post["bounds"]
        after_layer = ipyleaflet.TileLayer(
            url=tilejson_post["tiles"][0],
            min_zoom=tilejson_post["minzoom"],
            max_zoom=tilejson_post["maxzoom"],
            bounds=[[bounds_post[1], bounds_post[0]], [bounds_post[3], bounds_post[2]]],
        )

        control = ipyleaflet.SplitMapControl(
            left_layer=before_layer, right_layer=after_layer
        )

        m.add_control(control)

        if add_item_bounds:
            geo_json = ipyleaflet.GeoJSON(
                data={
                    "type": "FeatureCollection",
                    "features": items,
                },
                style={"fillOpacity": 0, "weight": 1},
            )
            m.add_layer(geo_json)

        return m
