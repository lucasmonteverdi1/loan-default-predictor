from contextlib import asynccontextmanager
from typing import Annotated, Any
import logging

import joblib
import shap
from fastapi import Body, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import settings
from app.logging_config import configure_logging
from app.schema import (
    EmailRequest, EmailResponse,
    PredictRequest, PredictResponse,
    StatsResponse,
)
from app.predict import predict as run_predict
from app.email_gen import generate_email
from app.stats_store import stats_store

configure_logging(settings.log_level)
logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)


class ModelState:
    model: Any = None
    explainer: shap.TreeExplainer = None
    feature_names: list[str] = None


model_state = ModelState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Loading model artifacts")
    model_state.model = joblib.load(settings.model_path)
    model_state.feature_names = joblib.load(settings.features_path)
    model_state.explainer = shap.TreeExplainer(model_state.model)
    logger.info(f"Model loaded — {len(model_state.feature_names)} features")
    yield
    logger.info("Shutting down")


app = FastAPI(
    title="Credit Risk Scoring API",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/stats", response_model=StatsResponse)
def stats_endpoint():
    return stats_store.snapshot()


@app.post("/predict", response_model=PredictResponse)
@limiter.limit("30/minute")
def predict_endpoint(request: Request, body: PredictRequest = Body(...)) -> PredictResponse:
    result = run_predict(
        request=body,
        model=model_state.model,
        explainer=model_state.explainer,
        feature_names=model_state.feature_names,
    )
    stats_store.record(result["default_probability"], result["recommendation"])
    return PredictResponse(**result)


@app.post("/email", response_model=EmailResponse)
@limiter.limit("10/minute")
def email_endpoint(request: Request, body: EmailRequest = Body(...)) -> EmailResponse:
    return generate_email(body)
