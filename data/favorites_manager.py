"""
data/favorites_manager.py

Tiny JSON-backed store for favorite currency pairs (bonus "Favorites
System" feature), e.g. ⭐ USD → INR.
"""

from __future__ import annotations

import json
import os
from typing import List, Tuple

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
FAVORITES_FILE = os.path.join(DATA_DIR, "favorites.json")


class FavoritesManager:
    def __init__(self, path: str = FAVORITES_FILE):
        self.path = path
        self._ensure_file()

    def list_pairs(self) -> List[Tuple[str, str]]:
        data = self._load()
        return [tuple(pair) for pair in data]

    def add_pair(self, from_code: str, to_code: str) -> None:
        data = self._load()
        pair = [from_code, to_code]
        if pair not in data:
            data.append(pair)
            self._save(data)

    def remove_pair(self, from_code: str, to_code: str) -> None:
        data = self._load()
        pair = [from_code, to_code]
        if pair in data:
            data.remove(pair)
            self._save(data)

    def is_favorite(self, from_code: str, to_code: str) -> bool:
        return [from_code, to_code] in self._load()

    def toggle(self, from_code: str, to_code: str) -> bool:
        """Returns True if the pair is now a favorite, False if removed."""
        if self.is_favorite(from_code, to_code):
            self.remove_pair(from_code, to_code)
            return False
        self.add_pair(from_code, to_code)
        return True

    def _ensure_file(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        if not os.path.exists(self.path):
            self._save([["USD", "INR"], ["EUR", "INR"]])

    def _load(self) -> List[list]:
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, json.JSONDecodeError):
            return []

    def _save(self, data: List[list]) -> None:
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
