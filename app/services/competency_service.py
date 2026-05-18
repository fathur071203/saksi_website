from __future__ import annotations

from typing import Any


class CompetencyService:
    def __init__(self, repository) -> None:
        self._repository = repository

    def get_profile(self) -> dict[str, Any]:
        return self._repository.load("competency.json")
