import json
from pathlib import Path
from typing import Any


class JsonRepository:
    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir

    def load(self, filename: str) -> Any:
        file_path = self._data_dir / filename
        with file_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
