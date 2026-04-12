from __future__ import annotations
import math
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.schema import PredictRequest
from app.predict import engineer_features, get_recommendation

VALID_PAYLOAD = {
    "person_age": 28,
    "person_income": 55000,
    "person_home_ownership": "RENT",
    "person_emp_length": 3.0,
    "loan_intent": "PERSONAL",
    "loan_grade": "C",
    "loan_amnt": 10000,
    "loan_int_rate": 13.5,
    "loan_percent_income": 0.18,
    "cb_person_default_on_file": "N",
    "cb_person_cred_hist_length": 4,
}

EXPECTED_FEATURES = [
    "person_age", "person_emp_length", "loan_amnt", "loan_int_rate",
    "cb_person_cred_hist_length", "person_income_log", "debt_to_income",
    "annual_interest_burden", "income_per_emp_year", "loan_to_cred_hist",
    "age_at_credit_start", "emp_to_age_ratio", "high_interest_flag",
    "high_debt_burden_flag", "loan_grade_encoded",
    "person_home_ownership_OTHER", "person_home_ownership_OWN",
    "person_home_ownership_RENT", "loan_intent_EDUCATION",
    "loan_intent_HOMEIMPROVEMENT", "loan_intent_MEDICAL",
    "loan_intent_PERSONAL", "loan_intent_VENTURE",
    "cb_person_default_on_file_Y",
]


@pytest.fixture
def client():
    mock_model = MagicMock()
    mock_model.predict_proba.return_value = np.array([[0.75, 0.25]])

    mock_explainer = MagicMock()
    mock_explainer.shap_values.return_value = np.zeros((1, 24))

    with patch("app.main.joblib.load") as mock_load, \
         patch("app.main.shap.TreeExplainer") as mock_explainer_cls:

        mock_load.side_effect = [mock_model, EXPECTED_FEATURES]
        mock_explainer_cls.return_value = mock_explainer

        from app.main import app
        with TestClient(app) as client:
            yield client


# 1. /health returns 200
def test_health_returns_200(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# 2. Valid input returns expected response shape
def test_valid_predict_response_shape(client):
    response = client.post("/predict", json=VALID_PAYLOAD)
    assert response.status_code == 200
    body = response.json()
    assert "default_probability" in body
    assert "default_pct" in body
    assert "recommendation" in body
    assert "top_risk_factors" in body
    assert isinstance(body["top_risk_factors"], list)
    assert len(body["top_risk_factors"]) == 3


# 3. Missing fields return 422
def test_missing_fields_return_422(client):
    payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "person_age"}
    response = client.post("/predict", json=payload)
    assert response.status_code == 422


# 4. Feature engineering produces 24 columns in correct order
def test_feature_engineering_columns_and_order():
    request = PredictRequest(**VALID_PAYLOAD)
    df = engineer_features(request, EXPECTED_FEATURES)

    assert list(df.columns) == EXPECTED_FEATURES
    assert len(df.columns) == 24

    row = df.iloc[0]
    assert row["person_income_log"] == pytest.approx(math.log(55000))
    assert row["debt_to_income"] == pytest.approx(0.18)
    assert row["annual_interest_burden"] == pytest.approx(10000 * 13.5 / 100)
    assert row["income_per_emp_year"] == pytest.approx(55000 / 3.0)
    assert row["loan_grade_encoded"] == 2  # C → 2
    assert row["person_home_ownership_RENT"] == 1
    assert row["person_home_ownership_OWN"] == 0
    assert row["loan_intent_PERSONAL"] == 1
    assert row["loan_intent_EDUCATION"] == 0
    assert row["cb_person_default_on_file_Y"] == 0
    assert row["high_interest_flag"] == 0    # 13.5 <= 15
    assert row["high_debt_burden_flag"] == 0  # 0.18 <= 0.3


# 5. Prediction probability is in [0, 1]
def test_prediction_probability_in_unit_interval(client):
    response = client.post("/predict", json=VALID_PAYLOAD)
    assert response.status_code == 200
    prob = response.json()["default_probability"]
    assert 0.0 <= prob <= 1.0


# Edge: zero emp_length no produce inf
def test_feature_engineering_zero_emp_length():
    payload = {**VALID_PAYLOAD, "person_emp_length": 0.0}
    request = PredictRequest(**payload)
    df = engineer_features(request, EXPECTED_FEATURES)
    assert not df["income_per_emp_year"].isnull().any()
    assert not (df["income_per_emp_year"] == float("inf")).any()


# Edge: zero cred hist no produce inf
def test_feature_engineering_zero_cred_hist():
    payload = {**VALID_PAYLOAD, "cb_person_cred_hist_length": 0}
    request = PredictRequest(**payload)
    df = engineer_features(request, EXPECTED_FEATURES)
    assert not df["loan_to_cred_hist"].isnull().any()
    assert not (df["loan_to_cred_hist"] == float("inf")).any()


# Recommendation thresholds
def test_recommendation_thresholds():
    assert get_recommendation(0.10) == "APPROVED"
    assert get_recommendation(0.19) == "APPROVED"
    assert get_recommendation(0.20) == "CONDITIONAL"
    assert get_recommendation(0.44) == "CONDITIONAL"
    assert get_recommendation(0.45) == "REVIEW_NEEDED"
    assert get_recommendation(0.69) == "REVIEW_NEEDED"
    assert get_recommendation(0.70) == "REJECTED"
    assert get_recommendation(0.99) == "REJECTED"
