import { useState } from "react";
import LoanForm, { type FormValues } from "../components/LoanForm";
import ResultCard from "../components/ResultCard";
import WhatIfPanel from "../components/WhatIfPanel";
import { predictLoan, generateEmail, type PredictResponse, type EmailResponse } from "../api";

export default function EvaluatePage() {
  const [predicting, setPredicting] = useState(false);
  const [emailLoading, setEmailLoading] = useState(false);
  const [prediction, setPrediction] = useState<PredictResponse | null>(null);
  const [email, setEmail] = useState<EmailResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [formValues, setFormValues] = useState<FormValues | null>(null);

  async function handleSubmit(values: FormValues) {
    setError(null);
    setPrediction(null);
    setEmail(null);
    setFormValues(values);
    setPredicting(true);

    try {
      const { applicant_name, ...predictFields } = values;
      const result = await predictLoan(predictFields);
      setPrediction(result);
      setPredicting(false);

      // Generate email non-blocking — does NOT re-fire on what-if changes
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
    <div className="flex flex-col gap-6 max-w-2xl mx-auto">
      {/* Form card */}
      <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
        <LoanForm onSubmit={handleSubmit} loading={predicting} />
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
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

      {/* What-if simulator — shown after first prediction, email not regenerated */}
      {prediction && formValues && (
        <WhatIfPanel
          baseValues={formValues}
          baseResult={prediction}
        />
      )}
    </div>
  );
}
