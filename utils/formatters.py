"""
utils/formatters.py

Small, pure helper functions for input validation and number/date
formatting. Kept dependency-free (besides the standard library) so they're
trivial to unit test.
"""

from datetime import datetime
from typing import Optional, Tuple


class ValidationError(ValueError):
    """Raised for any user-facing input problem (bad amount, empty field…)."""


def validate_amount(raw: str) -> float:
    """
    Validate a raw amount string typed by the user.

    Raises ValidationError with a friendly message on any problem;
    otherwise returns the parsed positive float.
    """
    if raw is None or raw.strip() == "":
        raise ValidationError("Please enter an amount to convert.")

    text = raw.strip().replace(",", "")

    try:
        value = float(text)
    except ValueError:
        raise ValidationError("That doesn't look like a valid number.")

    if value != value:  # NaN check
        raise ValidationError("That doesn't look like a valid number.")

    if value <= 0:
        raise ValidationError("Amount must be greater than zero.")

    if value > 1_000_000_000_000:
        raise ValidationError("That amount is too large to convert.")

    return value


def format_amount(value: float, precision: int = 2) -> str:
    """Format a number with thousands separators, e.g. 8583.4231 -> 8,583.42"""
    precision = max(0, min(precision, 8))
    return f"{value:,.{precision}f}"


def format_rate(value: float, precision: int = 6) -> str:
    precision = max(2, min(precision, 8))
    return f"{value:.{precision}f}".rstrip("0").rstrip(".") if "." in f"{value:.{precision}f}" else f"{value:.{precision}f}"


def format_timestamp(dt: Optional[datetime] = None) -> Tuple[str, str]:
    """Return (date_str, time_str) for the given/now datetime."""
    dt = dt or datetime.now()
    return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M:%S")


def parse_iso(date_str: str) -> datetime:
    return datetime.strptime(date_str, "%Y-%m-%d")
