from __future__ import annotations

import uuid
import numpy as np
import pandas as pd

from src.core.schema_catalog import FEMALE_VALUES, FINANCIAL_SIGNAL_COLUMNS, MINORITY_VALUES, RURAL_VALUES
from src.api.schemas import DeBiasConfig, SchemaColumn
from src.domain.scoring_engine import compute_approval_score, calculate_systemic_penalties, numerical_bounds

def apply_historical_bias(df: pd.DataFrame, correction: float, schema: list[SchemaColumn]) -> pd.DataFrame:
    adjusted = df.copy()
    correction_ratio = correction / 100
    base_score = compute_approval_score(adjusted, schema)
    total_penalty = calculate_systemic_penalties(adjusted, schema) * (1 - correction_ratio)
    adjusted["approval_score"] = base_score.sub(total_penalty).clip(0, 1).round(4)
    adjusted["loan_approved"] = adjusted["approval_score"] >= 0.52
    return adjusted

def _clone_and_perturb(df: pd.DataFrame, mask: pd.Series, schema: list[SchemaColumn], rng: np.random.Generator, needed: int) -> pd.DataFrame:
    source = df[mask].sample(n=needed, replace=True, random_state=13).copy()
    for column in schema:
        if column.name not in source.columns or column.name == "loan_approved":
            continue
        if column.type == "numerical":
            lower, upper = numerical_bounds(column, source[column].fillna(0))
            spread = max((upper - lower) * 0.03, 1)
            perturbed = np.clip(source[column].fillna((lower + upper) / 2) + rng.normal(0, spread, len(source)), lower, upper)
            if pd.api.types.is_integer_dtype(source[column]):
                source[column] = np.round(perturbed).astype(int)
            else:
                source[column] = np.round(perturbed, 4)
        elif column.type == "categorical" and column.config.options:
            replacement_mask = rng.random(len(source)) < 0.06
            if replacement_mask.any():
                weights = np.array(column.config.weights or [1] * len(column.config.options), dtype=float)
                weights = weights / weights.sum() if weights.sum() > 0 else np.repeat(1 / len(column.config.options), len(column.config.options))
                source.loc[replacement_mask, column.name] = rng.choice(column.config.options, size=int(replacement_mask.sum()), p=weights)
    source["_clone_id"] = [str(uuid.uuid4()) for _ in range(len(source))]
    return source.reset_index(drop=True)

def _rebalance_minimum(df: pd.DataFrame, mask: pd.Series, target_pct: float, schema: list[SchemaColumn], rng: np.random.Generator) -> pd.DataFrame:
    current_count = int(mask.sum())
    target_count = int(np.ceil(len(df) * target_pct / 100))
    if current_count >= target_count or current_count == 0:
        return df

    needed = target_count - current_count
    extra = _clone_and_perturb(df, mask, schema, rng, needed)
    combined = pd.concat([df, extra], ignore_index=True)
    return combined.sample(n=len(df), replace=False, random_state=17).reset_index(drop=True)

def apply_representation_bias(df: pd.DataFrame, config: DeBiasConfig, schema: list[SchemaColumn]) -> pd.DataFrame:
    adjusted = df.copy()
    rng = np.random.default_rng(21)
    available = {column.name for column in schema}

    if "gender" in available:
        adjusted = _rebalance_minimum(
            adjusted,
            adjusted["gender"].isin(FEMALE_VALUES),
            config.representation.femalePct,
            schema,
            rng,
        )
    if "race" in available:
        adjusted = _rebalance_minimum(
            adjusted,
            adjusted["race"].isin(MINORITY_VALUES),
            config.representation.minorityPct,
            schema,
            rng,
        )
    if "zip_code_tier" in available:
        adjusted = _rebalance_minimum(
            adjusted,
            adjusted["zip_code_tier"].isin(RURAL_VALUES),
            config.representation.ruralPct,
            schema,
            rng,
        )

    for custom_filter in config.customFilters:
        group_mask = pd.Series(np.zeros(len(adjusted), dtype=bool), index=adjusted.index)
        for column_name in ("gender", "race", "zip_code_tier"):
            if column_name in adjusted.columns:
                group_mask = group_mask | adjusted[column_name].eq(custom_filter.group)
        income_mask = adjusted["annual_income"] >= custom_filter.incomeMin if "annual_income" in adjusted.columns else pd.Series(True, index=adjusted.index)
        adjusted = _rebalance_minimum(adjusted, group_mask & income_mask, custom_filter.targetMinRepresentationPct, schema, rng)

    adjusted["approval_score"] = compute_approval_score(adjusted, schema).round(4)
    adjusted["loan_approved"] = adjusted["approval_score"] >= 0.52
    return adjusted

