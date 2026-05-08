"""In-memory ring buffer of recent predictions for the monitoring dashboard.

This is a deliberately simple store: no database, no persistence. Predictions
are kept in a thread-safe deque of bounded size and exposed via a snapshot
method that aggregates the data for the /stats endpoint.

Trade-offs accepted for a portfolio demo:
- State is lost on process restart (Cloud Run cold starts reset the buffer).
- Each Cloud Run instance keeps its own counters — not globally consistent
  when the service scales beyond one instance.

Both are acceptable because the dashboard is a visualization of live traffic,
not a source of truth.
"""

from __future__ import annotations

from collections import Counter, deque
from datetime import datetime, timezone
from threading import Lock
from typing import TypedDict


class PredictionRecord(TypedDict):
    ts: str
    prob: float
    recommendation: str


class StatsSnapshot(TypedDict):
    total: int          # all-time prediction count (does not reset with the ring buffer)
    recent_count: int   # predictions currently in the ring buffer (≤ maxlen)
    recommendation_counts: dict[str, int]
    histogram: list[dict[str, float | int]]
    recent: list[PredictionRecord]


# Histogram bin edges: 10 bins of width 0.1 covering [0, 1].
_BIN_EDGES: list[float] = [i / 10 for i in range(11)]


def _bucket(prob: float) -> int:
    """Return the histogram bin index (0..9) for a probability in [0, 1]."""
    if prob >= 1.0:
        return 9
    return int(prob * 10)


class StatsStore:
    """Thread-safe ring buffer of recent predictions.

    _total_seen tracks the all-time count and never resets, while _buf caps at
    maxlen so memory stays bounded. The dashboard shows _total_seen as "Total
    predictions" — it's accurate even after the buffer rolls over.
    """

    def __init__(self, maxlen: int = 500):
        self._buf: deque[PredictionRecord] = deque(maxlen=maxlen)
        self._lock = Lock()
        self._total_seen: int = 0

    def record(self, prob: float, recommendation: str) -> None:
        record: PredictionRecord = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "prob": round(prob, 4),
            "recommendation": recommendation,
        }
        with self._lock:
            self._buf.append(record)
            self._total_seen += 1

    def snapshot(self) -> StatsSnapshot:
        with self._lock:
            items = list(self._buf)

        rec_counts: Counter[str] = Counter(r["recommendation"] for r in items)

        bin_counts = [0] * 10
        for r in items:
            bin_counts[_bucket(r["prob"])] += 1

        histogram = [
            {
                "bin_start": _BIN_EDGES[i],
                "bin_end": _BIN_EDGES[i + 1],
                "count": bin_counts[i],
            }
            for i in range(10)
        ]

        recent = items[-20:][::-1]  # newest first

        return {
            "total": self._total_seen,
            "recent_count": len(items),
            "recommendation_counts": dict(rec_counts),
            "histogram": histogram,
            "recent": recent,
        }

    def clear(self) -> None:
        """Reset the buffer and counter. Only used by tests."""
        with self._lock:
            self._buf.clear()
            self._total_seen = 0


# Module-level singleton used by predict.py and main.py.
stats_store = StatsStore()
