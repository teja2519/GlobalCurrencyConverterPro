"""
utils/currencies.py

Static metadata about supported currencies: ISO code, display name, symbol
and country flag emoji. This is reference/display metadata only — it is NOT
used as exchange-rate data (rates always come live from the API layer).

Adding a new currency only requires one new entry in CURRENCIES, as long as
the code is supported by the Frankfurter API (see api/currency_api.py for
the small list of pegged exceptions).
"""

from typing import Dict, List, TypedDict


class CurrencyInfo(TypedDict):
    name: str
    symbol: str
    flag: str


CURRENCIES: Dict[str, CurrencyInfo] = {
    "USD": {"name": "US Dollar",        "symbol": "$",   "flag": "\U0001F1FA\U0001F1F8"},
    "INR": {"name": "Indian Rupee",     "symbol": "\u20B9", "flag": "\U0001F1EE\U0001F1F3"},
    "EUR": {"name": "Euro",             "symbol": "\u20AC", "flag": "\U0001F1EA\U0001F1FA"},
    "GBP": {"name": "British Pound",    "symbol": "\u00A3", "flag": "\U0001F1EC\U0001F1E7"},
    "JPY": {"name": "Japanese Yen",     "symbol": "\u00A5", "flag": "\U0001F1EF\U0001F1F5"},
    "AUD": {"name": "Australian Dollar","symbol": "$",   "flag": "\U0001F1E6\U0001F1FA"},
    "CAD": {"name": "Canadian Dollar",  "symbol": "$",   "flag": "\U0001F1E8\U0001F1E6"},
    "CHF": {"name": "Swiss Franc",      "symbol": "CHF", "flag": "\U0001F1E8\U0001F1ED"},
    "CNY": {"name": "Chinese Yuan",     "symbol": "\u00A5", "flag": "\U0001F1E8\U0001F1F3"},
    "SGD": {"name": "Singapore Dollar", "symbol": "$",   "flag": "\U0001F1F8\U0001F1EC"},
    "HKD": {"name": "Hong Kong Dollar", "symbol": "$",   "flag": "\U0001F1ED\U0001F1F0"},
    "NZD": {"name": "New Zealand Dollar","symbol": "$",  "flag": "\U0001F1F3\U0001F1FF"},
    "SEK": {"name": "Swedish Krona",    "symbol": "kr",  "flag": "\U0001F1F8\U0001F1EA"},
    "NOK": {"name": "Norwegian Krone",  "symbol": "kr",  "flag": "\U0001F1F3\U0001F1F4"},
    "DKK": {"name": "Danish Krone",     "symbol": "kr",  "flag": "\U0001F1E9\U0001F1F0"},
    "ZAR": {"name": "South African Rand","symbol": "R",  "flag": "\U0001F1FF\U0001F1E6"},
    "AED": {"name": "UAE Dirham",       "symbol": "\u062F.\u0625", "flag": "\U0001F1E6\U0001F1EA"},
    "SAR": {"name": "Saudi Riyal",      "symbol": "\uFDFC", "flag": "\U0001F1F8\U0001F1E6"},
    "THB": {"name": "Thai Baht",        "symbol": "\u0E3F", "flag": "\U0001F1F9\U0001F1ED"},
    "KRW": {"name": "South Korean Won", "symbol": "\u20A9", "flag": "\U0001F1F0\U0001F1F7"},
}

# Currencies whose live market rate is not published by the underlying
# Frankfurter/ECB feed because their central banks maintain a fixed,
# publicly-announced peg against the US Dollar. Rather than hardcoding a
# fabricated "market" rate, the API layer derives these from the live
# USD rate using the official peg constant, and flags the result with a
# distinct "Pegged" status so the user always knows where a number came from.
PEGGED_TO_USD = {
    "AED": 3.6725,
    "SAR": 3.7500,
}

DEFAULT_FROM = "USD"
DEFAULT_TO = "INR"


def currency_label(code: str) -> str:
    """Return the full dropdown label, e.g. '🇺🇸 USD - US Dollar ($)'."""
    info = CURRENCIES[code]
    return f"{info['flag']} {code} - {info['name']} ({info['symbol']})"


def short_label(code: str) -> str:
    """Return a compact label, e.g. '🇺🇸 USD'."""
    info = CURRENCIES[code]
    return f"{info['flag']} {code}"


def code_from_label(label: str) -> str:
    """Recover the 3-letter code from any label produced above."""
    for code in CURRENCIES:
        if label.strip().startswith(code) or code in label:
            return code
    return label.strip()[:3].upper()


def all_labels() -> List[str]:
    return [currency_label(code) for code in CURRENCIES]


def symbol_of(code: str) -> str:
    return CURRENCIES.get(code, {}).get("symbol", "")


def flag_of(code: str) -> str:
    return CURRENCIES.get(code, {}).get("flag", "")


def name_of(code: str) -> str:
    return CURRENCIES.get(code, {}).get("name", code)
