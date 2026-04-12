import { useState } from "react";
import type { PredictResponse, EmailResponse } from "../api";

type Recommendation = PredictResponse["recommendation"];

const BADGE: Record<Recommendation, { bg: string; text: string; label: string }> = {
  APPROVED: {
    bg: "bg-green-100",
    text: "text-green-800",
    label: "✓ Approved",
  },
  CONDITIONAL: {
    bg: "bg-yellow-100",
    text: "text-yellow-800",
    label: "⚠ Conditional",
  },
  REVIEW_NEEDED: {
    bg: "bg-orange-100",
    text: "text-orange-800",
    label: "⟳ Review needed",
  },
  REJECTED: {
    bg: "bg-red-100",
    text: "text-red-800",
    label: "✕ Rejected",
  },
};

interface Props {
  prediction: PredictResponse;
  email: EmailResponse | null;
  emailLoading: boolean;
}

export default function ResultCard({ prediction, email, emailLoading }: Props) {
  const badge = BADGE[prediction.recommendation];
  const [copied, setCopied] = useState(false);

  function copyEmail() {
    if (!email) return;
    navigator.clipboard.writeText(`Subject: ${email.subject}\n\n${email.body}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="flex flex-col gap-5">
      {/* Decision */}
      <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <span
            className={`rounded-full px-3 py-1 text-sm font-semibold ${badge.bg} ${badge.text}`}
          >
            {badge.label}
          </span>
          <span className="text-2xl font-bold text-gray-900">
            {prediction.default_pct}
            <span className="ml-1 text-sm font-normal text-gray-500">
              default probability
            </span>
          </span>
        </div>

        <div className="mt-4">
          <p className="text-xs font-medium uppercase tracking-wide text-gray-500 mb-2">
            Top risk factors
          </p>
          <div className="flex flex-wrap gap-2">
            {prediction.top_risk_factors.map((f) => (
              <span
                key={f}
                className="rounded-md bg-gray-100 px-2 py-1 text-xs font-mono text-gray-700"
              >
                {f}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Email */}
      <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
        <div className="flex items-center justify-between mb-3">
          <p className="text-sm font-semibold text-gray-700">
            📧 Draft email for applicant
          </p>
          {email && (
            <button
              onClick={copyEmail}
              className="rounded-md bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-600 hover:bg-gray-200 transition-colors"
            >
              {copied ? "Copied!" : "Copy"}
            </button>
          )}
        </div>

        {emailLoading && (
          <p className="text-sm text-gray-400 animate-pulse">Generating email…</p>
        )}

        {email && !emailLoading && (
          <div className="text-sm text-gray-700 space-y-2">
            <p>
              <span className="font-medium text-gray-500">Subject: </span>
              {email.subject}
            </p>
            <hr className="border-gray-100" />
            <pre className="whitespace-pre-wrap font-sans leading-relaxed">
              {email.body}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
