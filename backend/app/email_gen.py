"""LangGraph-based email generation agent for loan decision notifications.

Architecture overview, graph topology, and multi-model strategy are documented
in EMAIL_AGENT.md in this directory.
"""

from __future__ import annotations

import json
import logging
from typing import TypedDict

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langgraph.graph import END, START, StateGraph

from app.config import settings
from app.feature_labels import to_readable
from app.prompts import build_generation_prompt, build_validation_prompt
from app.schema import EmailRequest, EmailResponse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tone mapping: one style guide per recommendation outcome.
# ---------------------------------------------------------------------------
_TONE_MAP: dict[str, str] = {
    "APPROVED": "warm and encouraging — celebrate the approval while keeping it professional",
    "CONDITIONAL": "professional and supportive — explain that more information is needed",
    "REVIEW_NEEDED": "neutral and informative — explain that the application is under review",
    "REJECTED": "empathetic and formal — decline respectfully and mention next steps",
}

_INTENT_LABELS: dict[str, str] = {
    "PERSONAL": "personal expenses",
    "EDUCATION": "education",
    "MEDICAL": "medical expenses",
    "VENTURE": "a business venture",
    "HOMEIMPROVEMENT": "home improvement",
    "DEBTCONSOLIDATION": "debt consolidation",
}


# ---------------------------------------------------------------------------
# State schema
# ---------------------------------------------------------------------------

class EmailState(TypedDict):
    # ---- Inputs (set once before the graph runs) ----
    recommendation: str          # APPROVED | CONDITIONAL | REVIEW_NEEDED | REJECTED
    applicant_name: str
    loan_amnt: float
    loan_intent: str
    top_risk_factors: list[str]  # technical feature names from SHAP

    # ---- Intermediate (filled by nodes) ----
    readable_factors: list[str]  # human-readable version of top_risk_factors
    tone: str                    # style guide for the LLM

    # ---- Loop control ----
    retries: int                 # how many times generate_email has been called

    # ---- Outputs ----
    subject: str
    body: str
    validation_passed: bool


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------

def translate_factors(state: EmailState) -> dict:
    """Translate technical SHAP feature names into human-readable labels.

    Returns: readable_factors — list of strings safe to include in an email.
    Position in graph: first node after START; no LLM call.
    """
    readable = [to_readable(f) for f in state["top_risk_factors"]]
    return {"readable_factors": readable}


def choose_tone(state: EmailState) -> dict:
    """Pick a tone style based on the recommendation outcome.

    Returns: tone — a style guide string injected into the generation prompt.
    Position in graph: after translate_factors; no LLM call.
    """
    tone = _TONE_MAP.get(state["recommendation"], "professional and clear")
    return {"tone": tone}


def _parse_json_response(raw: str) -> dict:
    """Strip markdown fences and parse JSON from an LLM response."""
    raw = raw.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1] if len(parts) > 1 else raw
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    return json.loads(raw)


def generate_email_node(state: EmailState) -> dict:
    """Call the LLM to draft the applicant email.

    Uses the readable factors and tone selected by upstream nodes so the
    prompt is focused. Returns subject + body as raw strings.
    Position in graph: after choose_tone; may be called again on retry.
    """
    llm = ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.gemini_api_key,
        temperature=0.7,
    )

    intent_label = _INTENT_LABELS.get(state["loan_intent"], state["loan_intent"].lower())
    factors_text = (
        ", ".join(state["readable_factors"])
        if state["readable_factors"]
        else "general risk assessment"
    )

    prompt = build_generation_prompt(
        applicant_name=state["applicant_name"],
        loan_amnt=state["loan_amnt"],
        intent_label=intent_label,
        recommendation=state["recommendation"],
        tone=state["tone"],
        factors_text=factors_text,
    )

    response = llm.invoke(prompt)
    data = _parse_json_response(response.content)

    return {
        "subject": data.get("subject", "Regarding your loan application"),
        "body": data.get("body", ""),
        "retries": state.get("retries", 0) + 1,
    }


