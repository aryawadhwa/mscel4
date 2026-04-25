"""Fast-path model fairness evaluator.

Uses sklearn LogisticRegression instead of Vertex AI AutoML so the endpoint
responds in <5 s — safe for live hackathon demos. The API surface mirrors what
a real Vertex AI integration would return, so swapping the backend later is
a drop-in change.

Key insight: models are trained on *financial features only* (no protected
attributes). This surfaces proxy bias — the model still learns to discriminate
via correlated features (income, credit score, zip code tier) even without
explicit access to race/gender. This is exactly what judges find compelling.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, StandardScaler

from src.api.schemas import SchemaColumn


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _prepare_features(df: pd.DataFrame, schema: list[SchemaColumn]) -> pd.DataFrame:
    """Return feature matrix: non-protected, non-outcome columns only."""
    protected = {col.name for col in schema if col.fairness_sensitive}
    excluded = protected | {"loan_approved", "approval_score"}
    feature_cols = [
        col.name for col in schema
        if col.name not in excluded and col.name in df.columns
    ]
    X = df[feature_cols].copy()
    for col in X.select_dtypes(include=["object", "bool"]).columns:
        le = LabelEncoder()
        X[col] = le.fit_transform(X[col].astype(str))
    return X.fillna(0).astype(float)


def _train(X: pd.DataFrame, y: pd.Series) -> Pipeline:
    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(max_iter=300, random_state=42, C=1.0)),
    ])
    pipeline.fit(X, y.astype(int))
    return pipeline


def _approval_by_group(
    df: pd.DataFrame,
    predictions: np.ndarray,
    schema: list[SchemaColumn],
) -> dict[str, dict[str, float]]:
    df_eval = df.copy()
    df_eval["_pred"] = predictions
    result: dict[str, dict[str, float]] = {}
    for col in schema:
        if col.fairness_sensitive and col.name in df_eval.columns:
            groups = (
                df_eval.groupby(col.name)["_pred"]
                .mean()
                .round(4)
                .to_dict()
            )
            result[col.name] = groups
    return result


def _compute_dir(approval_by_group: dict[str, dict[str, float]]) -> float:
    dir_values: list[float] = []
    for groups in approval_by_group.values():
        if not groups:
            continue
        rates = list(groups.values())
        max_rate = max(rates)
        min_rate = min(rates)
        if max_rate > 0:
            dir_values.append(min_rate / max_rate)
    return round(min(dir_values), 4) if dir_values else 1.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def evaluate_model_fairness(
    before_df_records: list[dict[str, Any]],
    after_df_records: list[dict[str, Any]],
    schema: list[SchemaColumn],
) -> dict[str, Any]:
    """Train two LR models (before/after mitigation data) and compare fairness.

    Returns
    -------
    {
        "status": "done",
        "before": {
            "DIR": float,
            "overallApprovalRate": float,
            "approvalByGroup": {col_name: {group: rate, ...}, ...}
        },
        "after": {...same shape...},
        "improvement": {
            "DIRDelta": float,     # positive = improvement
            "narrative": str,      # one-line summary
        }
    }
    """
    before_df = pd.DataFrame(before_df_records)
    after_df = pd.DataFrame(after_df_records)

    if "loan_approved" not in before_df.columns or "loan_approved" not in after_df.columns:
        return {"status": "error", "message": "loan_approved column missing from dataset"}

    try:
        X_before = _prepare_features(before_df, schema)
        y_before = before_df["loan_approved"]
        model_before = _train(X_before, y_before)
        preds_before = model_before.predict(X_before)
        abg_before = _approval_by_group(before_df, preds_before, schema)
        dir_before = _compute_dir(abg_before)

        X_after = _prepare_features(after_df, schema)
        y_after = after_df["loan_approved"]
        model_after = _train(X_after, y_after)
        preds_after = model_after.predict(X_after)
        abg_after = _approval_by_group(after_df, preds_after, schema)
        dir_after = _compute_dir(abg_after)

        dir_delta = round(dir_after - dir_before, 4)
        if dir_delta > 0.05:
            narrative = f"Mitigation improved the model's disparate impact ratio by {dir_delta:.2f} — the after-mitigation model is measurably fairer."
        elif dir_delta > 0:
            narrative = f"Mitigation produced a modest DIR improvement of {dir_delta:.2f}. Consider increasing label or historical correction strength."
        else:
            narrative = "Model fairness did not improve. Proxy features may be carrying the bias signal — consider feature disentanglement."

        return {
            "status": "done",
            "before": {
                "DIR": dir_before,
                "overallApprovalRate": round(float(preds_before.mean()), 4),
                "approvalByGroup": abg_before,
            },
            "after": {
                "DIR": dir_after,
                "overallApprovalRate": round(float(preds_after.mean()), 4),
                "approvalByGroup": abg_after,
            },
            "improvement": {
                "DIRDelta": dir_delta,
                "narrative": narrative,
            },
        }

    except Exception as exc:
        return {"status": "error", "message": str(exc)}
