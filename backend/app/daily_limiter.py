"""Global daily cap shared across all clients, independent of per-IP rate limits.

Protects against LLM cost blowouts (a per-IP limit alone doesn't cap total
spend if traffic comes from many IPs). In-memory only — resets on process
restart, which is acceptable since Cloud Run cold starts are infrequent and
this is a soft cost guardrail, not a billing-accurate meter.
"""

from __future__ import annotations

from datetime import date
from threading import Lock


class DailyLimiter:
    def __init__(self, limit: int):
        self._limit = limit
        self._lock = Lock()
        self._day: date = date.today()
        self._count = 0

    def try_consume(self) -> bool:
        """Return True and increment if under the daily cap, False if exhausted."""
        with self._lock:
            today = date.today()
            if today != self._day:
                self._day = today
                self._count = 0
            if self._count >= self._limit:
                return False
            self._count += 1
            return True
