"""Tests for MapVisualizer."""

from datetime import UTC, datetime

import pytest

from eo_maxar.models import STACCollection, STACItem, TileJSON
from eo_maxar.visualiser import (
    _FEATURE_STYLE,
    _MAIN_BBOX_STYLE,
    _POST_EVENT_COLOR,
    _PRE_EVENT_COLOR,
    MapVisualizer,
)
from tests.conftest import (
    SAMPLE_COLLECTION_DATA,
    SAMPLE_ITEM_DATA,
    SAMPLE_TILEJSON_DATA,
)


@pytest.fixture
def visualizer() -> MapVisualizer:
    return MapVisualizer()


@pytest.fixture
def tilejson() -> TileJSON:
    return TileJSON.model_validate(SAMPLE_TILEJSON_DATA)


@pytest.fixture
def collection() -> STACCollection:
    return STACCollection.model_validate(SAMPLE_COLLECTION_DATA)


@pytest.fixture
def item() -> STACItem:
    return STACItem.model_validate(SAMPLE_ITEM_DATA)


class TestCreateBaseMap:
    def test_center_is_computed_from_bounds(self, visualizer: MapVisualizer) -> None:
        bounds = [36.0, 37.0, 37.0, 38.0]
        m = visualizer._create_base_map(bounds)
        # center should be [(37+38)/2, (36+37)/2] = [37.5, 36.5]
        assert m.center == [37.5, 36.5]

    def test_default_zoom_applied(self, visualizer: MapVisualizer) -> None:
        bounds = [36.0, 37.0, 37.0, 38.0]
        m = visualizer._create_base_map(bounds)
        from eo_maxar.config import settings

        assert m.zoom == settings.default_zoom

    def test_custom_zoom_applied(self, visualizer: MapVisualizer) -> None:
        bounds = [36.0, 37.0, 37.0, 38.0]
        m = visualizer._create_base_map(bounds, zoom=12)
        assert m.zoom == 12

    def test_overrides_applied(self, visualizer: MapVisualizer) -> None:
        bounds = [36.0, 37.0, 37.0, 38.0]
        m = visualizer._create_base_map(bounds, overrides={"zoom": 5})
        assert m.zoom == 5


class TestCollectionFootprintsStyleCallback:
    """Test the style_callback logic in create_collection_footprints_map."""

    def test_main_bbox_gets_main_style(
        self, visualizer: MapVisualizer, collection: STACCollection
    ) -> None:
        import ipyleaflet

        m = visualizer.create_collection_footprints_map(collection)
        layer = next(
            layer for layer in m.layers if isinstance(layer, ipyleaflet.GeoJSON)
        )

        main_feature = {"properties": {"is_main": True}}
        other_feature = {"properties": {"is_main": False}}

        assert layer.style_callback(main_feature) == _MAIN_BBOX_STYLE
        assert layer.style_callback(other_feature) == _FEATURE_STYLE


class TestPrePostEventStyleCallback:
    """Test the date-based colour logic in create_pre_post_event_map."""

    def test_pre_event_item_gets_blue(
        self, visualizer: MapVisualizer, item: STACItem
    ) -> None:
        import ipyleaflet

        event_date = datetime(2023, 2, 6, tzinfo=UTC)
        m = visualizer.create_pre_post_event_map([item], event_date)
        layer = next(
            layer for layer in m.layers if isinstance(layer, ipyleaflet.GeoJSON)
        )

        pre_feature = {"properties": {"datetime": "2023-02-05T10:00:00Z"}}
        post_feature = {"properties": {"datetime": "2023-02-07T10:00:00Z"}}

        assert layer.style_callback(pre_feature)["fillColor"] == _PRE_EVENT_COLOR
        assert layer.style_callback(post_feature)["fillColor"] == _POST_EVENT_COLOR

    def test_empty_items_raises(self, visualizer: MapVisualizer) -> None:
        with pytest.raises(ValueError, match="Item list cannot be empty"):
            visualizer.create_pre_post_event_map([], datetime(2023, 2, 6, tzinfo=UTC))


class TestCreateSplitMap:
    def test_returns_map_with_split_control(
        self, visualizer: MapVisualizer, tilejson: TileJSON
    ) -> None:
        import ipyleaflet

        m = visualizer.create_split_map(tilejson, tilejson)
        assert isinstance(m, ipyleaflet.Map)
        split_controls = [
            ctrl for ctrl in m.controls if isinstance(ctrl, ipyleaflet.SplitMapControl)
        ]
        assert len(split_controls) == 1


class TestCreateTileMap:
    def test_returns_map_with_tile_layer(
        self, visualizer: MapVisualizer, tilejson: TileJSON
    ) -> None:
        import ipyleaflet

        m = visualizer.create_tile_map(tilejson)
        assert isinstance(m, ipyleaflet.Map)
        tile_layers = [
            layer for layer in m.layers if isinstance(layer, ipyleaflet.TileLayer)
        ]
        # Should have the OSM base layer + our custom tile layer
        assert len(tile_layers) >= 1


class TestCreateCollectionFootprintsMap:
    def test_returns_map(
        self, visualizer: MapVisualizer, collection: STACCollection
    ) -> None:
        import ipyleaflet

        m = visualizer.create_collection_footprints_map(collection)
        assert isinstance(m, ipyleaflet.Map)
