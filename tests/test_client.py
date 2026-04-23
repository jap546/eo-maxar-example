"""Tests for APIClient."""

import json

import httpx
import pytest
import respx

from eo_maxar.client import APIClient
from eo_maxar.config import settings
from eo_maxar.models import STACCollection, STACItem, TileJSON
from tests.conftest import (
    SAMPLE_COLLECTION_DATA,
    SAMPLE_COLLECTIONS_LIST_DATA,
    SAMPLE_ITEM_DATA,
    SAMPLE_ITEMS_PAGE_DATA,
    SAMPLE_MOSAIC_REGISTER_DATA,
    SAMPLE_TILEJSON_DATA,
)


class TestAPIClientContextManager:
    def test_context_manager_closes_client(self) -> None:
        with APIClient() as client:
            assert client.http_client is not None
            assert not client.http_client.is_closed
        assert client.http_client.is_closed

    def test_enter_returns_self(self) -> None:
        client = APIClient()
        assert client.__enter__() is client
        client.close()


class TestGetAllCollections:
    @respx.mock
    def test_returns_collection_ids(self) -> None:
        respx.get(url__startswith=f"{settings.stac_api_url}/collections").respond(
            json=SAMPLE_COLLECTIONS_LIST_DATA
        )
        with APIClient() as client:
            result = client.get_all_collections()

        assert result == [
            "maxar-open-data__turkey-earthquake-2023",
            "maxar-open-data__morocco-earthquake-2023",
        ]

    @respx.mock
    def test_handles_pagination(self) -> None:
        page1 = {
            "collections": [{"id": "collection-1"}],
            "links": [{"rel": "next", "href": f"{settings.stac_api_url}/collections?page=2"}],
        }
        page2 = {
            "collections": [{"id": "collection-2"}],
            "links": [],
        }

        def get_page(request):
            if "page=2" in str(request.url):
                return httpx.Response(200, json=page2)
            return httpx.Response(200, json=page1)

        respx.get(url__startswith=f"{settings.stac_api_url}/collections").mock(side_effect=get_page)

        with APIClient() as client:
            result = client.get_all_collections()

        assert result == ["collection-1", "collection-2"]

    @respx.mock
    def test_raises_on_request_error(self) -> None:
        respx.get(url__startswith=f"{settings.stac_api_url}/collections").mock(
            side_effect=httpx.RequestError("Connection refused")
        )

        with APIClient() as client, pytest.raises(httpx.RequestError) as _:
            client.get_all_collections()


class TestGetCollection:
    @respx.mock
    def test_returns_validated_collection(self) -> None:
        respx.get(
            url__startswith=f"{settings.stac_api_url}/collections/maxar-open-data__turkey-earthquake-2023"
        ).respond(json=SAMPLE_COLLECTION_DATA)
        with APIClient() as client:
            result = client.get_collection("maxar-open-data__turkey-earthquake-2023")

        assert isinstance(result, STACCollection)
        assert result.id == "maxar-open-data__turkey-earthquake-2023"


class TestGetCollectionItems:
    @respx.mock
    def test_returns_all_items_single_page(self) -> None:
        respx.get(
            url__startswith=f"{settings.stac_api_url}/collections/turkey-earthquake-2023/items"
        ).respond(json=SAMPLE_ITEMS_PAGE_DATA)
        with APIClient() as client:
            result = client.get_collection_items("turkey-earthquake-2023")

        assert len(result) == 1
        assert isinstance(result[0], STACItem)

    @respx.mock
    def test_pagination_passes_limit_only_on_first_request(self) -> None:
        page1 = {
            "type": "FeatureCollection",
            "features": [SAMPLE_ITEM_DATA],
            "links": [{"rel": "next", "href": f"{settings.stac_api_url}/items?token=xyz"}],
        }
        page2 = {
            "type": "FeatureCollection",
            "features": [SAMPLE_ITEM_DATA],
            "links": [],
        }

        req1 = respx.get(
            url__startswith=f"{settings.stac_api_url}/collections/turkey-earthquake-2023/items"
        ).respond(json=page1)
        req2 = respx.get(url__startswith=f"{settings.stac_api_url}/items").respond(json=page2)

        with APIClient() as client:
            result = client.get_collection_items("turkey-earthquake-2023")

        assert len(result) == 2
        assert req1.called
        assert req2.called

        assert "limit=" in str(req1.calls[0].request.url)
        assert "limit=" not in str(req2.calls[0].request.url)


class TestRegisterMosaic:
    @respx.mock
    def test_returns_search_id(self) -> None:
        route = respx.post(url__startswith=f"{settings.raster_api_url}/searches/register").respond(
            json=SAMPLE_MOSAIC_REGISTER_DATA
        )
        with APIClient() as client:
            result = client.register_mosaic(
                collection_id="turkey-earthquake-2023",
                bbox=[36.0, 37.0, 36.5, 37.5],
                filter_args={
                    "op": "lt",
                    "args": [{"property": "datetime"}, "2023-02-06T00:00:00Z"],
                },
                name="Pre-event",
            )

        assert result == "abc123"
        assert route.called

    @respx.mock
    def test_payload_structure(self) -> None:
        route = respx.post(url__startswith=f"{settings.raster_api_url}/searches/register").respond(
            json=SAMPLE_MOSAIC_REGISTER_DATA
        )
        with APIClient() as client:
            client.register_mosaic(
                collection_id="turkey-earthquake-2023",
                bbox=[36.0, 37.0, 36.5, 37.5],
                filter_args={"op": "lt", "args": []},
                name="Pre-event",
            )

        assert route.called
        payload = json.loads(route.calls[0].request.content)
        assert payload["filter-lang"] == "cql2-json"
        assert payload["metadata"]["name"] == "Pre-event"
        assert payload["metadata"]["bounds"] == [36.0, 37.0, 36.5, 37.5]


class TestGetTileJSON:
    @respx.mock
    def test_returns_tilejson(self) -> None:
        respx.get(
            url__startswith=f"{settings.raster_api_url}/searches/abc123/{settings.tilejson_path}"
        ).respond(json=SAMPLE_TILEJSON_DATA)
        with APIClient() as client:
            result = client.get_tilejson("abc123")

        assert isinstance(result, TileJSON)
        assert result.minzoom == 12
        assert result.maxzoom == 22

    @respx.mock
    def test_uses_default_asset_from_settings(self) -> None:
        route = respx.get(
            url__startswith=f"{settings.raster_api_url}/searches/abc123/{settings.tilejson_path}"
        ).respond(json=SAMPLE_TILEJSON_DATA)
        with APIClient() as client:
            client.get_tilejson("abc123")

        assert route.called
        assert "assets=visual" in str(route.calls[0].request.url)


class TestGetItemTileJSON:
    @respx.mock
    def test_returns_item_tilejson(self) -> None:
        route = respx.get(
            url__startswith=f"{settings.raster_api_url}/collections/collection-id/items/item-id/{settings.tilejson_path}"
        ).respond(json=SAMPLE_TILEJSON_DATA)
        with APIClient() as client:
            result = client.get_item_tilejson("collection-id", "item-id", "visual")

        assert isinstance(result, TileJSON)
        assert result.minzoom == 12
        assert result.maxzoom == 22

        assert route.called
        assert "assets=visual" in str(route.calls[0].request.url)
