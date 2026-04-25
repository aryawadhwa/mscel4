from __future__ import annotations

import math

import pandas as pd

from src.core.schema_catalog import AGE_BUCKETS
from src.api.schemas import SchemaColumn


METRIC_TOOLTIPS = {
    "DPD": "How big is the approval gap between protected groups?",
    "DIR": "Does the least-approved group get at least 90% of the opportunities of the most-approved group?",
    "LCS": "For applicants on the edge, does protected-group membership affect the decision?",
    "REI": "Are monitored groups represented in a balanced way?",
    "OFS": "A combined score summarizing fairness across the key metrics.",
}


def _safe_std(series: pd.Series) -> float:
    value = float(series.std()) if len(series) > 1 else 0.0
    if math.isnan(value):
        return 0.0
    return value


def _safe_mean(series: pd.Series) -> float:
    value = float(series.mean()) if len(series) else 0.0
    if math.isnan(value):
        return 0.0
    return value


def monitored_columns(schema: list[SchemaColumn]) -> list[SchemaColumn]:
    return [column for column in schema if column.fairness_sensitive]


def _group_series(df: pd.DataFrame, column: SchemaColumn) -> pd.Series:
    if column.name not in df.columns:
        return pd.Series(dtype="object")
    series = df[column.name]
    if column.name == "age":
        return pd.cut(series.astype(float), bins=[0, 24, 34, 44, 54, 120], labels=AGE_BUCKETS, include_lowest=True).astype(str)
    return series.astype(str)


def compute_fairness_metrics(df: pd.DataFrame, schema: list[SchemaColumn]) -> dict[str, float]:
    if df.empty:
        return {"DPD": 0.0, "DIR": 1.0, "LCS": 1.0, "REI": 1.0, "OFS": 100.0}

    protected = monitored_columns(schema)
    if not protected:
        return {"DPD": 0.0, "DIR": 1.0, "LCS": 1.0, "REI": 1.0, "OFS": 100.0}

    dpd_values: list[float] = []
    dir_values: list[float] = []
    lcs_values: list[float] = []
    rei_values: list[float] = []
    borderline = df[(df["approval_score"] > 0.47) & (df["approval_score"] < 0.57)] if "approval_score" in df.columns else df.iloc[0:0]

    for column in protected:
        groups = _group_series(df, column)
        approval_by_group = df.groupby(groups)["loan_approved"].mean().fillna(0)
        if approval_by_group.empty:
            continue
        dpd_values.append(float(approval_by_group.max() - approval_by_group.min()))
        dir_values.append(float(approval_by_group.min() / approval_by_group.max()) if approval_by_group.max() > 0 else 1.0)

        if len(borderline) > 0:
            borderline_groups = _group_series(borderline, column)
            lcs_values.append(1 - float(borderline.groupby(borderline_groups)["loan_approved"].mean().fillna(0).std()))
        else:
            lcs_values.append(1.0)

        group_pcts = groups.value_counts(normalize=True)
        mean_pct = _safe_mean(group_pcts)
        rei_values.append(float(1 - (_safe_std(group_pcts) / mean_pct)) if mean_pct > 0 else 1.0)

    dpd = max(dpd_values) if dpd_values else 0.0
    dir_ratio = min(dir_values) if dir_values else 1.0
    lcs = sum(lcs_values) / len(lcs_values) if lcs_values else 1.0
    rei = sum(rei_values) / len(rei_values) if rei_values else 1.0

    ofs = round(
        max(0, 1 - dpd / 0.2) * 25
        + min(max(dir_ratio, 0.0), 1.0) * 25
        + min(max(lcs, 0.0), 1.0) * 25
        + min(max(rei, 0.0), 1.0) * 25,
        1,
    )

    return {
        "DPD": round(dpd, 4),
        "DIR": round(dir_ratio, 4),
        "LCS": round(lcs, 4),
        "REI": round(rei, 4),
        "OFS": ofs,
    }


def metric_status(metric_name: str, value: float) -> str:
    if metric_name == "DPD":
        if value < 0.05:
            return "fair"
        if value < 0.10:
            return "moderate"
        return "biased"
    if metric_name == "DIR":
        if value > 0.90:
            return "fair"
        if value > 0.80:
            return "moderate"
        return "biased"
    if metric_name == "LCS":
        if value > 0.95:
            return "fair"
        if value > 0.85:
            return "moderate"
        return "biased"
    if metric_name == "REI":
        if value > 0.90:
            return "fair"
        if value > 0.80:
            return "moderate"
        return "biased"
    if value >= 80:
        return "fair"
    if value >= 60:
        return "moderate"
    return "biased"


def build_metric_cards(metrics: dict[str, float]) -> list[dict[str, str | float]]:
    cards = []
    for key in ("DPD", "DIR", "LCS", "REI"):
        cards.append(
            {
                "key": key,
                "value": metrics[key],
                "status": metric_status(key, metrics[key]),
                "description": METRIC_TOOLTIPS[key],
            }
        )
    return cards


def _approval_groups(df: pd.DataFrame, column: SchemaColumn) -> list[dict[str, float | str]]:
    groups = _group_series(df, column)
    return (
        df.groupby(groups)["loan_approved"]
        .mean()
        .reset_index()
        .rename(columns={"loan_approved": "approvalRate", column.name: "name"})
        .to_dict(orient="records")
    )


def _representation_groups(df: pd.DataFrame, column: SchemaColumn) -> list[dict[str, float | str]]:
    groups = _group_series(df, column)
    return groups.value_counts(normalize=True).mul(100).rename_axis("name").reset_index(name="representationPct").to_dict(orient="records")


def build_distribution_summary(df: pd.DataFrame, schema: list[SchemaColumn]) -> dict[str, list[dict[str, object]]]:
    protected = monitored_columns(schema)
    approval_rate_by_protected = [
        {"column": column.name, "groups": _approval_groups(df, column)}
        for column in protected
        if column.name in df.columns
    ]
    representation_by_protected = [
        {"column": column.name, "groups": _representation_groups(df, column)}
        for column in protected
        if column.name in df.columns
    ]

    numeric_candidates = [name for name in ("credit_score", "annual_income", "loan_amount", "debt_to_income") if name in df.columns]
    numeric_breakdowns: list[dict[str, object]] = []
    for numeric_name in numeric_candidates[:2]:
        for column in protected[:2]:
            groups = _group_series(df, column)
            values = (
                df.groupby(groups)[numeric_name]
                .mean()
                .reset_index()
                .rename(columns={numeric_name: "average", column.name: "name"})
                .to_dict(orient="records")
            )
            numeric_breakdowns.append({"column": numeric_name, "by": column.name, "values": values})

    return {
        "approvalRateByProtected": approval_rate_by_protected,
        "representationByProtected": representation_by_protected,
        "numericBreakdowns": numeric_breakdowns,
    }
