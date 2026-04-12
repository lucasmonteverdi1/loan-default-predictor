from __future__ import annotations
import logging.config
from contextlib import asynccontextmanager
from typing import Any

import joblib
import shap
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.schema import PredictRequest, PredictResponse, EmailRequest, EmailResponse
from app.predict import predict as run_predict
from app.email_gen import generate_email

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
        }
    },
    "handlers": {
        "stdout": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "formatter": "json",
        }
    },
    "root": {"handlers": ["stdout"], "level": settings.log_level.upper()},
}
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/predict", response_model=PredictResponse)
def predict_endpoint(request: PredictRequest) -> PredictResponse:
    result = run_predict(
        request=request,
        model=model_state.model,
        explainer=model_state.explainer,
        feature_names=model_state.feature_names,
    )
    return PredictResponse(**result)


@app.post("/email", response_model=EmailResponse)
def email_endpoint(request: EmailRequest) -> EmailResponse:
    return generate_email(request)
