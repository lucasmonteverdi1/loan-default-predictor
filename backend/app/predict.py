from __future__ import annotations
import math
import logging

import numpy as np
import pandas as pd
import shap

logger = logging.getLogger(__name__)

GRADE_ENCODING: dict[str, int] = {
    "A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5, "G": 6
}


def get_recommendation(prob: float) -> str:
    if prob < 0.20:
        return "APPROVED"
    elif prob < 0.45:
        return "CONDITIONAL"
    elif prob < 0.70:
        return "REVIEW_NEEDED"
    else:
        return "REJECTED"


def engineer_features(request, feature_names: list[str]) -> pd.DataFrame:
    p = request

    person_income_log = math.log(p.person_income)
    # debt_to_income is derived from the two inputs the user already provides —
    # no need to ask for loan_percent_income as a separate field.
    debt_to_income = p.loan_amnt / p.person_income
    annual_interest_burden = p.loan_amnt * p.loan_int_rate / 100.0
    income_per_emp_year = (
        p.person_income / p.person_emp_length
        if p.person_emp_length > 0
        else p.person_income / 0.5
    )
    loan_to_cred_hist = (
        p.loan_amnt / p.cb_person_cred_hist_length
        if p.cb_person_cred_hist_length > 0
        else p.loan_amnt
    )
    age_at_credit_start = p.person_age - p.cb_person_cred_hist_length
    emp_to_age_ratio = p.person_emp_length / p.person_age
    high_interest_flag = 1 if p.loan_int_rate > 15.0 else 0
    high_debt_burden_flag = 1 if debt_to_income > 0.3 else 0
    loan_grade_encoded = GRADE_ENCODING[p.loan_grade]

    row = {
        "person_age": p.person_age,
        "person_emp_length": p.person_emp_length,
        "loan_amnt": p.loan_amnt,
        "loan_int_rate": p.loan_int_rate,
        "cb_person_cred_hist_length": p.cb_person_cred_hist_length,
        "person_income_log": person_income_log,
        "debt_to_income": debt_to_income,
        "annual_interest_burden": annual_interest_burden,
        "income_per_emp_year": income_per_emp_year,
        "loan_to_cred_hist": loan_to_cred_hist,
        "age_at_credit_start": age_at_credit_start,
        "emp_to_age_ratio": emp_to_age_ratio,
        "high_interest_flag": high_interest_flag,
        "high_debt_burden_flag": high_debt_burden_flag,
        "loan_grade_encoded": loan_grade_encoded,
        "person_home_ownership_OTHER": 1 if p.person_home_ownership == "OTHER" else 0,
        "person_home_ownership_OWN": 1 if p.person_home_ownership == "OWN" else 0,
        "person_home_ownership_RENT": 1 if p.person_home_ownership == "RENT" else 0,
        "loan_intent_EDUCATION": 1 if p.loan_intent == "EDUCATION" else 0,
        "loan_intent_HOMEIMPROVEMENT": 1 if p.loan_intent == "HOMEIMPROVEMENT" else 0,
        "loan_intent_MEDICAL": 1 if p.loan_intent == "MEDICAL" else 0,
        "loan_intent_PERSONAL": 1 if p.loan_intent == "PERSONAL" else 0,
        "loan_intent_VENTURE": 1 if p.loan_intent == "VENTURE" else 0,
        "cb_person_default_on_file_Y": 1 if p.cb_person_default_on_file == "Y" else 0,
    }

    df = pd.DataFrame([row])
    df = df[feature_names]
    return df


def predict(request, model, explainer: shap.TreeExplainer, feature_names: list[str]) -> dict:
    df = engineer_features(request, feature_names)

    prob = float(model.predict_proba(df)[0][1])

    sv = explainer.shap_values(df)
    if isinstance(sv, list):
        row_shap = sv[1][0]
    else:
        row_shap = sv[0]
    top3_idx = np.argsort(np.abs(row_shap))[::-1][:3]
    top_risk_factors = [feature_names[i] for i in top3_idx]

    recommendation = get_recommendation(prob)

    logger.info(
        "prediction_complete",
        extra={"default_probability": round(prob, 4), "recommendation": recommendation},
    )

    return {
        "default_probability": round(prob, 4),
        "default_pct": f"{prob * 100:.1f}%",
        "recommendation": recommendation,
        "top_risk_factors": top_risk_factors,
    }
