"""GeoJSON helper functions for building geometries and feature collections."""

from __future__ import annotations


def bbox_to_polygon_geometry(bbox: list[float]) -> dict:
    """Convert a bounding box to a GeoJSON Polygon geometry.

    Args:
        bbox: [min_lon, min_lat, max_lon, max_lat]

    Returns:
        GeoJSON Polygon geometry dict.
    """
    min_lon, min_lat, max_lon, max_lat = bbox
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [min_lon, min_lat],
                [max_lon, min_lat],
                [max_lon, max_lat],
                [min_lon, max_lat],
                [min_lon, min_lat],
            ]
        ],
    }


def bboxes_to_feature_collection(
    bboxes: list[list[float]], main_bbox: list[float]
) -> dict:
    """Convert a list of bounding boxes to a GeoJSON FeatureCollection.

    Args:
        bboxes: List of [min_lon, min_lat, max_lon, max_lat] bounding boxes.
        main_bbox: The primary bounding box, used to set the ``is_main`` property.

    Returns:
        GeoJSON FeatureCollection dict.
    """
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": bbox_to_polygon_geometry(bbox),
                "properties": {"is_main": bbox == main_bbox},
            }
            for bbox in bboxes
        ],
    }
