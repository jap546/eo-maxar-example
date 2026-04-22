"""Tests for MaxarCollection."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

from eo_maxar.collection import MaxarCollection
from eo_maxar.models import STACCollection, STACItem, TileJSON
from tests.conftest import (
    SAMPLE_COLLECTION_DATA,
    SAMPLE_TILEJSON_DATA,
)


def _make_mock_client(
    collection_data: dict | None = None,
    item_data: dict | None = None,
    tilejson_data: dict | None = None,
    search_id: str = "abc123",
) -> MagicMock:
    client = MagicMock()
    if collection_data:
        client.get_collection.return_value = STACCollection.model_validate(
            collection_data
        )
    if item_data:
        client.get_collection_items.return_value = [STACItem.model_validate(item_data)]
    if tilejson_data:
        client.get_tilejson.return_value = TileJSON.model_validate(tilejson_data)
        client.get_item_tilejson.return_value = TileJSON.model_validate(tilejson_data)
    client.register_mosaic.return_value = search_id
    return client


class TestMaxarCollectionCreate:
    def test_create_factory_method(self) -> None:
        collection = MaxarCollection.create("turkey-earthquake-2023")
        assert collection.collection_id == "turkey-earthquake-2023"
        assert collection._client is not None
        assert collection._visualizer is not None
        collection._client.close()

    def test_constructor_accepts_injected_dependencies(self) -> None:
        mock_client = MagicMock()
        mock_visualizer = MagicMock()
        collection = MaxarCollection(
            "turkey-earthquake-2023",
            client=mock_client,
            visualizer=mock_visualizer,
        )
        assert collection._client is mock_client
        assert collection._visualizer is mock_visualizer


class TestMaxarCollectionInfo:
    def test_info_calls_get_collection(self) -> None:
        mock_client = _make_mock_client(collection_data=SAMPLE_COLLECTION_DATA)
        collection = MaxarCollection(
            "maxar-open-data__turkey-earthquake-2023", client=mock_client
        )
        info = collection.info
        assert isinstance(info, STACCollection)
        mock_client.get_collection.assert_called_once_with(
            "maxar-open-data__turkey-earthquake-2023"
        )

    def test_info_is_cached(self) -> None:
        mock_client = _make_mock_client(collection_data=SAMPLE_COLLECTION_DATA)
        collection = MaxarCollection(
            "maxar-open-data__turkey-earthquake-2023", client=mock_client
        )
        _ = collection.info
        _ = collection.info
        # cached_property means the client method is only called once
        mock_client.get_collection.assert_called_once()


class TestGetMosaicTilejson:
    def test_pre_period_uses_lt_operator(self) -> None:
        mock_client = _make_mock_client(tilejson_data=SAMPLE_TILEJSON_DATA)
        collection = MaxarCollection("test-collection", client=mock_client)
        event_date = datetime(2023, 2, 6, tzinfo=UTC)

        collection._get_mosaic_tilejson([36.0, 37.0, 36.5, 37.5], event_date, "pre")

        call_args = mock_client.register_mosaic.call_args
        filter_args = call_args[0][2]
        assert filter_args["op"] == "lt"
        assert call_args[0][3] == "Pre-event"

    def test_post_period_uses_ge_operator(self) -> None:
        mock_client = _make_mock_client(tilejson_data=SAMPLE_TILEJSON_DATA)
        collection = MaxarCollection("test-collection", client=mock_client)
        event_date = datetime(2023, 2, 6, tzinfo=UTC)

        collection._get_mosaic_tilejson([36.0, 37.0, 36.5, 37.5], event_date, "post")

        call_args = mock_client.register_mosaic.call_args
        filter_args = call_args[0][2]
        assert filter_args["op"] == "ge"
        assert call_args[0][3] == "Post-event"

    def test_event_date_formatted_correctly(self) -> None:
        mock_client = _make_mock_client(tilejson_data=SAMPLE_TILEJSON_DATA)
        collection = MaxarCollection("test-collection", client=mock_client)
        event_date = datetime(2023, 2, 6, 12, 30, 0, tzinfo=UTC)

        collection._get_mosaic_tilejson([36.0, 37.0, 36.5, 37.5], event_date, "pre")

        call_args = mock_client.register_mosaic.call_args
        filter_args = call_args[0][2]
        assert filter_args["args"][1] == "2023-02-06T12:30:00Z"
