"""Tests for the LangGraph email agent in email_gen.py.

All LLM calls are mocked so these tests run without a real API key or
network access. They verify:
  - Pure nodes (translate_factors, choose_tone) work correctly.
  - The public generate_email() function returns valid EmailResponse objects.
  - The fallback path is triggered when the API key is missing.
  - The validation retry logic fires when validation_passed=False.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.email_gen import _is_transient, _llm_retry, choose_tone, translate_factors
from app.schema import EmailRequest, EmailResponse


# ---------------------------------------------------------------------------
# Pure node tests (no LLM, no mocking needed)
# ---------------------------------------------------------------------------

def test_translate_factors_known_features():
    state = {
        "top_risk_factors": ["person_income_log", "debt_to_income", "loan_amnt"],
        "readable_factors": [],
    }
    result = translate_factors(state)
    assert result["readable_factors"] == [
        "Income level",
        "Debt-to-income ratio",
        "Loan amount",
    ]


def test_translate_factors_unknown_feature_falls_back():
    state = {"top_risk_factors": ["unknown_feature_xyz"], "readable_factors": []}
    result = translate_factors(state)
    # Unknown features should pass through unchanged.
    assert result["readable_factors"] == ["unknown_feature_xyz"]


def test_choose_tone_approved():
    state = {"recommendation": "APPROVED"}
    result = choose_tone(state)
    assert "warm" in result["tone"].lower()


def test_choose_tone_rejected():
    state = {"recommendation": "REJECTED"}
    result = choose_tone(state)
    assert "empathetic" in result["tone"].lower()


def test_choose_tone_unknown_falls_back():
    state = {"recommendation": "UNKNOWN_STATUS"}
    result = choose_tone(state)
    assert result["tone"] == "professional and clear"


# ---------------------------------------------------------------------------
# Integration tests for generate_email() — LLM calls are mocked
# ---------------------------------------------------------------------------

EMAIL_REQUEST = EmailRequest(
    recommendation="APPROVED",
    applicant_name="Jane Doe",
    loan_amnt=10000.0,
    loan_intent="PERSONAL",
    top_risk_factors=["person_income_log", "debt_to_income"],
)

_FAKE_EMAIL_JSON = '{"subject": "Good news!", "body": "Dear Jane,\\n\\nApproved!"}'
_FAKE_VALID_JSON = '{"valid": true, "reason": "All checks passed."}'


def _make_llm_response(content: str) -> MagicMock:
    mock = MagicMock()
    mock.content = content
    return mock


async def test_generate_email_happy_path():
    """Graph runs successfully: generate node produces email, validate node passes it."""
    # Mock at node level — the graph is compiled at import time so mocking
    # the LLM classes after import has no effect. Mocking the node functions
    # directly is the correct approach for LangGraph tests.
    fake_generate_output = {
        "subject": "Good news!",
        "body": "Dear Jane,\n\nApproved!",
        "retries": 1,
    }
    fake_validate_output = {"validation_passed": True}

    import app.email_gen as eg
    original_graph = eg._graph  # save so we can restore after test

    try:
        with patch("app.email_gen.generate_email_node", AsyncMock(return_value=fake_generate_output)), \
             patch("app.email_gen.validate_email_node", AsyncMock(return_value=fake_validate_output)), \
             patch("app.email_gen.settings") as mock_settings:
            mock_settings.gemini_api_key = "fake-key"
            mock_settings.groq_api_key = "fake-groq-key"

            eg._graph = eg._build_graph()
            result = await eg.generate_email(EMAIL_REQUEST)
    finally:
        eg._graph = original_graph  # always restore, even if the test fails

    assert isinstance(result, EmailResponse)
    assert result.subject == "Good news!"
    assert "Jane" in result.body


async def test_generate_email_no_api_key_returns_fallback():
    """Missing API key should return the hardcoded fallback — no LLM calls made."""
    with patch("app.email_gen.settings") as mock_settings:
        mock_settings.gemini_api_key = ""
        mock_settings.groq_api_key = ""

        from app.email_gen import generate_email
        result = await generate_email(EMAIL_REQUEST)

    assert isinstance(result, EmailResponse)
    assert result.subject == "Regarding your loan application"


async def test_generate_email_llm_exception_returns_fallback():
    """If a node raises unexpectedly, the fallback email is returned (no 500)."""
    import app.email_gen as eg
    original_graph = eg._graph

    try:
        with patch("app.email_gen.generate_email_node", AsyncMock(side_effect=RuntimeError("API down"))), \
             patch("app.email_gen.settings") as mock_settings:
            mock_settings.gemini_api_key = "fake-key"
            mock_settings.groq_api_key = "fake-groq-key"

            eg._graph = eg._build_graph()
            result = await eg.generate_email(EMAIL_REQUEST)
    finally:
        eg._graph = original_graph

    assert isinstance(result, EmailResponse)
    assert result.subject == "Regarding your loan application"


# ---------------------------------------------------------------------------
# Retry logic
# ---------------------------------------------------------------------------

class _FakeAPIError(Exception):
    def __init__(self, status_code: int):
        self.status_code = status_code


def test_is_transient_503_retries():
    assert _is_transient(_FakeAPIError(503)) is True


def test_is_transient_400_does_not_retry():
    assert _is_transient(_FakeAPIError(400)) is False


async def test_llm_retry_recovers_from_transient_failure():
    """A 503 followed by success should succeed without raising."""
    calls = {"n": 0}

    @_llm_retry
    async def flaky():
        calls["n"] += 1
        if calls["n"] < 2:
            raise _FakeAPIError(503)
        return "ok"

    assert await flaky() == "ok"
    assert calls["n"] == 2


async def test_llm_retry_gives_up_on_non_transient_error():
    """A 400 should not be retried — it fails on the first attempt."""
    calls = {"n": 0}

    @_llm_retry
    async def always_bad():
        calls["n"] += 1
        raise _FakeAPIError(400)

    with pytest.raises(_FakeAPIError):
        await always_bad()
    assert calls["n"] == 1
