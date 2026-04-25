from __future__ import annotations

import numpy as np
import pandas as pd

from src.api.schemas import SchemaColumn
from src.domain.domain_profiles import categorical_options

def _perturb_numeric(series: pd.Series, column: SchemaColumn, rng: np.random.Generator) -> pd.Series:
    numeric_series = pd.to_numeric(series, errors="coerce").dropna()
    lower = float(column.config.min) if column.config.min is not None else (float(numeric_series.min()) if not numeric_series.empty else 0.0)
    upper = float(column.config.max) if column.config.max is not None else (float(numeric_series.max()) if not numeric_series.empty else 100.0)
    
    if np.isnan(lower): lower = 0.0
    if np.isnan(upper): upper = 100.0
    if lower >= upper: upper = lower + 1.0
    
    spread = max((upper - lower) * 0.05, 0.1)
    
    # Fill NaNs before perturbing to avoid errors
    filled_series = series.fillna((lower + upper) / 2).astype(float)
    
    perturbed = np.clip(filled_series + rng.normal(0, spread, len(series)), lower, upper)
    
    if pd.api.types.is_integer_dtype(series):
        return perturbed.round().astype(int)
    return perturbed.round(4)

def augment_dataset(seed_df: pd.DataFrame, schema: list[SchemaColumn], target_size: int) -> pd.DataFrame:
    """Generic statistical perturbation engine.
    
    Takes a base dataframe and artificially expands it to target_size by 
    adding localized Gaussian noise to numeric columns and swapping categorical
    labels according to configuration constraints.
    """
    rng = np.random.default_rng(7)
    sampled = seed_df.sample(n=target_size, replace=True, random_state=7).reset_index(drop=True).copy()

    for column in schema:
        if column.name == "loan_approved":
            continue
        if column.type == "numerical" and column.name in sampled:
            sampled[column.name] = _perturb_numeric(sampled[column.name], column, rng)
        elif column.type == "categorical" and column.name in sampled and rng.random() < 0.15:
            options, weights = categorical_options(column)
            replacement_mask = rng.random(len(sampled)) < 0.08
            sampled.loc[replacement_mask, column.name] = rng.choice(options, size=int(replacement_mask.sum()), p=weights)
        elif column.type == "boolean" and column.name in sampled and column.name != "loan_approved":
            base_rate = column.config.base_rate if column.config.base_rate is not None else float(sampled[column.name].mean())
            sampled[column.name] = rng.random(len(sampled)) < base_rate

    return sampled
