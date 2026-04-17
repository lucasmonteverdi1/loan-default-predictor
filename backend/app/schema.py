from typing import Literal
from pydantic import BaseModel, Field

HomeOwnership = Literal["RENT", "OWN", "MORTGAGE", "OTHER"]
LoanIntent = Literal[
    "PERSONAL", "EDUCATION", "MEDICAL", "VENTURE",
    "HOMEIMPROVEMENT", "DEBTCONSOLIDATION"
]
LoanGrade = Literal["A", "B", "C", "D", "E", "F", "G"]
DefaultOnFile = Literal["Y", "N"]
Recommendation = Literal["APPROVED", "CONDITIONAL", "REVIEW_NEEDED", "REJECTED"]


class PredictRequest(BaseModel):
    person_age: int = Field(..., ge=18, le=100)
    person_income: float = Field(..., gt=0)
    person_home_ownership: HomeOwnership
    person_emp_length: float = Field(..., ge=0)
    loan_intent: LoanIntent
    loan_grade: LoanGrade
    loan_amnt: float = Field(..., gt=0)
    loan_int_rate: float = Field(..., gt=0, le=100)
    cb_person_default_on_file: DefaultOnFile
    cb_person_cred_hist_length: int = Field(..., ge=0)


class PredictResponse(BaseModel):
    default_probability: float
    default_pct: str
    recommendation: Recommendation
    top_risk_factors: list[str]


class EmailRequest(BaseModel):
    recommendation: Recommendation
    applicant_name: str = Field(..., min_length=1)
    loan_amnt: float = Field(..., gt=0)
    loan_intent: LoanIntent
    top_risk_factors: list[str]


class EmailResponse(BaseModel):
    subject: str
    body: str


class HistogramBin(BaseModel):
    bin_start: float
    bin_end: float
    count: int


class PredictionRecord(BaseModel):
    ts: str
    prob: float
    recommendation: Recommendation


class StatsResponse(BaseModel):
    total: int
    recommendation_counts: dict[str, int]
    histogram: list[HistogramBin]
    recent: list[PredictionRecord]
