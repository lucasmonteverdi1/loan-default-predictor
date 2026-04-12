# AGENTS.md — Credit Risk Scoring API

This file is the source of truth for any AI agent (Claude Code or otherwise)
working on this codebase. Read it fully before making any changes.

---

## Project overview

End-to-end credit risk scoring system. Given a loan applicant's financial
profile, the API returns a default probability, a risk recommendation, and
the top features driving the prediction.

Built as a portfolio project — public repo, intended to demonstrate ML
engineering skills in a CV context.

**Stack:** Python · XGBoost · FastAPI · Docker · Google Cloud Run (target)

---

## Repository structure

```
loan-default-predictor/
├── AGENTS.md                  ← you are here
├── README.md
├── .gitignore                 ← must include .env, *.joblib (see note below)
├── .env.example               ← template for environment variables, no real values
│
├── model/
│   ├── credit_model.joblib    ← trained XGBoost model (631 KB)
│   └── features.joblib        ← ordered list of feature names the model expects
│
├── app/
│   ├── main.py                ← FastAPI app, lifespan, routers
│   ├── predict.py             ← prediction logic and SHAP explanations
│   ├── schema.py              ← Pydantic input/output models
│   └── config.py              ← settings loaded from environment variables
│
├── notebooks/
│   └── Dataset_cleaning.ipynb ← full ML pipeline (EDA → training → export)
│
├── Dockerfile
├── requirements.txt
└── tests/
    └── test_predict.py
```

---

## Model details

| Property | Value |
|---|---|
| Algorithm | XGBoost (XGBClassifier) |
| Training data | Credit Risk Dataset — Kaggle (laotse/credit-risk-dataset) |
| Features | 24 engineered features (see list below) |
| Decision threshold | **0.35** |
| ROC-AUC (test) | 0.9501 |
| PR-AUC (test) | 0.9072 |
| F1-Score @ 0.35 | 0.7837 |
| Recall on defaults | 0.85 |

### Why threshold = 0.35

This is a deliberate business decision, not a default. In credit risk,
a false negative (approving a borrower who defaults) carries higher cost
than a false positive (rejecting a good borrower). Threshold 0.35 maximises
recall at an acceptable precision level. Do not change this threshold without
explicit business justification.

The mathematical optimum by F1 is 0.636 — this was evaluated and rejected
in favour of higher recall.

### Feature list (order matters)

The model expects exactly these 24 features in this order:

```
person_age, person_emp_length, loan_amnt, loan_int_rate,
cb_person_cred_hist_length, person_income_log, debt_to_income,
annual_interest_burden, income_per_emp_year, loan_to_cred_hist,
age_at_credit_start, emp_to_age_ratio, high_interest_flag,
high_debt_burden_flag, loan_grade_encoded,
person_home_ownership_OTHER, person_home_ownership_OWN,
person_home_ownership_RENT, loan_intent_EDUCATION,
loan_intent_HOMEIMPROVEMENT, loan_intent_MEDICAL,
loan_intent_PERSONAL, loan_intent_VENTURE,
cb_person_default_on_file_Y
```

The canonical source for this list is `model/features.joblib`.
Always load from that file — never hardcode the list in application code.

---

## API design

### Endpoints

```
GET  /health          → liveness check, returns {"status": "ok"}
POST /predict         → single applicant prediction
```

### POST /predict — request body

Accepts the raw applicant fields (pre-feature-engineering). Feature
engineering runs inside the API, not on the client side.

```json
{
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
  "cb_person_cred_hist_length": 4
}
```

### POST /predict — response

```json
{
  "default_probability": 0.2341,
  "default_pct": "23.4%",
  "recommendation": "CONDITIONAL",
  "top_risk_factors": ["annual_interest_burden", "loan_grade_encoded", "debt_to_income"]
}
```

### Recommendation thresholds

| Probability | Label |
|---|---|
| < 0.20 | APPROVED |
| 0.20 – 0.44 | CONDITIONAL |
| 0.45 – 0.69 | REVIEW_NEEDED |
| ≥ 0.70 | REJECTED |

These thresholds are business-driven. Treat them as configuration, not constants.

---

## Serverless cloud architecture

**Target platform:** Google Cloud Run (preferred) or AWS Lambda container.
All design decisions must account for this constraint.

### Key implications

**Stateless:** The API must not rely on in-process state that persists between
requests. Each container instance is ephemeral. No local file writes, no
in-memory caches that need to survive restarts.

**Cold start:** Model loading happens at container startup inside the
FastAPI lifespan context manager, not at import time and not per-request.
The model (631 KB) is bundled in the Docker image — do not load it from
external storage unless the model grows beyond ~50 MB.

**No filesystem writes at runtime:** Do not write logs, temp files, or any
output to disk. Use structured stdout logging (JSON format) so the cloud
logging service can parse it.

**Environment variables only:** All configuration (port, log level, CORS
origins, any future API keys) must be read from environment variables via
`app/config.py`. Never hardcode values. See `.env.example` for the full list.

**Container image size:** Keep the Docker image lean. Use a slim Python base
image. Avoid installing unnecessary packages. Faster image pull = faster
cold start.

**Health check:** Cloud Run requires a `/health` endpoint that returns 200.
This is already in the spec above — do not remove it.

---

## Docker

The model file is bundled in the image. Build target is linux/amd64 (Cloud Run).

```dockerfile
# key requirements:
# - python:3.11-slim base
# - copy model/ directory into image
# - expose port 8080 (Cloud Run default)
# - run with uvicorn, single worker (Cloud Run scales via instances, not workers)
```

Typical run command for local testing:

```bash
docker build -t loan-default-predictor .
docker run -p 8080:8080 --env-file .env loan-default-predictor
```

---

## Environment variables

Defined in `app/config.py` using Pydantic Settings.
Real values go in `.env` (gitignored). Template in `.env.example`.

| Variable | Description | Default |
|---|---|---|
| `PORT` | Port the server listens on | `8080` |
| `LOG_LEVEL` | Uvicorn log level | `info` |
| `CORS_ORIGINS` | Comma-separated allowed origins | `*` |
| `MODEL_PATH` | Path to credit_model.joblib | `model/credit_model.joblib` |
| `FEATURES_PATH` | Path to features.joblib | `model/features.joblib` |

---

## Security and privacy

- This API serves predictions on a **public dataset model**. No PII is stored or logged.
- Do not log request bodies in production (they contain financial data).
- The Kaggle credentials used during training are never part of this repo.
  They were used interactively in Google Colab and never written to disk.
- `.gitignore` must always include: `.env`, `*.joblib`, `kaggle.json`, `__pycache__`

---

## Testing

Minimum required tests before any deployment:

1. `/health` returns 200
2. Valid input returns expected response shape
3. Missing fields return 422 (Pydantic validation)
4. Feature engineering produces the correct 24 columns in the correct order
5. Prediction output is in [0, 1]

Run with: `pytest tests/`

---

## What not to change without discussion

- **Threshold (0.35):** has business justification documented above
- **Feature list order:** must match training exactly, sourced from `features.joblib`
- **Recommendation labels:** APPROVED / CONDITIONAL / REVIEW_NEEDED / REJECTED
- **Model file:** do not retrain without updating this document with new metrics
