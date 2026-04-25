export const DEFAULT_CONFIG = {
  datasetSize: 500,
  representation: {
    femalePct: 40,
    minorityPct: 35,
    ruralPct: 20,
  },
  historicalCorrection: 80,
  labelCorrection: 70,
  measurementNoise: {
    enabled: true,
    creditScoreSigma: 15,
    incomeSigma: 2000,
  },
  customFilters: [],
};

export const FAIRNESS_BADGES = [
  "Structural Integrity",
  "Zero Entropy Calibration",
  "Open Source",
  "LLM Optimized",
];

export const TABS = [
  { id: "table", label: "Data Table" },
  { id: "charts", label: "Distribution Charts" },
  { id: "report", label: "Fairness Report" },
];

export const TOOLTIP_COPY = {
  historicalBias:
    "Historical bias happens when past lending decisions shaped by discrimination get baked into training data. This control reduces those inherited penalties.",
  representationBias:
    "Representation bias means some groups barely appear in the dataset, so models learn less about them. These controls enforce stronger minimum representation.",
  labelBias:
    "Label bias happens when similar applicants get different approval labels because of human bias. This control repairs unfair outcomes near the approval boundary.",
  measurementBias:
    "Measurement bias means some groups have noisier or less reliable financial data. de.bias applies the same noise pattern to everyone instead.",
  dpd:
    "Demographic Parity Difference shows the size of the approval-rate gap between monitored groups. Lower is better.",
  dir:
    "Disparate Impact Ratio compares the least-approved group to the most-approved group. Closer to 1 means fairer outcomes.",
  lcs:
    "Label Consistency Score checks whether borderline applicants are treated similarly across monitored groups. Higher is better.",
  rei:
    "Representation Equity Index measures how evenly monitored groups appear in the dataset. Higher means more balanced coverage.",
};

export const SCHEMA_CATEGORY_ORDER = [
  "Applicant Demographics",
  "Financial Profile",
  "Loan Details",
  "Outcome",
];

