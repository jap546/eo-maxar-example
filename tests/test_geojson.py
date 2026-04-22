"""Tests for GeoJSON helper functions."""

from eo_maxar.geojson import bbox_to_polygon_geometry, bboxes_to_feature_collection


class TestBboxToPolygonGeometry:
    def test_returns_polygon_type(self) -> None:
        result = bbox_to_polygon_geometry([36.0, 37.0, 36.5, 37.5])
        assert result["type"] == "Polygon"

    def test_coordinates_form_closed_ring(self) -> None:
        bbox = [36.0, 37.0, 36.5, 37.5]
        result = bbox_to_polygon_geometry(bbox)
        coords = result["coordinates"][0]
        assert coords[0] == coords[-1], "Ring must be closed (first == last point)"

    def test_coordinates_corners(self) -> None:
        min_lon, min_lat, max_lon, max_lat = 36.0, 37.0, 36.5, 37.5
        result = bbox_to_polygon_geometry([min_lon, min_lat, max_lon, max_lat])
        coords = result["coordinates"][0]
        assert [min_lon, min_lat] in coords
        assert [max_lon, min_lat] in coords
        assert [max_lon, max_lat] in coords
        assert [min_lon, max_lat] in coords

    def test_negative_coordinates(self) -> None:
        result = bbox_to_polygon_geometry([-10.0, -5.0, 10.0, 5.0])
        assert result["type"] == "Polygon"
        coords = result["coordinates"][0]
        assert [-10.0, -5.0] in coords


class TestBboxesToFeatureCollection:
    def test_returns_feature_collection_type(self) -> None:
        bbox = [36.0, 37.0, 36.5, 37.5]
        result = bboxes_to_feature_collection([bbox], bbox)
        assert result["type"] == "FeatureCollection"

    def test_feature_count_matches_input(self) -> None:
        bboxes = [
            [36.0, 37.0, 36.5, 37.5],
            [37.0, 38.0, 37.5, 38.5],
        ]
        result = bboxes_to_feature_collection(bboxes, bboxes[0])
        assert len(result["features"]) == 2

    def test_main_bbox_is_marked(self) -> None:
        main = [36.0, 37.0, 36.5, 37.5]
        other = [37.0, 38.0, 37.5, 38.5]
        result = bboxes_to_feature_collection([main, other], main)
        features = result["features"]
        assert features[0]["properties"]["is_main"] is True
        assert features[1]["properties"]["is_main"] is False

    def test_each_feature_has_polygon_geometry(self) -> None:
        bboxes = [[36.0, 37.0, 36.5, 37.5]]
        result = bboxes_to_feature_collection(bboxes, bboxes[0])
        assert result["features"][0]["geometry"]["type"] == "Polygon"