def apply_label_bias(df: pd.DataFrame, ratio: float, schema: list[SchemaColumn]) -> pd.DataFrame:
    adjusted = df.copy()
    ratio_fraction = ratio / 100
    borderline_mask = adjusted["approval_score"].between(0.47, 0.57, inclusive="both")
    fairness_columns = [column.name for column in schema if column.fairness_sensitive and column.name in adjusted.columns]
    if not borderline_mask.any() or not fairness_columns:
        return adjusted

    pivot_column = "race" if "race" in fairness_columns else fairness_columns[0]
    rates = adjusted.groupby(pivot_column)["loan_approved"].mean().fillna(0)
    if rates.empty:
        return adjusted
    best_group = rates.idxmax()
    best_rate = rates.max()

    for group, group_rate in rates.items():
        if group == best_group:
            continue
        gap = best_rate - group_rate
        if gap <= 0.10:
            continue
        group_mask = borderline_mask & adjusted[pivot_column].eq(group)
        flip_probability = min(1.0, gap * ratio_fraction * 2)
        flip_mask = group_mask & (~adjusted["loan_approved"])
        if not flip_mask.any():
            continue
        candidates = adjusted[flip_mask].sample(frac=flip_probability, random_state=23).index
        adjusted.loc[candidates, "loan_approved"] = True

    return adjusted

def apply_measurement_bias(df: pd.DataFrame, config: DeBiasConfig, schema: list[SchemaColumn]) -> pd.DataFrame:
    if not config.measurementNoise.enabled:
        return df

    adjusted = df.copy()
    rng = np.random.default_rng(5)
    sensitive_or_financial = {
        column.name
        for column in schema
        if column.type == "numerical" and (column.fairness_sensitive or column.name in FINANCIAL_SIGNAL_COLUMNS or column.name in {"loan_amount", "loan_term_months", "interest_rate"})
    }

    for column in schema:
        if column.name not in sensitive_or_financial or column.name not in adjusted.columns:
            continue

        lower, upper = numerical_bounds(column, adjusted[column.name].fillna(0))
        sigma = config.measurementNoise.incomeSigma
        if column.name in {"credit_score", "age", "prior_defaults", "debt_to_income", "loan_term_months", "interest_rate"}:
            sigma = max((upper - lower) * (config.measurementNoise.creditScoreSigma / 100), 0.01)
        noise = rng.normal(0, sigma, len(adjusted))
        values = np.clip(adjusted[column.name].fillna((lower + upper) / 2).astype(float) + noise, lower, upper)
        if pd.api.types.is_integer_dtype(adjusted[column.name]):
            adjusted[column.name] = np.round(values).astype(int)
        else:
            adjusted[column.name] = np.round(values, 4)

    adjusted["approval_score"] = compute_approval_score(adjusted, schema).round(4)
    adjusted["loan_approved"] = adjusted["approval_score"] >= 0.52
    return adjusted

def create_biased_baseline(df: pd.DataFrame, schema: list[SchemaColumn]) -> pd.DataFrame:
    return apply_historical_bias(df, correction=0, schema=schema)

def apply_bias_pipeline(df: pd.DataFrame, config: DeBiasConfig, schema: list[SchemaColumn]) -> pd.DataFrame:
    adjusted = apply_representation_bias(df, config, schema)
    adjusted = apply_historical_bias(adjusted, config.historicalCorrection, schema)
    adjusted = apply_label_bias(adjusted, config.labelCorrection, schema)
    adjusted = apply_measurement_bias(adjusted, config, schema)
    adjusted["approval_score"] = compute_approval_score(adjusted, schema).round(4)
    adjusted["loan_approved"] = adjusted["loan_approved"].astype(bool)
    return adjusted
