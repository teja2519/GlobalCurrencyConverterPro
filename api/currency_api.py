"""
api/currency_api.py

CurrencyAPI talks to the Frankfurter exchange-rate API (https://api.frankfurter.app)
to fetch live and historical rates. It never hardcodes a market rate.

Resilience features:
  * Local JSON cache of the last successful fetch (data/cache/rates_cache.json)
    so the app stays usable during an outage.
  * Short, explicit network timeouts so the UI never hangs.
  * A clear `status` on every result: "online", "cached", "offline", or
    "pegged" (see note below).

A note on AED and SAR
----------------------
The Frankfurter feed mirrors the European Central Bank's reference rates,
which does not include the UAE Dirham or Saudi Riyal. Both currencies are
not freely floating: their central banks maintain a fixed, publicly
announced peg to the US Dollar (AED 3.6725, SAR 3.7500 per USD — values
set by the UAE Central Bank and SAMA respectively, not invented by this
app). For those two currencies only, the live USD rate from Frankfurter is
combined with that public peg constant to derive a rate, and the result is
labelled "Pegged Rate" everywhere in the UI so it is never confused with a
live market quote.
"""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

import requests

from utils.currencies import CURRENCIES, PEGGED_TO_USD

BASE_URL = "https://api.frankfurter.app"
REQUEST_TIMEOUT = 6  # seconds
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "cache")
CACHE_FILE = os.path.join(CACHE_DIR, "rates_cache.json")

FLOATING_CODES = sorted(set(CURRENCIES.keys()) - set(PEGGED_TO_USD.keys()))


@dataclass
class RateResult:
    base: str
    rates: Dict[str, float]          # 1 base == rates[code] of code
    timestamp: datetime
    status: str                       # online | cached | offline | pegged
    pegged_codes: List[str] = field(default_factory=list)

    def rate_for(self, code: str) -> Optional[float]:
        if code == self.base:
            return 1.0
        return self.rates.get(code)


