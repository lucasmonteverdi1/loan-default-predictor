/**
 * Human-readable labels for the 24 engineered model features.
 *
 * Mirrors backend/app/feature_labels.py — both files must be kept in sync.
 * If the feature set changes, update both.
 */
export const FEATURE_LABELS: Record<string, string> = {
  // Raw numeric
  person_age: "Age",
  person_emp_length: "Employment length (years)",
  loan_amnt: "Loan amount",
  loan_int_rate: "Interest rate",
  cb_person_cred_hist_length: "Credit history length (years)",
  // Derived numeric
  person_income_log: "Income level",
  debt_to_income: "Debt-to-income ratio",
  annual_interest_burden: "Yearly interest cost",
  income_per_emp_year: "Income per year of employment",
  loan_to_cred_hist: "Loan size vs credit history length",
  age_at_credit_start: "Age when credit history began",
  emp_to_age_ratio: "Employment length relative to age",
  // Flags
  high_interest_flag: "High interest rate flag",
  high_debt_burden_flag: "High debt burden flag",
  // Encoded categorical
  loan_grade_encoded: "Loan grade",
  // One-hot: home ownership
  person_home_ownership_RENT: "Home ownership (renting)",
  person_home_ownership_OWN: "Home ownership (owner)",
  person_home_ownership_OTHER: "Home ownership (other)",
  // One-hot: loan intent
  loan_intent_EDUCATION: "Loan purpose: education",
  loan_intent_HOMEIMPROVEMENT: "Loan purpose: home improvement",
  loan_intent_MEDICAL: "Loan purpose: medical",
  loan_intent_PERSONAL: "Loan purpose: personal",
  loan_intent_VENTURE: "Loan purpose: business venture",
  // One-hot: prior default
  cb_person_default_on_file_Y: "Previous default on record",
};

export function toReadable(feature: string): string {
  return FEATURE_LABELS[feature] ?? feature;
}
