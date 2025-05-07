import json
from datetime import datetime
from typing import Any

import httpx
import ipyleaflet
from pydantic import BaseModel

from eo_maxar.constants import (
    MAP_LAYOUT,
    RASTER_ENDPOINT,
    STAC_ENDPOINT,
    TILEJSON_ENDPOINT,
)
from eo_maxar.models import Collection, Item


def get_collections() -> list[str]:
    """Fetch all collection names from the STAC API, following pagination."""
    url = f"{STAC_ENDPOINT}/collections"
    collection_ids = []

    while url:
        response = httpx.get(url)
        response.raise_for_status()
        data = response.json()
        collection_ids.extend(c["id"] for c in data["collections"])

        next_link = next(
            (link["href"] for link in data.get("links", []) if link["rel"] == "next"),
            None,
        )
        url = next_link

    return collection_ids


class MaxarCollection(BaseModel):
    """Represents a Maxar Open Data collection.

    Attributes:
    -----------
    collection_id (str):
        Maxar Open Data collection to work with.
    """

    collection_id: str

    def get_collection_info(self) -> Collection:
        """Retrieve metadata for a specific Maxar STAC collection.

        Sends a GET request to the STAC API to fetch collection-level metadata,
        including spatial/temporal extent, description, and links. The response
        is parsed and validated into a `Collection` Pydantic model.

        Returns:
        --------
        Collection
            Validated Collection object containing metadata for a specified collection.
        """
        response = httpx.get(f"{STAC_ENDPOINT}/collections/{self.collection_id}")
        collection_data = response.json()
        return Collection.model_validate(collection_data)

    def get_collection_items(self) -> list[Item]:
        """
        Retrieve all STAC items for the current collection, handling pagination.

        Sends repeated GET requests to the STAC API to retrieve all items (features)
        belonging to the specified collection. Handles pagination automatically using
        the 'next' link in the response.

        Returns:
        --------
        list[Item]
            List of Item dictionaries representing individual assets in the collection.
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

    def _register_mosaic(
        self,
        bbox: list[float],
        datetime_op: str,
        event_date_str: str,
        name: str,
    ) -> str:
        """
        Register a mosaic search with filtering conditions and return the search ID.

        This helper function submits a search request to the Raster API endpoint using
        CQL2 filters to define temporal and spatial constraints. The resulting search is
        registered on the server, and its unique search ID is returned.

        Parameters:
        -----------
        bbox : list[float]
            The spatial bounding box of the area of interest in [minX, minY, maxX, maxY]
            format.

        datetime_op : str
            The comparison operator for filtering by datetime (e.g., "lt" for less than,
            "ge" for greater than or equal).

        event_date_str : str
            The datetime string to use for filtering (e.g., "2023-02-06T00:00:00Z").

        name : str
            Name to associate with the registered mosaic search for identification.

        Returns:
        --------
        str
            Unique ID of the registered mosaic search to retrieve associated tile data.
        """
        response = httpx.post(
            f"{RASTER_ENDPOINT}/searches/register",
            data=json.dumps({
                "filter-lang": "cql2-json",
                "filter": {
                    "op": "and",
                    "args": [
                        {
                            "op": "in",
                            "args": [{"property": "collection"}, [self.collection_id]],
                        },
                        {
                            "op": datetime_op,
                            "args": [{"property": "datetime"}, event_date_str],
                        },
                    ],
                },
                "sortby": [{"field": "tile:clouds_percent", "direction": "asc"}],
                "metadata": {"name": name, "bounds": bbox},
            }),
        )
        return response.json()["id"]

    def _get_tilejson(self, search_id: str) -> dict:
        """Fetch a TileJSON metadata dictionary for a given search ID and asset type.

        This helper sends a GET request to the raster service to retrieve TileJSON
        metadata, which describes how to render tiles for a mosaic or item (including
        tile URLs, bounds, zoom levels, etc.).

        Parameters:
        -----------
        search_id : str
            ID of the registered mosaic or item search obtained from `_register_mosaic`.

        asset : str
            The asset type to render (e.g., "visual", "analytic", etc.).

        Returns:
        --------
        dict
            A dictionary conforming to the TileJSON format, including tile URLs, bounds,
            min/max zoom, and other rendering metadata.
        """
        return httpx.get(
            f"{RASTER_ENDPOINT}/searches/{search_id}/{TILEJSON_ENDPOINT}",
            params={"assets": "visual", "minzoom": 12, "maxzoom": 22},
        ).json()

    def mosaic_split_map(
        self,
        bbox: list[float],
        event_date: datetime,
        *,
        map_kwargs: dict | None = None,
    ) -> ipyleaflet.Map:
        """Create a split-view map comparing pre- and post-event mosaics side by side.

        Uses ipyleaflet.SplitMapControl to let users swipe between pre-post imagery.

        Parameters:
        -----------
        bbox : list[float]
            Bounding box [minX, minY, maxX, maxY] to define the area of interest.

        event_date : datetime
            The event date to split imagery around.

        map_kwargs : dict | None
            Optional keyword arguments to customize the map display.

        Returns:
        --------
        ipyleaflet.Map
            An interactive split map showing pre- and post-event imagery.
        """
        event_date_str = event_date.strftime("%Y-%m-%dT%H:%M:%SZ")

        search_id_pre = self._register_mosaic(bbox, "lt", event_date_str, "Pre event")
        tilejson_pre = self._get_tilejson(search_id_pre)

        search_id_post = self._register_mosaic(bbox, "ge", event_date_str, "Post event")
        tilejson_post = self._get_tilejson(search_id_post)

        bounds = tilejson_pre["bounds"]
        m = ipyleaflet.Map(**self._set_default_map_kwargs(bounds, overrides=map_kwargs))

        left_layer = ipyleaflet.TileLayer(
            url=tilejson_pre["tiles"][0],
            min_zoom=tilejson_pre["minzoom"],
            max_zoom=tilejson_pre["maxzoom"],
            bounds=[[bounds[1], bounds[0]], [bounds[3], bounds[2]]],
        )

        bounds_post = tilejson_post["bounds"]
        right_layer = ipyleaflet.TileLayer(
            url=tilejson_post["tiles"][0],
            min_zoom=tilejson_post["minzoom"],
            max_zoom=tilejson_post["maxzoom"],
            bounds=[[bounds_post[1], bounds_post[0]], [bounds_post[3], bounds_post[2]]],
        )

        m.add_control(
            ipyleaflet.SplitMapControl(left_layer=left_layer, right_layer=right_layer)
        )
        return m

    def pre_post_map(
        self,
        items: list[dict],
        event_date: datetime,
        map_kwargs: dict | None = None,
    ) -> ipyleaflet.Map:
        """Create a map to visualize STAC items styled by pre-post event.

        Items earlier than the event date are shown in blue; those on/after the event
        date are red.

        Parameters:
        -----------
        items : list[dict]
            A list of STAC item features to be visualized.

        event_date : datetime
            The event date used to split pre- and post-event imagery.

        map_kwargs : dict | None
            Optional map customization parameters.

        Returns:
        --------
        ipyleaflet.Map
            A map showing the items colored by time relative to the event.
        """
        collection_info = self.get_collection_info()

        bounds = collection_info.extent["spatial"]["bbox"][0]

        m = ipyleaflet.Map(**self._set_default_map_kwargs(bounds, overrides=map_kwargs))

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

    def collection_bbox_map(
        self,
        map_kwargs: dict | None = None,
    ) -> ipyleaflet.Map:
        """Create an interactive map displaying the bounding box of the collection.

        Each bounding box defined in the collection's spatial extent is rendered as a
        polygon.

        The main bbox is styled with a dashed outline to differentiate it from others.

        Parameters:
        -----------
        map_kwargs : dict | None
            Optional keyword arguments to customize the ipyleaflet.Map (e.g. center).

        Returns:
        --------
        ipyleaflet.Map
            A map with bounding box geometries visualized.
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

        m = ipyleaflet.Map(**self._set_default_map_kwargs(bounds, overrides=map_kwargs))

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

    def single_cog_map(
        self,
        item_id: str,
        asset: str = "visual",
        map_kwargs: dict | None = None,
    ) -> ipyleaflet.Map:
        """Create a map displaying a single Cloud Optimized GeoTIFF asset by item ID.

        Parameters:
        -----------
        item_id : str
            The STAC item ID to retrieve imagery for.

        asset : str, default="visual"
            The asset type to visualize (e.g., "visual", "analytic").

        map_kwargs : dict | None
            Optional map customization parameters.

        Returns:
        --------
        ipyleaflet.Map
            Map centered on item's bounds with the selected asset shown as a tile layer.
        """
        tilejson = httpx.get(
            f"{RASTER_ENDPOINT}/collections/{self.collection_id}/items/{item_id}/{TILEJSON_ENDPOINT}",
            params={"assets": asset, "minzoom": 12, "maxzoom": 22},
        ).json()

        bounds = tilejson["bounds"]

        m = ipyleaflet.Map(**self._set_default_map_kwargs(bounds, overrides=map_kwargs))

        tiles = ipyleaflet.TileLayer(
            url=tilejson["tiles"][0],
            min_zoom=tilejson["minzoom"],
            max_zoom=tilejson["maxzoom"],
            bounds=[[bounds[1], bounds[0]], [bounds[3], bounds[2]]],
        )
        m.add_layer(tiles)
        return m

    def pre_event_mosaic_map(
        self,
        bbox: list[float],
        event_date: datetime,
        *,
        map_kwargs: dict | None = None,
    ) -> ipyleaflet.Map:
        """Create a mosaic map of imagery acquired before a specified event date.

        Parameters:
        -----------
        bbox : list[float]
            Bounding box [minX, minY, maxX, maxY] to spatially constrain the mosaic.

        event_date : datetime
            The datetime used to filter images taken before the event.

        map_kwargs : dict | None
            Optional keyword arguments to customize the map display.

        Returns:
        --------
        ipyleaflet.Map
            A map displaying the pre-event mosaic of the collection.
        """
        event_date_str = event_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        search_id = self._register_mosaic(bbox, "lt", event_date_str, "Pre event")
        tilejson = self._get_tilejson(search_id)
        return self._make_map_from_tilejson(tilejson, map_kwargs)

    def post_event_mosaic_map(
        self,
        bbox: list[float],
        event_date: datetime,
        *,
        map_kwargs: dict | None = None,
    ) -> ipyleaflet.Map:
        """Create a mosaic map of imagery acquired on or after a specified event date.

        Parameters:
        -----------
        bbox : list[float]
            Bounding box [minX, minY, maxX, maxY] to spatially constrain the mosaic.

        event_date : datetime
            The datetime used to filter images taken on or after the event.

        map_kwargs : dict | None
            Optional keyword arguments to customize the map display.

        Returns:
        --------
        ipyleaflet.Map
            A map displaying the post-event mosaic of the collection.
        """
        event_date_str = event_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        search_id = self._register_mosaic(bbox, "ge", event_date_str, "Post event")
        tilejson = self._get_tilejson(search_id)
        return self._make_map_from_tilejson(tilejson, map_kwargs)

    def _make_map_from_tilejson(
        self, tilejson: dict, map_kwargs: dict | None
    ) -> ipyleaflet.Map:
        """
        Create an ipyleaflet.Map instance using a TileJSON dictionary.

        This helper sets up an interactive map centered on the TileJSON's bounding box
        and adds a TileLayer based on the provided tile URL and zoom levels. Optionally,
        it allows for user-provided map customization via `map_kwargs`.

        Parameters:
        -----------
        tilejson : dict
            A TileJSON dictionary containing metadata such as tile URL templates,
            bounds, and min/max zoom levels. Typically returned by `_get_tilejson`.

        map_kwargs : dict | None
            Optional keyword arguments to override default map configuration
            (e.g., `{"zoom": 14}` or `{"center": [lat, lon]}`).

        Returns:
        --------
        ipyleaflet.Map
            An interactive ipyleaflet map with the tile layer rendered according to the
            TileJSON specification.
        """
        bounds = tilejson["bounds"]

        m = ipyleaflet.Map(**self._set_default_map_kwargs(bounds, overrides=map_kwargs))

        m.add_layer(
            ipyleaflet.TileLayer(
                url=tilejson["tiles"][0],
                min_zoom=tilejson["minzoom"],
                max_zoom=tilejson["maxzoom"],
                bounds=[[bounds[1], bounds[0]], [bounds[3], bounds[2]]],
            )
        )
        return m

    def _set_default_map_kwargs(
        self, bounds: list[float], zoom: int = 10, overrides: dict | None = None
    ) -> dict[str, Any]:
        """Create map keyword arguments for ipyleaflet.Map with optional user overrides.

        Computes the map center based on a bounding box and applies a default zoom and
        layout.

        If `overrides` are provided, they will take precedence over the defaults (e.g.
        to override zoom level or center).

        Parameters:
        -----------
        bounds : list[float]
            Bounding box [minX, minY, maxX, maxY] used to compute map center.

        zoom : int, default=10
            The default zoom level to use if not overridden.

        overrides : dict | None
            Optional dictionary of keyword arguments to override the defaults (e.g.
            {"zoom": 14}).

        Returns:
        --------
        dict[str, Any]
            Dictionary of keyword arguments for initializing an ipyleaflet.Map instance.
        """
        default_kwargs = {
            "center": [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2],
            "zoom": zoom,
            "layout": MAP_LAYOUT,
        }
        return {**default_kwargs, **(overrides or {})}
