import { useEffect, useRef, useState } from "react";
import { predictLoan, type PredictResponse } from "../api";
import type { FormValues } from "./LoanForm";

type Recommendation = PredictResponse["recommendation"];

const BADGE_COLOR: Record<Recommendation, string> = {
  APPROVED: "bg-green-100 text-green-800",
  CONDITIONAL: "bg-yellow-100 text-yellow-800",
  REVIEW_NEEDED: "bg-orange-100 text-orange-800",
  REJECTED: "bg-red-100 text-red-800",
};

interface Props {
  baseValues: FormValues;
  baseResult: PredictResponse;
}

interface Sliders {
  loan_amnt: number;
  loan_int_rate: number;
  person_income: number;
}

export default function WhatIfPanel({ baseValues, baseResult }: Props) {
  const [sliders, setSliders] = useState<Sliders>({
    loan_amnt: baseValues.loan_amnt,
    loan_int_rate: baseValues.loan_int_rate,
    person_income: baseValues.person_income,
  });
  const [result, setResult] = useState<PredictResponse>(baseResult);
  const [loading, setLoading] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Reset sliders when a new base prediction comes in.
  // Also clears any pending debounce on unmount to avoid state updates on
  // an unmounted component when the user navigates away mid-slide.
  useEffect(() => {
    setSliders({
      loan_amnt: baseValues.loan_amnt,
      loan_int_rate: baseValues.loan_int_rate,
      person_income: baseValues.person_income,
    });
    setResult(baseResult);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [baseResult, baseValues]);

  function handleSliderChange(field: keyof Sliders, value: number) {
    const next = { ...sliders, [field]: value };
    setSliders(next);

      if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      setLoading(true);
      try {
        const { applicant_name, ...rest } = baseValues;
        void applicant_name; // not needed for /predict
        const updated = await predictLoan({
          ...rest,
          loan_amnt: next.loan_amnt,
          loan_int_rate: next.loan_int_rate,
          person_income: next.person_income,
        });
        setResult(updated);
      } catch {
        // silently ignore — keep showing last valid result
      } finally {
        setLoading(false);
      }
    }, 500);
  }

  function reset() {
    setSliders({
      loan_amnt: baseValues.loan_amnt,
      loan_int_rate: baseValues.loan_int_rate,
      person_income: baseValues.person_income,
    });
    setResult(baseResult);
  }

  const delta = (result.default_probability - baseResult.default_probability) * 100;
  const deltaStr = delta > 0 ? `+${delta.toFixed(1)}%` : `${delta.toFixed(1)}%`;
  const deltaColor = delta > 0 ? "text-red-600" : delta < 0 ? "text-green-600" : "text-gray-400";
  // Use a threshold to avoid showing "+0.0% vs original" from floating-point noise
  const showDelta = Math.abs(delta) > 0.05;

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <div>
          <p className="text-sm font-semibold text-gray-700">What-if Simulator</p>
          <p className="text-xs text-gray-400 mt-0.5">
            Adjust parameters to see how the risk score changes
          </p>
        </div>
        <button
          onClick={reset}
          className="text-xs text-indigo-600 hover:text-indigo-800 font-medium"
        >
          Reset to original
        </button>
      </div>

      {/* Sliders */}
      <div className="flex flex-col gap-5">
        <SliderField
          label="Loan amount"
          value={sliders.loan_amnt}
          min={500}
          max={50000}
          step={500}
          format={(v) => `$${v.toLocaleString()}`}
          base={baseValues.loan_amnt}
          onChange={(v) => handleSliderChange("loan_amnt", v)}
        />
        <SliderField
          label="Interest rate"
          value={sliders.loan_int_rate}
          min={5}
          max={25}
          step={0.5}
          format={(v) => `${v.toFixed(1)}%`}
          base={baseValues.loan_int_rate}
          onChange={(v) => handleSliderChange("loan_int_rate", v)}
        />
        <SliderField
          label="Annual income ($)"
          value={sliders.person_income}
          min={10000}
          max={200000}
          step={5000}
          format={(v) => `$${v.toLocaleString()}`}
          base={baseValues.person_income}
          onChange={(v) => handleSliderChange("person_income", v)}
        />
      </div>

      {/* Result */}
      <div className="mt-5 pt-4 border-t border-gray-100 flex items-center gap-4 flex-wrap">
        <span
          className={`rounded-full px-3 py-1 text-sm font-semibold ${BADGE_COLOR[result.recommendation]} ${loading ? "opacity-50" : ""}`}
        >
          {result.recommendation.replaceAll("_", " ")}
        </span>
        <span className={`text-xl font-bold text-gray-900 ${loading ? "opacity-50" : ""}`}>
          {result.default_pct}
        </span>
        {showDelta && (
          <span className={`text-sm font-medium ${deltaColor}`}>
            {deltaStr} vs original
          </span>
        )}
        {loading && (
          <span className="text-xs text-gray-400 animate-pulse">Recalculating…</span>
        )}
      </div>
    </div>
  );
}

interface SliderFieldProps {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  format: (v: number) => string;
  base: number;
  onChange: (v: number) => void;
}

function SliderField({ label, value, min, max, step, format, base, onChange }: SliderFieldProps) {
  const diff = value - base;
  const diffStr = diff > 0 ? `+${format(Math.abs(diff))}` : diff < 0 ? `-${format(Math.abs(diff))}` : null;
  const diffColor = diff !== 0 ? "text-gray-500" : "";

  return (
    <div>
      <div className="flex justify-between items-baseline mb-1">
        <label className="text-sm font-medium text-gray-700">{label}</label>
        <div className="flex items-baseline gap-2">
          <span className="text-sm font-semibold text-gray-900">{format(value)}</span>
          {diffStr && (
            <span className={`text-xs ${diffColor}`}>{diffStr} vs original</span>
          )}
        </div>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-indigo-600"
      />
      <div className="flex justify-between text-xs text-gray-400 mt-0.5">
        <span>{format(min)}</span>
        <span>{format(max)}</span>
      </div>
    </div>
  );
}
