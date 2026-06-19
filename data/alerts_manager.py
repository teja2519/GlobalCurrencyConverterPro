"""
data/alerts_manager.py

Exchange-rate alerts (bonus feature): the user picks a currency pair and a
threshold; the background refresh loop checks the live rate against it and
fires an in-app notification the first time it's crossed.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from typing import List

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
ALERTS_FILE = os.path.join(DATA_DIR, "alerts.json")


@dataclass
class Alert:
    from_code: str
    to_code: str
    direction: str    # "above" | "below"
    threshold: float
    triggered: bool = False

    def label(self) -> str:
        arrow = "\u2265" if self.direction == "above" else "\u2264"
        return f"{self.from_code} \u2192 {self.to_code} {arrow} {self.threshold}"


class AlertsManager:
    def __init__(self, path: str = ALERTS_FILE):
        self.path = path
        self.alerts: List[Alert] = self._load()

    def add(self, from_code: str, to_code: str, direction: str, threshold: float) -> None:
        self.alerts.append(Alert(from_code, to_code, direction, threshold))
        self._save()

    def remove(self, index: int) -> None:
        if 0 <= index < len(self.alerts):
            self.alerts.pop(index)
            self._save()

    def check(self, from_code: str, to_code: str, current_rate: float) -> List[Alert]:
        """Return newly-triggered alerts for this pair and mark them fired."""
        fired = []
        for alert in self.alerts:
            if alert.triggered or alert.from_code != from_code or alert.to_code != to_code:
                continue
            crossed = (alert.direction == "above" and current_rate >= alert.threshold) or \
                      (alert.direction == "below" and current_rate <= alert.threshold)
            if crossed:
                alert.triggered = True
                fired.append(alert)
        if fired:
            self._save()
        return fired

    def _load(self) -> List[Alert]:
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
            return [Alert(**item) for item in raw]
        except (OSError, json.JSONDecodeError, TypeError):
            return []

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump([asdict(a) for a in self.alerts], fh, indent=2)
