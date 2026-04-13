from __future__ import annotations
import logging
import json

from google import genai
from google.genai import types

from app.config import settings
from app.schema import EmailRequest, EmailResponse

logger = logging.getLogger(__name__)

_INTENT_LABELS = {
    "PERSONAL": "personal expenses",
    "EDUCATION": "education",
    "MEDICAL": "medical expenses",
    "VENTURE": "a business venture",
    "HOMEIMPROVEMENT": "home improvement",
    "DEBTCONSOLIDATION": "debt consolidation",
}

_RECOMMENDATION_CONTEXT = {
    "APPROVED": "has been approved",
    "CONDITIONAL": "has been conditionally approved, subject to additional review",
    "REVIEW_NEEDED": "requires further review before a decision can be made",
    "REJECTED": "cannot be approved at this time",
}

client = genai.Client(api_key=settings.gemini_api_key)

def generate_email(request: EmailRequest) -> EmailResponse:
    intent_label = _INTENT_LABELS.get(request.loan_intent, request.loan_intent.lower())
    decision_text = _RECOMMENDATION_CONTEXT[request.recommendation]
    factors_list = ", ".join(request.top_risk_factors)

    prompt = f"""You are a professional loan officer writing a formal but empathetic email to a loan applicant.

Applicant name: {request.applicant_name}
Loan amount requested: ${request.loan_amnt:,.0f}
Loan purpose: {intent_label}
Decision: {decision_text}
Key factors considered: {factors_list}

Write a professional email that:
1. Addresses the applicant by name
2. Clearly states the decision
3. Briefly mentions the key factors considered (use plain language, not technical feature names)
4. Provides a next step appropriate to the decision
5. Is warm but professional in tone

Return your response as JSON with exactly two fields:
- "subject": the email subject line
- "body": the full email body (use \\n for line breaks)

Return only the JSON object, no additional text."""

    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.7,
        )
    )

    try:
        data = json.loads(response.text)

        logger.info("email_generated", extra={"recommendation": request.recommendation})

        return EmailResponse(
            subject=data.get("subject", "Actualización de solicitud"),
            body=data.get("body", "")
        )
    except Exception as e:
        logger.error(f"Error procesando Gemini: {str(e)}")
        raise e
