from __future__ import annotations

DEMOGRAPHIC_COLUMNS = {
    "age",
    "gender",
    "race",
    "zip_code_tier",
    "marital_status",
    "education_level",
    "dependents_count",
    "citizenship_status",
}

FINANCIAL_SIGNAL_COLUMNS = {
    "annual_income",
    "credit_score",
    "debt_to_income",
    "prior_defaults",
    "savings_balance",
    "assets_value",
    "existing_loans",
}

FINANCIAL_COLUMNS = FINANCIAL_SIGNAL_COLUMNS | {
    "employment_status",
    "monthly_expenses",
}

LOAN_COLUMNS = {
    "loan_amount",
    "loan_purpose",
    "loan_term_months",
    "interest_rate",
    "collateral_type",
    "co_applicant",
}

OUTCOME_COLUMNS = {"loan_approved"}

DEFAULT_SENSITIVE_COLUMNS = {"race", "gender", "age", "zip_code_tier"}

MINORITY_VALUES = {"Black", "Hispanic", "Asian", "Other"}
FEMALE_VALUES = {"Female", "Non-binary"}
RURAL_VALUES = {"Rural"}

AGE_BUCKETS = ["18-24", "25-34", "35-44", "45-54", "55+"]

CATEGORICAL_DEFAULTS = {
    "gender": ["Male", "Female", "Non-binary"],
    "race": ["White", "Black", "Hispanic", "Asian", "Other"],
    "zip_code_tier": ["Urban", "Suburban", "Rural"],
    "marital_status": ["Single", "Married", "Divorced", "Widowed"],
    "education_level": ["High school", "Associate", "Bachelor", "Master", "Doctorate"],
    "citizenship_status": ["Citizen", "Permanent Resident", "Visa Holder"],
    "employment_status": ["Employed", "Self-employed", "Unemployed", "Retired"],
    "loan_purpose": ["Home", "Auto", "Education", "Business", "Personal"],
    "collateral_type": ["None", "Vehicle", "Property", "Savings"],
}
