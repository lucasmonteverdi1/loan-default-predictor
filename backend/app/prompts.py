"""Prompt templates for the LangGraph email agent.

Keeping prompts in a dedicated module separates concerns:
- email_gen.py owns the graph structure (nodes, edges, routing logic)
- prompts.py owns the text sent to the LLMs

This makes prompts easy to iterate on without touching orchestration code,
and easy to test in isolation.
"""

from __future__ import annotations


def _sanitize_text(value: str, max_len: int = 100) -> str:
    """Strip newlines and truncate to prevent prompt injection via user inputs."""
    return value.replace("\n", " ").replace("\r", " ").strip()[:max_len]


def build_generation_prompt(
    applicant_name: str,
    loan_amnt: float,
    intent_label: str,
    recommendation: str,
    tone: str,
    factors_text: str,
) -> str:
    """Prompt for the generation node (Gemini).

    Produces a JSON object with `subject` and `body` keys.
    """
    # Sanitize user-supplied inputs before embedding in the prompt.
    safe_name = _sanitize_text(applicant_name)
    safe_factors = _sanitize_text(factors_text, max_len=300)

    return f"""You are a professional loan officer writing a formal but empathetic email to a loan applicant.

Applicant name: {safe_name}
Loan amount requested: ${loan_amnt:,.0f}
Loan purpose: {intent_label}
Decision: {recommendation}
Tone: {tone}
Key factors considered (plain language): {safe_factors}

Write a professional email that:
1. Addresses the applicant by name
2. Clearly states the decision using plain language (NOT the raw label like "APPROVED")
3. Briefly mentions the key factors using the plain-language descriptions provided
4. Provides a next step appropriate to the decision
5. Uses the specified tone throughout

Return ONLY a JSON object with exactly two string fields:
- "subject": the email subject line
- "body": the full email body (use \\n for line breaks)"""


def build_validation_prompt(
    recommendation: str,
    tone: str,
    top_risk_factors: list[str],
    subject: str,
    body: str,
) -> str:
    """Prompt for the validation node (Groq llama-3.1-8b-instant).

    Returns a JSON object with `valid` (bool) and `reason` (str) keys.
    Optimized for fast classification — no creativity needed.
    """
    return f"""You are a quality reviewer for loan decision emails. Evaluate the email below.

Decision that should be communicated: {recommendation}
Expected tone: {tone}
Technical feature names that must NOT appear verbatim: {top_risk_factors}

Email subject: {subject}
Email body:
{body}

Answer ONLY with a JSON object:
{{"valid": true or false, "reason": "one sentence explaining your decision"}}

Mark as valid=true if ALL of the following are true:
- The decision is clearly stated in plain language
- The tone roughly matches the expectation
- None of the raw technical feature names appear in the body

Mark as valid=false otherwise."""
