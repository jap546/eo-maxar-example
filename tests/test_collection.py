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

    def test_items_calls_get_collection_items(self) -> None:
        from tests.conftest import SAMPLE_ITEM_DATA

        mock_client = _make_mock_client(item_data=SAMPLE_ITEM_DATA)
        collection = MaxarCollection("test-collection", client=mock_client)
        items = collection.items

        assert isinstance(items, list)
        assert len(items) == 1
        mock_client.get_collection_items.assert_called_once_with("test-collection")


class TestMaxarCollectionMaps:
    def test_collection_bbox_map(self) -> None:
        mock_client = _make_mock_client(collection_data=SAMPLE_COLLECTION_DATA)
        collection = MaxarCollection("test-collection", client=mock_client)
        collection._visualizer.create_collection_footprints_map = MagicMock()

        collection.collection_bbox_map()
        collection._visualizer.create_collection_footprints_map.assert_called_once_with(
            collection.info, None
        )

    def test_pre_post_map(self) -> None:
        from tests.conftest import SAMPLE_ITEM_DATA

        mock_client = _make_mock_client(item_data=SAMPLE_ITEM_DATA)
        # Mock items to bypass the client call to get_collection_items
        collection = MaxarCollection("test-collection", client=mock_client)
        collection.__dict__[
            "items"
        ] = []  # Just so it doesn't trigger get_collection_items
        collection._visualizer.create_pre_post_event_map = MagicMock()

        event_date = datetime(2023, 2, 6, tzinfo=UTC)
        collection.pre_post_map(event_date)
        collection._visualizer.create_pre_post_event_map.assert_called_once_with(
            [], event_date, None
        )

    def test_single_cog_map(self) -> None:
        mock_client = _make_mock_client(tilejson_data=SAMPLE_TILEJSON_DATA)
        collection = MaxarCollection("test-collection", client=mock_client)
        collection._visualizer.create_tile_map = MagicMock()

        collection.single_cog_map("item-1", "visual")
        mock_client.get_item_tilejson.assert_called_once_with(
            "test-collection", "item-1", "visual"
        )
        collection._visualizer.create_tile_map.assert_called_once()

    def test_pre_event_mosaic_map(self) -> None:
        mock_client = _make_mock_client(tilejson_data=SAMPLE_TILEJSON_DATA)
        collection = MaxarCollection("test-collection", client=mock_client)
        collection._visualizer.create_tile_map = MagicMock()

        event_date = datetime(2023, 2, 6, tzinfo=UTC)
        collection.pre_event_mosaic_map([1, 2, 3, 4], event_date, {"zoom": 10})
        collection._visualizer.create_tile_map.assert_called_once()

    def test_post_event_mosaic_map(self) -> None:
        mock_client = _make_mock_client(tilejson_data=SAMPLE_TILEJSON_DATA)
        collection = MaxarCollection("test-collection", client=mock_client)
        collection._visualizer.create_tile_map = MagicMock()

        event_date = datetime(2023, 2, 6, tzinfo=UTC)
        collection.post_event_mosaic_map([1, 2, 3, 4], event_date, {"zoom": 10})
        collection._visualizer.create_tile_map.assert_called_once()

    def test_mosaic_split_map(self) -> None:
        mock_client = _make_mock_client(tilejson_data=SAMPLE_TILEJSON_DATA)
        collection = MaxarCollection("test-collection", client=mock_client)
        collection._visualizer.create_split_map = MagicMock()

        event_date = datetime(2023, 2, 6, tzinfo=UTC)
        collection.mosaic_split_map([1, 2, 3, 4], event_date, {"zoom": 10})
        collection._visualizer.create_split_map.assert_called_once()
        # client.register_mosaic is called twice (pre and post)
        assert mock_client.register_mosaic.call_count == 2

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
