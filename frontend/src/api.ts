const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8080";

export type HomeOwnership = "RENT" | "OWN" | "MORTGAGE" | "OTHER";
export type LoanIntent =
  | "PERSONAL"
  | "EDUCATION"
  | "MEDICAL"
  | "VENTURE"
  | "HOMEIMPROVEMENT"
  | "DEBTCONSOLIDATION";
export type LoanGrade = "A" | "B" | "C" | "D" | "E" | "F" | "G";
export type DefaultOnFile = "Y" | "N";
export type Recommendation = "APPROVED" | "CONDITIONAL" | "REVIEW_NEEDED" | "REJECTED";

export interface PredictRequest {
  person_age: number;
  person_income: number;
  person_home_ownership: HomeOwnership;
  person_emp_length: number;
  loan_intent: LoanIntent;
  loan_grade: LoanGrade;
  loan_amnt: number;
  loan_int_rate: number;
  loan_percent_income: number;
  cb_person_default_on_file: DefaultOnFile;
  cb_person_cred_hist_length: number;
}

export interface PredictResponse {
  default_probability: number;
  default_pct: string;
  recommendation: Recommendation;
  top_risk_factors: string[];
}

export interface EmailRequest {
  recommendation: Recommendation;
  applicant_name: string;
  loan_amnt: number;
  loan_intent: LoanIntent;
  top_risk_factors: string[];
}

export interface EmailResponse {
  subject: string;
  body: string;
}

async function apiFetch<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

export const predictLoan = (data: PredictRequest): Promise<PredictResponse> =>
  apiFetch<PredictResponse>("/predict", data);

export const generateEmail = (data: EmailRequest): Promise<EmailResponse> =>
  apiFetch<EmailResponse>("/email", data);
