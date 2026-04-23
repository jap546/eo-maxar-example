"""Shared fixtures for the test suite."""

import pytest

SAMPLE_COLLECTION_DATA = {
    "id": "maxar-open-data__turkey-earthquake-2023",
    "title": "Turkey Earthquake 2023",
    "description": "Maxar open data for the 2023 Turkey earthquake.",
    "extent": {
        "spatial": {"bbox": [[36.0, 37.0, 37.5, 37.5]]},
        "temporal": {"interval": [["2023-02-06T00:00:00Z", None]]},
    },
    "links": [
        {"rel": "self", "href": "http://localhost:8081/collections/turkey-earthquake"}
    ],
    "item_assets": {},
}

SAMPLE_ITEM_DATA = {
    "type": "Feature",
    "stac_version": "1.0.0",
    "id": "item-001",
    "bbox": [36.0, 37.0, 36.5, 37.5],
    "geometry": {
        "type": "Polygon",
        "coordinates": [
            [
                [36.0, 37.0],
                [36.5, 37.0],
                [36.5, 37.5],
                [36.0, 37.5],
                [36.0, 37.0],
            ]
        ],
    },
    "properties": {"datetime": "2023-02-06T10:00:00Z"},
    "assets": {"visual": {"href": "s3://example/visual.tif", "type": "image/tiff"}},
    "links": [],
    "collection": "maxar-open-data__turkey-earthquake-2023",
}

SAMPLE_TILEJSON_DATA = {
    "tilejson": "2.2.0",
    "name": "Pre-event",
    "tiles": ["http://localhost:8082/searches/abc123/tiles/{z}/{x}/{y}"],
    "minzoom": 12,
    "maxzoom": 22,
    "bounds": [36.0, 37.0, 36.5, 37.5],
}

SAMPLE_MOSAIC_REGISTER_DATA = {"id": "abc123"}

SAMPLE_COLLECTIONS_LIST_DATA = {
    "collections": [
        {"id": "maxar-open-data__turkey-earthquake-2023"},
        {"id": "maxar-open-data__morocco-earthquake-2023"},
    ],
    "links": [],
}

SAMPLE_ITEMS_PAGE_DATA = {
    "type": "FeatureCollection",
    "features": [SAMPLE_ITEM_DATA],
    "links": [],
}


@pytest.fixture
def sample_collection_data() -> dict:
    return SAMPLE_COLLECTION_DATA


@pytest.fixture
def sample_item_data() -> dict:
    return SAMPLE_ITEM_DATA


@pytest.fixture
def sample_tilejson_data() -> dict:
    return SAMPLE_TILEJSON_DATA
