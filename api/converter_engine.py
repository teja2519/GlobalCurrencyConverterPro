"""
api/converter_engine.py

ConverterEngine sits between the UI and CurrencyAPI: it validates input,
performs the actual multiplication, and packages everything the UI needs
to render a result (amount, rate, status, timestamp) in one object.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from api.currency_api import CurrencyAPI, RateResult
from utils.formatters import ValidationError, validate_amount


@dataclass
class ConversionResult:
    amount: float
    from_code: str
    to_code: str
    rate: float
    converted: float
    status: str               # online | cached | offline | pegged
    timestamp: datetime
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None


class ConverterEngine:
    """Performs validated currency conversions on top of CurrencyAPI."""

    def __init__(self, api: Optional[CurrencyAPI] = None):
        self.api = api or CurrencyAPI()

    def convert(self, raw_amount: str, from_code: str, to_code: str) -> ConversionResult:
        try:
            amount = validate_amount(raw_amount)
        except ValidationError as exc:
            return ConversionResult(
                amount=0.0, from_code=from_code, to_code=to_code, rate=0.0,
                converted=0.0, status="offline", timestamp=datetime.now(), error=str(exc),
            )

        if from_code == to_code:
            return ConversionResult(
                amount=amount, from_code=from_code, to_code=to_code, rate=1.0,
                converted=amount, status="online", timestamp=datetime.now(),
            )

        result: RateResult = self.api.get_latest_rates(from_code)
        rate = result.rate_for(to_code)

        if rate is None:
            return ConversionResult(
                amount=amount, from_code=from_code, to_code=to_code, rate=0.0,
                converted=0.0, status=result.status, timestamp=result.timestamp,
                error="Exchange rate unavailable right now. Check your connection and try again.",
            )

        return ConversionResult(
            amount=amount, from_code=from_code, to_code=to_code, rate=rate,
            converted=amount * rate, status=result.status, timestamp=result.timestamp,
        )

    def get_rate_only(self, from_code: str, to_code: str):
        """Convenience helper used by the favorites quick-access buttons."""
        result = self.api.get_latest_rates(from_code)
        return result.rate_for(to_code), result.status, result.timestamp
