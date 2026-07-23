"""Tests for the global daily cap on /email calls."""

from __future__ import annotations

from app.daily_limiter import DailyLimiter


def test_allows_up_to_limit():
    limiter = DailyLimiter(limit=3)
    assert limiter.try_consume() is True
    assert limiter.try_consume() is True
    assert limiter.try_consume() is True


def test_blocks_after_limit():
    limiter = DailyLimiter(limit=2)
    assert limiter.try_consume() is True
    assert limiter.try_consume() is True
    assert limiter.try_consume() is False


def test_resets_on_new_day():
    limiter = DailyLimiter(limit=1)
    assert limiter.try_consume() is True
    assert limiter.try_consume() is False

    # Simulate a day rollover.
    limiter._day = limiter._day.fromordinal(limiter._day.toordinal() - 1)
    assert limiter.try_consume() is True
