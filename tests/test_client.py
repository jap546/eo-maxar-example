"""Tests for APIClient."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from eo_maxar.client import APIClient
from eo_maxar.models import STACCollection, STACItem, TileJSON
from tests.conftest import (
    SAMPLE_COLLECTION_DATA,
    SAMPLE_COLLECTIONS_LIST_DATA,
    SAMPLE_ITEM_DATA,
    SAMPLE_ITEMS_PAGE_DATA,
    SAMPLE_MOSAIC_REGISTER_DATA,
    SAMPLE_TILEJSON_DATA,
    make_mock_response,
)


class TestAPIClientContextManager:
    def test_context_manager_closes_client(self) -> None:
        with APIClient() as client:
            assert client.http_client is not None
        # After exiting, the httpx client should be closed (no exception raised)

    def test_enter_returns_self(self) -> None:
        client = APIClient()
        assert client.__enter__() is client
        client.close()


class TestGetAllCollections:
    def test_returns_collection_ids(self) -> None:
        mock_response = make_mock_response(SAMPLE_COLLECTIONS_LIST_DATA)
        with patch.object(APIClient, "__init__", lambda self: None):
            client = APIClient()
            client.http_client = MagicMock()
            client.http_client.get.return_value = mock_response

            result = client.get_all_collections()

        assert result == [
            "maxar-open-data__turkey-earthquake-2023",
            "maxar-open-data__morocco-earthquake-2023",
        ]

    def test_handles_pagination(self) -> None:
        page1 = {
            "collections": [{"id": "collection-1"}],
            "links": [
                {"rel": "next", "href": "http://localhost:8081/collections?page=2"}
            ],
        }
        page2 = {
            "collections": [{"id": "collection-2"}],
            "links": [],
        }
        with patch.object(APIClient, "__init__", lambda self: None):
            client = APIClient()
            client.http_client = MagicMock()
            client.http_client.get.side_effect = [
                make_mock_response(page1),
                make_mock_response(page2),
            ]

            result = client.get_all_collections()

        assert result == ["collection-1", "collection-2"]
        assert client.http_client.get.call_count == 2

    def test_raises_on_request_error(self) -> None:
        with patch.object(APIClient, "__init__", lambda self: None):
            client = APIClient()
            mock_http = MagicMock()
            mock_request = MagicMock()
            mock_request.url = "http://localhost:8081/collections"
            mock_http.get.side_effect = httpx.RequestError(
                "Connection refused", request=mock_request
            )
            client.http_client = mock_http

            with pytest.raises(httpx.RequestError):
                client.get_all_collections()


class TestGetCollection:
    def test_returns_validated_collection(self) -> None:
        mock_response = make_mock_response(SAMPLE_COLLECTION_DATA)
        with patch.object(APIClient, "__init__", lambda self: None):
            client = APIClient()
            client.http_client = MagicMock()
            client.http_client.get.return_value = mock_response

            result = client.get_collection("maxar-open-data__turkey-earthquake-2023")

        assert isinstance(result, STACCollection)
        assert result.id == "maxar-open-data__turkey-earthquake-2023"


class TestGetCollectionItems:
    def test_returns_all_items_single_page(self) -> None:
        mock_response = make_mock_response(SAMPLE_ITEMS_PAGE_DATA)
        with patch.object(APIClient, "__init__", lambda self: None):
            client = APIClient()
            client.http_client = MagicMock()
            client.http_client.get.return_value = mock_response

            result = client.get_collection_items("turkey-earthquake-2023")

        assert len(result) == 1
        assert isinstance(result[0], STACItem)

    def test_pagination_passes_limit_only_on_first_request(self) -> None:
        page1 = {
            "type": "FeatureCollection",
            "features": [SAMPLE_ITEM_DATA],
            "links": [{"rel": "next", "href": "http://localhost:8081/items?token=xyz"}],
        }
        page2 = {
            "type": "FeatureCollection",
            "features": [SAMPLE_ITEM_DATA],
            "links": [],
        }
        with patch.object(APIClient, "__init__", lambda self: None):
            client = APIClient()
            client.http_client = MagicMock()
            client.http_client.get.side_effect = [
                make_mock_response(page1),
                make_mock_response(page2),
            ]

            result = client.get_collection_items("turkey-earthquake-2023")

        assert len(result) == 2
        # First call should include limit param, second should not
        first_call_kwargs = client.http_client.get.call_args_list[0][1]
        second_call_kwargs = client.http_client.get.call_args_list[1][1]
        assert first_call_kwargs.get("params") is not None
        assert second_call_kwargs.get("params") is None


class TestRegisterMosaic:
    def test_returns_search_id(self) -> None:
        mock_response = make_mock_response(SAMPLE_MOSAIC_REGISTER_DATA)
        with patch.object(APIClient, "__init__", lambda self: None):
            client = APIClient()
            client.http_client = MagicMock()
            client.http_client.post.return_value = mock_response

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

    def test_payload_structure(self) -> None:
        mock_response = make_mock_response(SAMPLE_MOSAIC_REGISTER_DATA)
        with patch.object(APIClient, "__init__", lambda self: None):
            client = APIClient()
            client.http_client = MagicMock()
            client.http_client.post.return_value = mock_response

            client.register_mosaic(
                collection_id="turkey-earthquake-2023",
                bbox=[36.0, 37.0, 36.5, 37.5],
                filter_args={"op": "lt", "args": []},
                name="Pre-event",
            )

        call_kwargs = client.http_client.post.call_args[1]
        payload = call_kwargs["json"]
        assert payload["filter-lang"] == "cql2-json"
        assert payload["metadata"]["name"] == "Pre-event"
        assert payload["metadata"]["bounds"] == [36.0, 37.0, 36.5, 37.5]


class TestGetTileJSON:
    def test_returns_tilejson(self) -> None:
        mock_response = make_mock_response(SAMPLE_TILEJSON_DATA)
        with patch.object(APIClient, "__init__", lambda self: None):
            client = APIClient()
            client.http_client = MagicMock()
            client.http_client.get.return_value = mock_response

            result = client.get_tilejson("abc123")

        assert isinstance(result, TileJSON)
        assert result.minzoom == 12
        assert result.maxzoom == 22

    def test_uses_default_asset_from_settings(self) -> None:
        mock_response = make_mock_response(SAMPLE_TILEJSON_DATA)
        with patch.object(APIClient, "__init__", lambda self: None):
            client = APIClient()
            client.http_client = MagicMock()
            client.http_client.get.return_value = mock_response

            client.get_tilejson("abc123")

        call_kwargs = client.http_client.get.call_args[1]
        assert call_kwargs["params"]["assets"] == "visual"