export const SCHEMA_PRESETS = {
  age: {
    label: "age",
    category: "Applicant Demographics",
    type: "numerical",
    config: { min: 18, max: 75, distribution: "normal", nullable: false },
    fairness_sensitive: true,
  },
  gender: {
    label: "gender",
    category: "Applicant Demographics",
    type: "categorical",
    config: { options: ["Male", "Female", "Non-binary"], weights: [0.47, 0.46, 0.07], nullable: false },
    fairness_sensitive: true,
  },
  race: {
    label: "race",
    category: "Applicant Demographics",
    type: "categorical",
    config: { options: ["White", "Black", "Hispanic", "Asian", "Other"], weights: [0.38, 0.2, 0.22, 0.12, 0.08], nullable: false },
    fairness_sensitive: true,
  },
  zip_code_tier: {
    label: "zip_code_tier",
    category: "Applicant Demographics",
    type: "categorical",
    config: { options: ["Urban", "Suburban", "Rural"], weights: [0.5, 0.32, 0.18], nullable: false },
    fairness_sensitive: true,
  },
  marital_status: {
    label: "marital_status",
    category: "Applicant Demographics",
    type: "categorical",
    config: { options: ["Single", "Married", "Divorced", "Widowed"], weights: [0.38, 0.44, 0.12, 0.06], nullable: false },
    fairness_sensitive: false,
  },
  education_level: {
    label: "education_level",
    category: "Applicant Demographics",
    type: "categorical",
    config: { options: ["High school", "Associate", "Bachelor", "Master", "Doctorate"], weights: [0.2, 0.16, 0.36, 0.2, 0.08], nullable: false },
    fairness_sensitive: false,
  },
  dependents_count: {
    label: "dependents_count",
    category: "Applicant Demographics",
    type: "numerical",
    config: { min: 0, max: 6, distribution: "uniform", nullable: false },
    fairness_sensitive: false,
  },
  citizenship_status: {
    label: "citizenship_status",
    category: "Applicant Demographics",
    type: "categorical",
    config: { options: ["Citizen", "Permanent Resident", "Visa Holder"], weights: [0.76, 0.17, 0.07], nullable: false },
    fairness_sensitive: false,
  },
  annual_income: {
    label: "annual_income",
    category: "Financial Profile",
    type: "numerical",
    config: { min: 15000, max: 250000, distribution: "log-normal", nullable: false },
    fairness_sensitive: false,
  },
  employment_status: {
    label: "employment_status",
    category: "Financial Profile",
    type: "categorical",
    config: { options: ["Employed", "Self-employed", "Unemployed", "Retired"], weights: [0.62, 0.18, 0.12, 0.08], nullable: false },
    fairness_sensitive: false,
  },
  credit_score: {
    label: "credit_score",
    category: "Financial Profile",
    type: "numerical",
    config: { min: 300, max: 850, distribution: "normal", nullable: false },
    fairness_sensitive: false,
  },
  debt_to_income: {
    label: "debt_to_income",
    category: "Financial Profile",
    type: "numerical",
    config: { min: 0.05, max: 0.95, distribution: "normal", nullable: false },
    fairness_sensitive: false,
  },
  prior_defaults: {
    label: "prior_defaults",
    category: "Financial Profile",
    type: "numerical",
    config: { min: 0, max: 5, distribution: "uniform", nullable: false },
    fairness_sensitive: false,
  },
  savings_balance: {
    label: "savings_balance",
    category: "Financial Profile",
    type: "numerical",
    config: { min: 0, max: 220000, distribution: "log-normal", nullable: false },
    fairness_sensitive: false,
  },
  monthly_expenses: {
    label: "monthly_expenses",
    category: "Financial Profile",
    type: "numerical",
    config: { min: 500, max: 14000, distribution: "normal", nullable: false },
    fairness_sensitive: false,
  },
  existing_loans: {
    label: "existing_loans",
    category: "Financial Profile",
    type: "numerical",
    config: { min: 0, max: 8, distribution: "uniform", nullable: false },
    fairness_sensitive: false,
  },
  assets_value: {
    label: "assets_value",
    category: "Financial Profile",
    type: "numerical",
    config: { min: 0, max: 650000, distribution: "log-normal", nullable: false },
    fairness_sensitive: false,
  },
  loan_amount: {
    label: "loan_amount",
    category: "Loan Details",
    type: "numerical",
    config: { min: 1000, max: 100000, distribution: "log-normal", nullable: false },
    fairness_sensitive: false,
  },
  loan_purpose: {
    label: "loan_purpose",
    category: "Loan Details",
    type: "categorical",
    config: { options: ["Home", "Auto", "Education", "Business", "Personal"], weights: [0.2, 0.26, 0.16, 0.1, 0.28], nullable: false },
    fairness_sensitive: false,
  },
  loan_term_months: {
    label: "loan_term_months",
    category: "Loan Details",
    type: "numerical",
    config: { min: 12, max: 72, distribution: "uniform", nullable: false },
    fairness_sensitive: false,
  },
  interest_rate: {
    label: "interest_rate",
    category: "Loan Details",
    type: "numerical",
    config: { min: 2.5, max: 28, distribution: "normal", nullable: false },
    fairness_sensitive: false,
  },
  collateral_type: {
    label: "collateral_type",
    category: "Loan Details",
    type: "categorical",
    config: { options: ["None", "Vehicle", "Property", "Savings"], weights: [0.45, 0.2, 0.2, 0.15], nullable: false },
    fairness_sensitive: false,
  },
  co_applicant: {
    label: "co_applicant",
    category: "Loan Details",
    type: "boolean",
    config: { base_rate: 0.22, nullable: false },
    fairness_sensitive: false,
  },
  loan_approved: {
    label: "loan_approved",
    category: "Outcome",
    type: "boolean",
    config: { base_rate: 0.52, nullable: false },
    fairness_sensitive: false,
    locked: true,
  },
};

export const DEFAULT_SCHEMA_ORDER = [
  "age",
  "gender",
  "race",
  "zip_code_tier",
  "annual_income",
  "employment_status",
  "credit_score",
  "loan_amount",
  "debt_to_income",
  "prior_defaults",
  "loan_approved",
];

export const DEMO_SCHEMA_ORDER = [
  "age",
  "gender",
  "race",
  "zip_code_tier",
  "annual_income",
  "credit_score",
  "debt_to_income",
  "prior_defaults",
  "loan_amount",
  "loan_purpose",
  "loan_approved",
];

export function buildSchemaColumn(name, overrides = {}) {
  const preset = SCHEMA_PRESETS[name];
  return {
    name,
    type: preset.type,
    config: { ...(preset.config || {}) },
    fairness_sensitive: Boolean(preset.fairness_sensitive),
    ...overrides,
    config: {
      ...(preset.config || {}),
      ...(overrides.config || {}),
    },
  };
}

export const DEFAULT_SCHEMA = DEFAULT_SCHEMA_ORDER.map((name) => buildSchemaColumn(name));
export const DEMO_SCHEMA = DEMO_SCHEMA_ORDER.map((name) => buildSchemaColumn(name));