class CurrencyAPI:
    """Fetches and caches exchange rate data. Thread-safe for simple use."""

    def __init__(self):
        os.makedirs(CACHE_DIR, exist_ok=True)
        self._lock = threading.Lock()
        self._last_result: Optional[RateResult] = None

    # ------------------------------------------------------------ public API
    def get_latest_rates(self, base: str = "USD") -> RateResult:
        """
        Fetch the latest rates for `base` against every supported currency.
        Falls back to the local cache, then raises only if there is truly
        no usable data at all.
        """
        floating_targets = [c for c in FLOATING_CODES if c != base]
        try:
            usd_anchor_rates = None
            if base in PEGGED_TO_USD:
                # Need USD rates first to derive this pegged base's own rates.
                payload = self._fetch_json(
                    f"{BASE_URL}/latest", params={"from": "USD", "to": ",".join(FLOATING_CODES)}
                )
                usd_anchor_rates = payload["rates"]
                usd_anchor_rates["USD"] = 1.0
                rates = self._derive_from_usd(base, usd_anchor_rates)
                pegged = [base] + [c for c in PEGGED_TO_USD if c != base]
                result = RateResult(base, rates, datetime.now(), "pegged", pegged)
            else:
                payload = self._fetch_json(
                    f"{BASE_URL}/latest", params={"from": base, "to": ",".join(floating_targets)}
                )
                rates = dict(payload.get("rates", {}))
                # Add pegged currencies derived from this base via USD.
                if base != "USD":
                    usd_payload = self._fetch_json(
                        f"{BASE_URL}/latest", params={"from": "USD", "to": base}
                    )
                    usd_to_base = usd_payload["rates"][base]
                else:
                    usd_to_base = 1.0
                for code, per_usd in PEGGED_TO_USD.items():
                    # 1 base = (per_usd / usd_to_base) of `code`
                    rates[code] = per_usd / usd_to_base
                pegged = list(PEGGED_TO_USD.keys())
                status = "pegged" if False else "online"
                result = RateResult(base, rates, self._parse_date(payload.get("date")), status, pegged)

            self._save_cache(result)
            with self._lock:
                self._last_result = result
            return result

        except (requests.RequestException, KeyError, ValueError, json.JSONDecodeError):
            return self._fallback(base)

    def get_historical_series(self, base: str, target: str, days: int) -> Dict[str, float]:
        """
        Return an ordered {date_str: rate} series for `target` against `base`
        over the last `days` days. Handles the AED/SAR peg by returning a
        flat line at the official peg-derived value when one side is pegged,
        since no historical *market* series exists for them.
        """
        if base in PEGGED_TO_USD or target in PEGGED_TO_USD:
            return self._synthetic_pegged_series(base, target, days)

        end = datetime.now().date()
        start = end.fromordinal(end.toordinal() - days)
        try:
            payload = self._fetch_json(
                f"{BASE_URL}/{start.isoformat()}..{end.isoformat()}",
                params={"from": base, "to": target},
            )
            series = {}
            for date_str, rates in payload.get("rates", {}).items():
                if target in rates:
                    series[date_str] = rates[target]
            return dict(sorted(series.items()))
        except (requests.RequestException, KeyError, ValueError, json.JSONDecodeError):
            return {}

    def last_known_status(self) -> str:
        with self._lock:
            return self._last_result.status if self._last_result else "offline"

    # ----------------------------------------------------------- internals
    def _fetch_json(self, url: str, params: dict) -> dict:
        response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.json()

    def _derive_from_usd(self, pegged_base: str, usd_rates: Dict[str, float]) -> Dict[str, float]:
        """Given 1 USD = usd_rates[code], compute 1 pegged_base = ? code."""
        usd_per_pegged = 1.0 / PEGGED_TO_USD[pegged_base]  # USD per 1 unit of pegged_base
        out = {}
        for code, usd_to_code in usd_rates.items():
            if code == pegged_base:
                continue
            out[code] = usd_to_code * usd_per_pegged
        for code, per_usd in PEGGED_TO_USD.items():
            if code == pegged_base:
                continue
            out[code] = per_usd * usd_per_pegged
        return out

    def _synthetic_pegged_series(self, base: str, target: str, days: int) -> Dict[str, float]:
        """Build a flat (or near-flat) series using today's derived rate,
        since AED/SAR don't float day-to-day against most currencies."""
        result = self.get_latest_rates(base)
        rate = result.rate_for(target)
        if rate is None:
            return {}
        end = datetime.now().date()
        series = {}
        for offset in range(days, -1, -1):
            d = end.fromordinal(end.toordinal() - offset)
            series[d.isoformat()] = rate
        return series

    def _parse_date(self, date_str: Optional[str]) -> datetime:
        if not date_str:
            return datetime.now()
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return datetime.now()

    def _save_cache(self, result: RateResult) -> None:
        try:
            payload = {
                "base": result.base,
                "rates": result.rates,
                "timestamp": result.timestamp.isoformat(),
                "pegged_codes": result.pegged_codes,
            }
            tmp = CACHE_FILE + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2)
            os.replace(tmp, CACHE_FILE)
        except OSError:
            pass  # caching is best-effort; never block on it

    def _fallback(self, base: str) -> RateResult:
        """Use the on-disk cache when the network/API is unavailable."""
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
            if payload.get("base") == base:
                rates = payload["rates"]
            else:
                # Re-derive the requested base from the cached rates via a
                # triangulation through whatever base was cached.
                cached_base = payload["base"]
                cached_rates = payload["rates"]
                cached_rates[cached_base] = 1.0
                if base not in cached_rates:
                    raise ValueError("base not in cache")
                base_to_cached = cached_rates[base]
                rates = {c: r / base_to_cached for c, r in cached_rates.items()}
                rates.pop(base, None)  # a currency's rate against itself is implicit

            # Note: cached_rates already includes correctly-derived AED/SAR
            # values from when it was saved (see get_latest_rates), so the
            # triangulation above naturally produces correct pegged rates
            # too — no extra re-derivation step needed here.

            ts = datetime.fromisoformat(payload["timestamp"])
            result = RateResult(base, rates, ts, "cached", list(PEGGED_TO_USD.keys()))
            with self._lock:
                self._last_result = result
            return result
        except (OSError, KeyError, ValueError, json.JSONDecodeError):
            result = RateResult(base, {}, datetime.now(), "offline", [])
            with self._lock:
                self._last_result = result
            return result
