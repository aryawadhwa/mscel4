from __future__ import annotations

import numpy as np
import pandas as pd

from src.core.schema_catalog import DEFAULT_SENSITIVE_COLUMNS
from src.api.schemas import SchemaColumn

def _column_map(schema: list[SchemaColumn]) -> dict[str, SchemaColumn]:
    return {column.name: column for column in schema}

def numerical_bounds(column: SchemaColumn, series: pd.Series) -> tuple[float, float]:
    # Ensure series is numeric and drop NaNs for bound detection
    numeric_series = pd.to_numeric(series, errors="coerce").dropna()
    
    if column.config.min is not None:
        lower = float(column.config.min)
    else:
        lower = float(numeric_series.min()) if not numeric_series.empty else 0.0
        
    if column.config.max is not None:
        upper = float(column.config.max)
    else:
        upper = float(numeric_series.max()) if not numeric_series.empty else 100.0
        
    if np.isnan(lower): lower = 0.0
    if np.isnan(upper): upper = 100.0
    
    if lower >= upper:
        upper = lower + 1.0
        
    return lower, upper

def compute_approval_score(df: pd.DataFrame, schema: list[SchemaColumn]) -> pd.Series:
    columns = _column_map(schema)
    signal_specs: list[tuple[str, float, callable]] = []

    if "credit_score" in df.columns and "credit_score" in columns:
        signal_specs.append(("credit_score", 0.45, lambda series: (series - 300) / 550))
    if "debt_to_income" in df.columns and "debt_to_income" in columns:
        signal_specs.append(("debt_to_income", 0.30, lambda series: 1 - series.astype(float)))
    if "prior_defaults" in df.columns and "prior_defaults" in columns:
        signal_specs.append(("prior_defaults", 0.15, lambda series: 1 - series.astype(float).clip(upper=5) / 5))
    if "annual_income" in df.columns and "annual_income" in columns:
        lower, upper = numerical_bounds(columns["annual_income"], df["annual_income"])
        signal_specs.append(("annual_income", 0.10, lambda series: (series.astype(float) - lower) / (upper - lower)))
    if "savings_balance" in df.columns and "savings_balance" in columns:
        lower, upper = numerical_bounds(columns["savings_balance"], df["savings_balance"])
        signal_specs.append(("savings_balance", 0.08, lambda series: (series.astype(float) - lower) / (upper - lower)))
    if "assets_value" in df.columns and "assets_value" in columns:
        lower, upper = numerical_bounds(columns["assets_value"], df["assets_value"])
        signal_specs.append(("assets_value", 0.08, lambda series: (series.astype(float) - lower) / (upper - lower)))
    if "existing_loans" in df.columns and "existing_loans" in columns:
        signal_specs.append(("existing_loans", 0.06, lambda series: 1 - series.astype(float).clip(upper=8) / 8))

    if not signal_specs:
        return pd.Series(np.repeat(0.5, len(df)), index=df.index)

    total_weight = sum(weight for _, weight, _ in signal_specs)
    score = pd.Series(np.zeros(len(df)), index=df.index, dtype=float)
    for name, weight, transform in signal_specs:
        score = score.add(transform(df[name]).fillna(0).clip(0, 1) * (weight / total_weight), fill_value=0)
    return score.clip(0, 1)

def calculate_systemic_penalties(df: pd.DataFrame, schema: list[SchemaColumn]) -> pd.Series:
    penalty = pd.Series(np.zeros(len(df)), index=df.index, dtype=float)
    fairness_columns = {column.name for column in schema if column.fairness_sensitive or column.name in DEFAULT_SENSITIVE_COLUMNS}

    if "race" in fairness_columns and "race" in df.columns:
        penalty += df["race"].map({"Black": 0.12, "Hispanic": 0.09, "White": 0.0, "Asian": 0.02, "Other": 0.05}).fillna(0)
    if "gender" in fairness_columns and "gender" in df.columns:
        penalty += df["gender"].map({"Female": 0.07, "Non-binary": 0.04, "Male": 0.0}).fillna(0)
    if "zip_code_tier" in fairness_columns and "zip_code_tier" in df.columns:
        penalty += df["zip_code_tier"].map({"Rural": 0.08, "Urban": 0.0, "Suburban": 0.0}).fillna(0)
    if "age" in fairness_columns and "age" in df.columns:
        penalty += np.where(df["age"].astype(float) > 55, 0.05, 0.0)

    return penalty
