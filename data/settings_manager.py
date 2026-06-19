"""
data/settings_manager.py

JSON-backed application settings: theme, default currency pair, decimal
precision, auto-refresh interval and language.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")

DEFAULTS: Dict[str, Any] = {
    "theme": "dark",                 # "dark" | "light"
    "default_from": "USD",
    "default_to": "INR",
    "decimal_precision": 2,
    "auto_refresh_seconds": 60,      # 0 disables auto-refresh
    "language": "English",
}


class SettingsManager:
    def __init__(self, path: str = SETTINGS_FILE):
        self.path = path
        self._settings = self._load()

    def get(self, key: str) -> Any:
        return self._settings.get(key, DEFAULTS.get(key))

    def get_all(self) -> Dict[str, Any]:
        return dict(self._settings)

    def set(self, key: str, value: Any) -> None:
        self._settings[key] = value
        self._save()

    def update(self, **kwargs) -> None:
        self._settings.update(kwargs)
        self._save()

    def _load(self) -> Dict[str, Any]:
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            merged = dict(DEFAULTS)
            merged.update(data)
            return merged
        except (OSError, json.JSONDecodeError):
            return dict(DEFAULTS)

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump(self._settings, fh, indent=2)
