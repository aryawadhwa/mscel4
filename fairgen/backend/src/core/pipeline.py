"""Deep pipeline module for de.bias generation.

Architecture: Ports & Adapters + functional entry points (hybrid Design 3+4).

Public surface:
    run_pipeline(schema, config, *, synthesizer=..., narrative=..., session_store=...) -> GenerationResult
    serialize_result(result: GenerationResult) -> dict

External dependencies are expressed as Protocols. Tests inject fakes as keyword
args. Production uses module-level defaults that check env vars lazily at
call time — so importing this module never fails, even without credentials.

    # Production (two lines in the HTTP handler):
    result = run_pipeline(schema, config)
    return serialize_result(result)

    # Test (inject fakes, zero I/O):
    result = run_pipeline(schema, config, narrative=FakeNarrative(), session_store=None)
    assert result.after_metrics["DIR"] > result.before_metrics["DIR"]
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

import pandas as pd

from src.domain.bias_layers import apply_bias_pipeline, create_biased_baseline
from src.core.fairness import (
    build_distribution_summary,
    build_metric_cards,
    compute_fairness_metrics,
    monitored_columns,
)
from src.domain.generator import GenerationArtifacts, SDV_VERSION, sample_base_dataset

# Re-export so tests only need to import from pipeline
__all__ = [
    "GenerationResult",
    "GenerationArtifacts",
    "DataSynthesisPort",
    "NarrativePort",
    "SessionPort",
    "run_pipeline",
    "serialize_result",
]
from src.api.schemas import DeBiasConfig, SchemaColumn


# ---------------------------------------------------------------------------
# Loading messages (moved from main.py — pipeline concern, not HTTP concern)
# ---------------------------------------------------------------------------

LOADING_MESSAGES: list[str] = [
    "Fitting SDV synthesizer...",
    "Sampling base records...",
    "Applying historical bias correction...",
    "Enforcing representation constraints...",
    "Correcting label bias...",
    "Injecting measurement noise parity...",
    "Computing fairness metrics...",
]


# ---------------------------------------------------------------------------
# Intermediate type — the missing dataclass
# ---------------------------------------------------------------------------

@dataclass
class GenerationResult:
    """Typed result of a full generation + mitigation run.

    Carries both DataFrames so callers (Vertex evaluation, Firestore save,
    HTTP serialization) all read from one place instead of re-computing.
    """
    before_df: pd.DataFrame
    after_df: pd.DataFrame
    before_metrics: dict[str, float]
    after_metrics: dict[str, float]
    before_charts: dict[str, Any]
    after_charts: dict[str, Any]
    schema: list[SchemaColumn]
    config: DeBiasConfig
    source: str                   # "sdv" | "seed-fallback"
    generation_time_ms: float
    narrative: str | None = None


# ---------------------------------------------------------------------------
# Ports — explicit Protocol definitions for every external dependency
# ---------------------------------------------------------------------------

@runtime_checkable
class DataSynthesisPort(Protocol):
    """Produces a base DataFrame from config + schema (may use SDV or fallback)."""
    def sample(
        self,
        config: DeBiasConfig,
        schema: list[SchemaColumn],
    ) -> GenerationArtifacts: ...


@runtime_checkable
class NarrativePort(Protocol):
    """Generates a plain-English compliance narrative from fairness metrics.

    Returns None on any failure — the pipeline must never fail because of
    a missing or broken narrative.
    """
    def generate(
        self,
        before_metrics: dict[str, float],
        after_metrics: dict[str, float],
        before_approval_by_group: list[dict],
        after_approval_by_group: list[dict],
        dataset_size: int,
    ) -> str | None: ...


@runtime_checkable
class SessionPort(Protocol):
    """Persists a generation session (e.g. to Firestore).

    Failures are silently swallowed by the pipeline — session save is
    additive, never load-bearing.
    """
    def save(
        self,
        result: GenerationResult,
        schema: list[dict],
        config: dict,
    ) -> str: ...


# ---------------------------------------------------------------------------
# Adapters — concrete implementations of each port
# ---------------------------------------------------------------------------

class SDVSynthesizerAdapter:
    """Wraps generator.sample_base_dataset (SDV + seed-fallback)."""

    def sample(self, config: DeBiasConfig, schema: list[SchemaColumn]) -> GenerationArtifacts:
        return sample_base_dataset(config, schema)


class GeminiNarrativeAdapter:
    """Wraps gemini_client.generate_fairness_narrative. Never raises."""

    def generate(
        self,
        before_metrics: dict[str, float],
        after_metrics: dict[str, float],
        before_approval_by_group: list[dict],
        after_approval_by_group: list[dict],
        dataset_size: int,
    ) -> str | None:
        try:
            from src.adapters.gemini_client import generate_fairness_narrative
            return generate_fairness_narrative(
                before_metrics=before_metrics,
                after_metrics=after_metrics,
                before_approval_by_group=before_approval_by_group,
                after_approval_by_group=after_approval_by_group,
                dataset_size=dataset_size,
            )
        except Exception:
            return None


class FirestoreSessionAdapter:
    """Wraps firestore_client.save_session. Never raises."""

    def save(self, result: GenerationResult, schema: list[dict], config: dict) -> str:
        try:
            from src.adapters.firestore_client import save_session
            return save_session(
                {
                    "metrics": result.after_metrics,
                    "beforeMetrics": result.before_metrics,
                    "geminiNarrative": result.narrative,
                    "generationTimeSeconds": round(result.generation_time_ms / 1000, 2),
                    "dataset": [],  # don't persist full dataset rows
                },
                schema=schema,
                config=config,
            )
        except Exception:
            return ""


# ---------------------------------------------------------------------------
# Sentinel — distinguishes "not provided" from "explicitly None"
# ---------------------------------------------------------------------------

_SENTINEL = object()


# ---------------------------------------------------------------------------
# Pipeline entry point
# ---------------------------------------------------------------------------

def run_pipeline(
    schema: list[SchemaColumn],
    config: DeBiasConfig,
    *,
    synthesizer: DataSynthesisPort | None = None,
    narrative: NarrativePort | None | object = _SENTINEL,
    session_store: SessionPort | None | object = _SENTINEL,
) -> GenerationResult:
    """Run the full generation + mitigation pipeline.

    Parameters
    ----------
    schema:
        List of SchemaColumn definitions (must include loan_approved + ≥1 protected).
    config:
        DeBiasConfig controlling dataset size and mitigation layer strengths.
    synthesizer:
        Port for synthetic data generation. Defaults to SDVSynthesizerAdapter.
        Pass a fake for testing.
    narrative:
        Port for Gemini compliance report generation. Defaults to
        GeminiNarrativeAdapter when credentials are present, None otherwise.
        Pass None to explicitly disable. Pass a fake for testing.
    session_store:
        Port for session persistence. Defaults to FirestoreSessionAdapter when
        GOOGLE_CLOUD_PROJECT is set, None otherwise.
        Pass None to explicitly disable. Pass a fake for testing.

    Returns
    -------
    GenerationResult — a typed intermediate result. Call serialize_result() to
    convert to the HTTP response dict.
    """
    # Resolve defaults lazily — env vars are checked at call time, not import time.
    if synthesizer is None:
        synthesizer = SDVSynthesizerAdapter()

    if narrative is _SENTINEL:
        has_gemini = bool(os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_CLOUD_PROJECT"))
        narrative = GeminiNarrativeAdapter() if has_gemini else None

    if session_store is _SENTINEL:
        session_store = FirestoreSessionAdapter() if os.getenv("GOOGLE_CLOUD_PROJECT") else None

    # ── Pure pipeline (no I/O below this line until narrative + session_store) ──
    started = time.perf_counter()

    artifacts = synthesizer.sample(config, schema)
    base_df = artifacts.base_dataset.copy()

    if "approval_score" not in base_df.columns:
        base_df["approval_score"] = 0.5
    if "loan_approved" not in base_df.columns:
        base_df["loan_approved"] = False

    before_df = create_biased_baseline(base_df, schema)
    after_df = apply_bias_pipeline(base_df, config, schema)

    before_metrics = compute_fairness_metrics(before_df, schema)
    after_metrics = compute_fairness_metrics(after_df, schema)

    before_charts = build_distribution_summary(before_df, schema)
    after_charts = build_distribution_summary(after_df, schema)

    generation_time_ms = round((time.perf_counter() - started) * 1000, 1)

    # ── Non-blocking I/O — narrative (Gemini) ──────────────────────────────
    narrative_text: str | None = None
    if narrative is not None:
        narrative_text = narrative.generate(
            before_metrics=before_metrics,
            after_metrics=after_metrics,
            before_approval_by_group=before_charts.get("approvalRateByProtected", []),
            after_approval_by_group=after_charts.get("approvalRateByProtected", []),
            dataset_size=len(after_df),
        )

    result = GenerationResult(
        before_df=before_df,
        after_df=after_df,
        before_metrics=before_metrics,
        after_metrics=after_metrics,
        before_charts=before_charts,
        after_charts=after_charts,
        schema=schema,
        config=config,
        source=artifacts.source,
        generation_time_ms=generation_time_ms,
        narrative=narrative_text,
    )

    # ── Non-blocking I/O — session persistence (Firestore) ─────────────────
    if session_store is not None:
        session_store.save(
            result,
            schema=[c.model_dump() for c in schema],
            config=config.model_dump(),
        )

    return result


# ---------------------------------------------------------------------------
# Serializer — pure function, converts GenerationResult → HTTP response dict
# ---------------------------------------------------------------------------

def serialize_result(result: GenerationResult) -> dict[str, Any]:
    """Convert a GenerationResult to the HTTP response dict.

    Pure function — no I/O, fully testable. NaN/Inf sanitization lives here
    (not inside the pipeline) because it's a serialization concern.
    """
    output_columns = [c.name for c in result.schema]
    monitored = [c.name for c in monitored_columns(result.schema)]

    clean_after = result.after_df.reindex(columns=output_columns).copy()
    clean_after = clean_after.replace([float("inf"), float("-inf")], 0).fillna(0)

    clean_before = result.before_df.reindex(columns=output_columns).copy()
    clean_before = clean_before.replace([float("inf"), float("-inf")], 0).fillna(0)

    time_s = round(result.generation_time_ms / 1000, 2)

    return {
        "dataset": clean_after.to_dict(orient="records"),
        "beforeDataset": clean_before.to_dict(orient="records"),
        "metrics": result.after_metrics,
        "beforeMetrics": result.before_metrics,
        "fairnessReport": {
            "overallScore": result.after_metrics["OFS"],
            "metricCards": build_metric_cards(result.after_metrics),
            "beforeCards": build_metric_cards(result.before_metrics),
        },
        "charts": {
            "before": result.before_charts,
            "after": result.after_charts,
        },
        "geminiNarrative": result.narrative,
        "generationTimeMs": result.generation_time_ms,
        "generationTimeSeconds": time_s,
        "sdvVersion": SDV_VERSION,
        "generatorSource": result.source,
        "loadingMessages": LOADING_MESSAGES + [f"Done ✓ — Generated in {time_s}s"],
        "monitoredColumns": monitored,
        "schema": [c.model_dump() for c in result.schema],
    }
