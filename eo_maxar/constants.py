from __future__ import annotations

from pathlib import Path

DEFAULT_DATA_DIR = Path("data")


class Paths:
    DEFAULT_DATA_DIR = DEFAULT_DATA_DIR
    RAW_DATA_DIR: Path = DEFAULT_DATA_DIR / "raw"


STAC_ENDPOINT = "http://localhost:8081"
RASTER_ENDPOINT = "http://localhost:8082"
TILEJSON_ENDPOINT = "WebMercatorQuad/tilejson.json"

MAP_LAYOUT = {"height": "700px"}
