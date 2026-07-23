import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import type { HomeOwnership, LoanIntent, LoanGrade, DefaultOnFile } from "../api";

const schema = z.object({
  applicant_name: z.string().min(1, "Required"),
  person_age: z.coerce.number().int().min(18).max(100),
  person_income: z.coerce.number().positive(),
  person_home_ownership: z.enum(["RENT", "OWN", "MORTGAGE", "OTHER"]),
  person_emp_length: z.coerce.number().min(0),
  loan_intent: z.enum([
    "PERSONAL",
    "EDUCATION",
    "MEDICAL",
    "VENTURE",
    "HOMEIMPROVEMENT",
    "DEBTCONSOLIDATION",
  ]),
  loan_grade: z.enum(["A", "B", "C", "D", "E", "F", "G"]),
  loan_amnt: z.coerce.number().positive(),
  loan_int_rate: z.coerce.number().positive().max(100),
  cb_person_default_on_file: z.enum(["Y", "N"]),
  cb_person_cred_hist_length: z.coerce.number().int().min(0),
});

export type FormValues = z.infer<typeof schema>;

interface Props {
  onSubmit: (data: FormValues) => void;
  loading: boolean;
  helpOpen: boolean;
  onToggleHelp: () => void;
}

function Field({
  label,
  error,
  children,
}: {
  label: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-sm font-medium text-gray-700">{label}</label>
      {children}
      {error && <p className="text-xs text-red-500">{error}</p>}
    </div>
  );
}

const inputCls =
  "rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500";
const selectCls = inputCls;

export default function LoanForm({ onSubmit, loading, helpOpen, onToggleHelp }: Props) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  return (
    <form
      onSubmit={handleSubmit(onSubmit)}
      className="grid grid-cols-1 gap-4 sm:grid-cols-2"
    >
      <div className="sm:col-span-2 flex items-center justify-between">
        <h2 className="text-xl font-bold text-gray-900">Loan application</h2>
        <button
          type="button"
          onClick={onToggleHelp}
          aria-label="Toggle field descriptions"
          aria-pressed={helpOpen}
          className={[
            "flex h-9 w-9 items-center justify-center rounded-full border text-base font-semibold transition-colors",
            helpOpen
              ? "border-indigo-600 bg-indigo-600 text-white"
              : "border-gray-300 text-gray-500 hover:bg-gray-100 hover:text-gray-700",
          ].join(" ")}
        >
          i
        </button>
      </div>

      {/* Applicant name — used for email generation only */}
      <div className="sm:col-span-2">
        <Field label="Applicant name" error={errors.applicant_name?.message}>
          <input
            {...register("applicant_name")}
            placeholder="John Smith"
            className={inputCls}
          />
        </Field>
      </div>

      <Field label="Age" error={errors.person_age?.message}>
        <input
          {...register("person_age")}
          type="number"
          placeholder="28"
          className={inputCls}
        />
      </Field>

      <Field label="Annual income ($)" error={errors.person_income?.message}>
        <input
          {...register("person_income")}
          type="number"
          placeholder="55000"
          className={inputCls}
        />
      </Field>

      <Field label="Home ownership" error={errors.person_home_ownership?.message}>
        <select {...register("person_home_ownership")} className={selectCls}>
          <option value="">Select...</option>
          {(["RENT", "OWN", "MORTGAGE", "OTHER"] as HomeOwnership[]).map((v) => (
            <option key={v} value={v}>
              {v}
            </option>
          ))}
        </select>
      </Field>

      <Field label="Employment length (years)" error={errors.person_emp_length?.message}>
        <input
          {...register("person_emp_length")}
          type="number"
          step="0.5"
          placeholder="3"
          className={inputCls}
        />
      </Field>

      <Field label="Loan intent" error={errors.loan_intent?.message}>
        <select {...register("loan_intent")} className={selectCls}>
          <option value="">Select...</option>
          {(
            [
              "PERSONAL",
              "EDUCATION",
              "MEDICAL",
              "VENTURE",
              "HOMEIMPROVEMENT",
              "DEBTCONSOLIDATION",
            ] as LoanIntent[]
          ).map((v) => (
            <option key={v} value={v}>
              {v}
            </option>
          ))}
        </select>
      </Field>

      <Field label="Loan grade" error={errors.loan_grade?.message}>
        <select {...register("loan_grade")} className={selectCls}>
          <option value="">Select...</option>
          {(["A", "B", "C", "D", "E", "F", "G"] as LoanGrade[]).map((v) => (
            <option key={v} value={v}>
              {v}
            </option>
          ))}
        </select>
      </Field>

      <Field label="Loan amount ($)" error={errors.loan_amnt?.message}>
        <input
          {...register("loan_amnt")}
          type="number"
          placeholder="10000"
          className={inputCls}
        />
      </Field>

      <Field label="Interest rate (%)" error={errors.loan_int_rate?.message}>
        <input
          {...register("loan_int_rate")}
          type="number"
          step="0.1"
          placeholder="13.5"
          className={inputCls}
        />
      </Field>

      <Field
        label="Previous default on file"
        error={errors.cb_person_default_on_file?.message}
      >
        <select {...register("cb_person_default_on_file")} className={selectCls}>
          <option value="">Select...</option>
          {(["N", "Y"] as DefaultOnFile[]).map((v) => (
            <option key={v} value={v}>
              {v === "N" ? "No" : "Yes"}
            </option>
          ))}
        </select>
      </Field>

      <Field
        label="Credit history length (years)"
        error={errors.cb_person_cred_hist_length?.message}
      >
        <input
          {...register("cb_person_cred_hist_length")}
          type="number"
          placeholder="4"
          className={inputCls}
        />
      </Field>

      <div className="sm:col-span-2 pt-2">
        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? "Evaluating…" : "Evaluate →"}
        </button>
      </div>
    </form>
  );
}
