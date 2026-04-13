# loan-default-predictor

End-to-end credit risk scoring system. A trained XGBoost model evaluates loan applications and returns a default probability, a risk recommendation, the top contributing factors, and an AI-generated email draft for the applicant.

Link to Google Colab with dataset cleaning and model training: https://colab.research.google.com/drive/19mi4wfKCh3tbsXAAagRCqEjxuYy_NTNM?usp=sharing

## Architecture

```
Frontend (React + Vite)  →  Firebase Hosting
         ↓ HTTP
Backend (FastAPI)        →  Cloud Run
         ↓
XGBoost model (joblib)  +  Gemini API (email generation)
```

## Project structure

```
loan-default-predictor/
├── model/                        # Trained model artifacts (not committed)
│   ├── credit_model.joblib
│   └── features.joblib
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI app, routes
│   │   ├── predict.py            # Feature engineering + XGBoost + SHAP
│   │   ├── email_gen.py          # Gemini API integration
│   │   ├── schema.py             # Pydantic models
│   │   └── config.py             # Settings from env vars
│   ├── tests/
│   │   └── test_predict.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── App.tsx
    │   ├── api.ts
    │   └── components/
    │       ├── LoanForm.tsx
    │       └── ResultCard.tsx
    ├── firebase.json
    └── .env.example
```

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/predict` | Evaluate loan application |
| POST | `/email` | Generate applicant email via LLM |

### POST /predict — example

```bash
curl -X POST http://localhost:8080/predict \
  -H "Content-Type: application/json" \
  -d '{
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
  }'
```

Response:
```json
{
  "default_probability": 0.2341,
  "default_pct": "23.4%",
  "recommendation": "CONDITIONAL",
  "top_risk_factors": ["annual_interest_burden", "loan_grade_encoded", "debt_to_income"]
}
```

Recommendation thresholds: `< 0.20` → APPROVED · `0.20–0.44` → CONDITIONAL · `0.45–0.69` → REVIEW_NEEDED · `≥ 0.70` → REJECTED

## Local setup

### Requirements

- Python 3.11+
- Node.js 18+ and pnpm
- A Gemini API key

### Backend

```bash
# From repo root
cd backend
cp .env.example .env          # edit .env and add your GEMINI_API_KEY

python3 -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate

pip install -r requirements.txt

uvicorn app.main:app --reload --port 8080
```


### Run tests

```bash
cd backend
pytest tests/ -v
```

### Frontend

```bash
cd frontend
cp .env.example .env          # VITE_API_URL=http://localhost:8080

pnpm install
pnpm dev                      # opens http://localhost:5173
```

## Docker (backend)

The Dockerfile is built from the repo root so it can access `model/`:

```bash
docker build -f backend/Dockerfile -t loan-backend .
docker run -p 8080:8080 \
  -e GEMINI_API_KEY=... \
  loan-backend
```

## Deploy

### Backend → Cloud Run

```bash
gcloud run deploy loan-backend \
  --source . \
  --dockerfile backend/Dockerfile \
  --region us-central1 \
  --set-env-vars GEMINI_API_KEY=...
```

### Frontend → Firebase Hosting

```bash
cd frontend
pnpm build
firebase deploy --only hosting
```

## Tech stack

| Layer | Technology                            |
|-------|---------------------------------------|
| ML model | XGBoost, scikit-learn, SHAP           |
| Backend | FastAPI, uvicorn, pydantic            |
| LLM | Google Gemini (Flash)                 |
| Frontend | React, Vite, TypeScript, Tailwind CSS |
| Backend hosting | Google Cloud Run                      |
| Frontend hosting | Firebase Hosting                      |
