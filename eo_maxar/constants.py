from __future__ import annotations

from pathlib import Path

TOP_FOLDER = Path(__file__).resolve().parent.parent


class Paths:
    TOP_FOLDER = TOP_FOLDER
    DATA_DIR: Path = TOP_FOLDER / "data"


MAP_LAYOUT = {"height": "700px"}
