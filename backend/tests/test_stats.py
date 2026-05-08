"""Tests for the in-memory stats store and the /stats endpoint."""

from __future__ import annotations

import numpy as np
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.stats_store import StatsStore

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

        from app.main import app, stats_store
        stats_store.clear()  # start fresh for each test

        with TestClient(app) as c:
            yield c, stats_store


# 1. Fresh store returns zero total
def test_stats_empty(client):
    c, _ = client
    resp = c.get("/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["recommendation_counts"] == {}
    assert len(data["histogram"]) == 10
    assert len(data["recent"]) == 0


# 2. Stats update after a /predict call
def test_stats_after_predict(client):
    c, _ = client
    payload = {
        "person_age": 28, "person_income": 55000,
        "person_home_ownership": "RENT", "person_emp_length": 3.0,
        "loan_intent": "PERSONAL", "loan_grade": "C",
        "loan_amnt": 10000, "loan_int_rate": 13.5,
        "cb_person_default_on_file": "N",
        "cb_person_cred_hist_length": 4,
    }
    c.post("/predict", json=payload)
    resp = c.get("/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["recent"]) == 1


# 3. StatsStore ring buffer caps at maxlen, but total is all-time
def test_ring_buffer_maxlen():
    store = StatsStore(maxlen=3)
    for i in range(5):
        store.record(0.1 * i, "APPROVED")
    snap = store.snapshot()
    assert snap["total"] == 5         # all-time count never decays
    assert snap["recent_count"] == 3  # ring buffer capped at maxlen


# 4. Histogram bins sum to total
def test_histogram_bins_sum_to_total():
    store = StatsStore()
    for prob in [0.05, 0.15, 0.55, 0.95]:
        store.record(prob, "APPROVED")
    snap = store.snapshot()
    assert sum(b["count"] for b in snap["histogram"]) == snap["total"]


# 5. Recommendation counts are correct
def test_recommendation_counts():
    store = StatsStore()
    store.record(0.1, "APPROVED")
    store.record(0.3, "CONDITIONAL")
    store.record(0.3, "CONDITIONAL")
    snap = store.snapshot()
    assert snap["recommendation_counts"]["APPROVED"] == 1
    assert snap["recommendation_counts"]["CONDITIONAL"] == 2


# 6. Recent list is newest-first and capped at 20
def test_recent_is_newest_first_and_capped():
    store = StatsStore()
    for i in range(25):
        store.record(round(i * 0.01, 2), "APPROVED")
    snap = store.snapshot()
    assert len(snap["recent"]) == 20
    # newest first: last recorded probability should appear first
    assert snap["recent"][0]["prob"] == round(24 * 0.01, 2)
