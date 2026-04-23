"""Tests for Pydantic models."""

import pytest
from pydantic import ValidationError

from eo_maxar.models import (
    MosaicRegisterResponse,
    STACCollection,
    STACItem,
    TileJSON,
)
from tests.conftest import (
    SAMPLE_COLLECTION_DATA,
    SAMPLE_ITEM_DATA,
    SAMPLE_TILEJSON_DATA,
)


class TestSTACCollection:
    def test_valid_collection(self, sample_collection_data: dict) -> None:
        collection = STACCollection.model_validate(sample_collection_data)
        assert collection.id == "maxar-open-data__turkey-earthquake-2023"
        assert collection.title == "Turkey Earthquake 2023"
        assert collection.extent.spatial.bbox == [[36.0, 37.0, 37.5, 37.5]]
        assert collection.extent.temporal.interval == [["2023-02-06T00:00:00Z", None]]

    def test_missing_required_field(self) -> None:
        data = {k: v for k, v in SAMPLE_COLLECTION_DATA.items() if k != "extent"}
        with pytest.raises(ValidationError):
            STACCollection.model_validate(data)

    def test_optional_description_defaults_to_none(self) -> None:
        data = {k: v for k, v in SAMPLE_COLLECTION_DATA.items() if k != "description"}
        collection = STACCollection.model_validate(data)
        assert collection.description is None

    def test_item_assets_defaults_to_empty_dict(self) -> None:
        data = {k: v for k, v in SAMPLE_COLLECTION_DATA.items() if k != "item_assets"}
        collection = STACCollection.model_validate(data)
        assert collection.item_assets == {}

    def test_populate_by_name_with_alias(self) -> None:
        # item_assets field has alias="item_assets" — populate_by_name allows both
        collection = STACCollection.model_validate(SAMPLE_COLLECTION_DATA)
        assert collection.item_assets == {}


class TestSTACItem:
    def test_valid_item(self, sample_item_data: dict) -> None:
        item = STACItem.model_validate(sample_item_data)
        assert item.id == "item-001"
        assert item.stac_version == "1.0.0"
        assert item.bbox == [36.0, 37.0, 36.5, 37.5]
        assert item.collection == "maxar-open-data__turkey-earthquake-2023"

    def test_bbox_wrong_length_raises(self) -> None:
        data = {**SAMPLE_ITEM_DATA, "bbox": [36.0, 37.0, 36.5]}
        with pytest.raises(ValidationError, match="bbox must have exactly 4 elements"):
            STACItem.model_validate(data)

    def test_bbox_too_many_elements_raises(self) -> None:
        data = {**SAMPLE_ITEM_DATA, "bbox": [36.0, 37.0, 36.5, 37.5, 100.0]}
        with pytest.raises(ValidationError, match="bbox must have exactly 4 elements"):
            STACItem.model_validate(data)

    def test_null_geometry_allowed(self) -> None:
        data = {**SAMPLE_ITEM_DATA, "geometry": None}
        item = STACItem.model_validate(data)
        assert item.geometry is None

    def test_model_dump_by_alias(self, sample_item_data: dict) -> None:
        item = STACItem.model_validate(sample_item_data)
        dumped = item.model_dump(by_alias=True)
        assert dumped["type"] == "Feature"
        assert "bbox" in dumped


class TestTileJSON:
    def test_valid_tilejson(self, sample_tilejson_data: dict) -> None:
        tj = TileJSON.model_validate(sample_tilejson_data)
        assert tj.tilejson == "2.2.0"
        assert tj.minzoom == 12
        assert tj.maxzoom == 22
        assert len(tj.tiles) == 1

    def test_bounds_wrong_length_raises(self) -> None:
        data = {**SAMPLE_TILEJSON_DATA, "bounds": [36.0, 37.0, 36.5]}
        with pytest.raises(ValidationError, match="bounds must have exactly 4 elements"):
            TileJSON.model_validate(data)

    def test_optional_name_defaults_to_none(self) -> None:
        data = {k: v for k, v in SAMPLE_TILEJSON_DATA.items() if k != "name"}
        tj = TileJSON.model_validate(data)
        assert tj.name is None


class TestMosaicRegisterResponse:
    def test_valid_response(self) -> None:
        response = MosaicRegisterResponse.model_validate({"id": "abc123"})
        assert response.id == "abc123"

    def test_missing_id_raises(self) -> None:
        with pytest.raises(ValidationError):
            MosaicRegisterResponse.model_validate({})
