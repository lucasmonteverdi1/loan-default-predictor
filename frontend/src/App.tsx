import { useState } from "react";
import LoanForm, { type FormValues } from "./components/LoanForm";
import ResultCard from "./components/ResultCard";
import {
  predictLoan,
  generateEmail,
  type PredictResponse,
  type EmailResponse,
} from "./api";

export default function App() {
  const [predicting, setPredicting] = useState(false);
  const [emailLoading, setEmailLoading] = useState(false);
  const [prediction, setPrediction] = useState<PredictResponse | null>(null);
  const [email, setEmail] = useState<EmailResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(values: FormValues) {
    setError(null);
    setPrediction(null);
    setEmail(null);
    setPredicting(true);

    try {
      const { applicant_name, ...predictFields } = values;
      const result = await predictLoan(predictFields);
      setPrediction(result);
      setPredicting(false);

      // Generate email in parallel (non-blocking)
      setEmailLoading(true);
      generateEmail({
        recommendation: result.recommendation,
        applicant_name,
        loan_amnt: values.loan_amnt,
        loan_intent: values.loan_intent,
        top_risk_factors: result.top_risk_factors,
      })
        .then(setEmail)
        .catch(() => setEmail({ subject: "—", body: "Email generation failed." }))
        .finally(() => setEmailLoading(false));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error");
      setPredicting(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 py-10 px-4">
      <div className="mx-auto max-w-2xl">
        {/* Header */}
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-gray-900">Credit Risk Scorer</h1>
          <p className="mt-1 text-sm text-gray-500">
            XGBoost · SHAP · Gemini · FastAPI
          </p>
        </div>

        {/* Form card */}
        <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm mb-6">
          <LoanForm onSubmit={handleSubmit} loading={predicting} />
        </div>

        {/* Error */}
        {error && (
          <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700 mb-6">
            {error}
          </div>
        )}

        {/* Results */}
        {prediction && (
          <ResultCard
            prediction={prediction}
            email={email}
            emailLoading={emailLoading}
          />
        )}
      </div>
    </div>
  );
}