def validate_email_node(state: EmailState) -> dict:
    """Ask Groq (llama-3.1-8b-instant) to self-check the generated email.

    Uses Groq instead of Gemini because validation is a classification task —
    fast and deterministic — where llama-3.1-8b-instant (~200ms) outperforms
    a heavier generative model without sacrificing accuracy.

    Checks three things:
      1. Is the decision clearly communicated in plain language?
      2. Does the tone match the requested style?
      3. Are there any raw technical feature names leaking into the body?

    Returns: validation_passed — True means the email is good to send.
    Position in graph: after generate_email; routes to END or back to generate.
    """
    llm = ChatGroq(
        model=settings.groq_model,
        api_key=settings.groq_api_key,
        temperature=0.0,  # deterministic for classification
    )

    prompt = build_validation_prompt(
        recommendation=state["recommendation"],
        tone=state["tone"],
        top_risk_factors=state["top_risk_factors"],
        subject=state["subject"],
        body=state["body"],
    )

    response = llm.invoke(prompt)
    try:
        result = _parse_json_response(response.content)
        passed = bool(result.get("valid", False))
        reason = result.get("reason", "")
    except (json.JSONDecodeError, ValueError, KeyError):
        # Treat parse failure as valid to avoid infinite retry loops
        passed = True
        reason = "parse error — skipping validation"

    logger.info("email_validation", extra={"valid": passed, "reason": reason})
    return {"validation_passed": passed}


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------

def _route_after_validation(state: EmailState) -> str:
    """Conditional edge: retry generation once if validation fails.

    We cap retries at 1 to guarantee the graph terminates even if the LLM
    keeps producing invalid output. On the second failure we accept the email
    as-is rather than blocking the user.
    """
    if not state["validation_passed"] and state.get("retries", 0) < 1:
        return "generate_email"
    return END


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def _build_graph():
    """Declare graph topology: nodes, fixed edges, and one conditional edge.

    The graph is compiled once at module load time and reused across requests.
    """
    # Ignores type because of PyCharm's type checker and LangGraph's generic TypedDict constraints
    builder = StateGraph(EmailState)  # type: ignore[arg-type]

    builder.add_node("translate_factors", translate_factors)  # type: ignore[arg-type]
    builder.add_node("choose_tone", choose_tone)  # type: ignore[arg-type]
    builder.add_node("generate_email", generate_email_node)  # type: ignore[arg-type]
    builder.add_node("validate_email", validate_email_node)  # type: ignore[arg-type]

    builder.add_edge(START, "translate_factors")
    builder.add_edge("translate_factors", "choose_tone")
    builder.add_edge("choose_tone", "generate_email")
    builder.add_edge("generate_email", "validate_email")

    # Conditional: go back to generate_email on first failure, else END.
    builder.add_conditional_edges(
        "validate_email",
        _route_after_validation,
        ["generate_email", END],
    )

    return builder.compile()


# Compile once at import time — reused for every /email request.
_graph = _build_graph()

# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

_FALLBACK_EMAIL = EmailResponse(
    subject="Regarding your loan application",
    body=(
        "Dear applicant,\n\n"
        "Thank you for your application. We will be in touch shortly "
        "with the outcome of our review.\n\n"
        "Best regards,\nCredit Risk Team"
    ),
)


def generate_email(request: EmailRequest) -> EmailResponse:
    """Run the LangGraph email agent and return a structured email.

    Falls back to a generic template if the API key is missing or the graph
    raises an unexpected exception — ensures the /email endpoint never 500s.
    """
    if not settings.gemini_api_key or not settings.groq_api_key:
        logger.warning("GEMINI_API_KEY or GROQ_API_KEY not set — returning fallback email")
        return _FALLBACK_EMAIL

    initial_state: EmailState = {
        "recommendation": request.recommendation,
        "applicant_name": request.applicant_name,
        "loan_amnt": request.loan_amnt,
        "loan_intent": request.loan_intent,
        "top_risk_factors": request.top_risk_factors,
        "readable_factors": [],
        "tone": "",
        "retries": 0,
        "subject": "",
        "body": "",
        "validation_passed": False,
    }

    try:
        final_state = _graph.invoke(initial_state)  # type: ignore[arg-type]
        logger.info("email_generated", extra={"recommendation": request.recommendation})
        return EmailResponse(
            subject=final_state["subject"],
            body=final_state["body"],
        )
    except Exception as exc:
        logger.error("email_agent_failed", extra={"error": str(exc)})
        return _FALLBACK_EMAIL
