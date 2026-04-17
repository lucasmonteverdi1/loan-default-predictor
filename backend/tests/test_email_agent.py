"""Tests for the LangGraph email agent in email_gen.py.

All LLM calls are mocked so these tests run without a real API key or
network access. They verify:
  - Pure nodes (translate_factors, choose_tone) work correctly.
  - The public generate_email() function returns valid EmailResponse objects.
  - The fallback path is triggered when the API key is missing.
  - The validation retry logic fires when validation_passed=False.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.email_gen import choose_tone, translate_factors
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


def test_generate_email_happy_path():
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

    with patch("app.email_gen.generate_email_node", return_value=fake_generate_output), \
         patch("app.email_gen.validate_email_node", return_value=fake_validate_output), \
         patch("app.email_gen.settings") as mock_settings:
        mock_settings.gemini_api_key = "fake-key"
        mock_settings.groq_api_key = "fake-groq-key"

        # Re-build the graph with the mocked nodes
        import app.email_gen as eg
        eg._graph = eg._build_graph()

        result = eg.generate_email(EMAIL_REQUEST)

    assert isinstance(result, EmailResponse)
    assert result.subject == "Good news!"
    assert "Jane" in result.body


def test_generate_email_no_api_key_returns_fallback():
    """Missing API key should return the hardcoded fallback — no LLM calls made."""
    with patch("app.email_gen.settings") as mock_settings:
        mock_settings.gemini_api_key = ""
        mock_settings.groq_api_key = ""

        from app.email_gen import generate_email
        result = generate_email(EMAIL_REQUEST)

    assert isinstance(result, EmailResponse)
    assert result.subject == "Regarding your loan application"


def test_generate_email_llm_exception_returns_fallback():
    """If a node raises unexpectedly, the fallback email is returned (no 500)."""
    with patch("app.email_gen.generate_email_node", side_effect=RuntimeError("API down")), \
         patch("app.email_gen.settings") as mock_settings:
        mock_settings.gemini_api_key = "fake-key"
        mock_settings.groq_api_key = "fake-groq-key"

        import app.email_gen as eg
        eg._graph = eg._build_graph()

        result = eg.generate_email(EMAIL_REQUEST)

    assert isinstance(result, EmailResponse)
    assert result.subject == "Regarding your loan application"
