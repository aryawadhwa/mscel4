"""Boundary tests for the generation pipeline.

All tests run without HTTP context, real Gemini, or Firestore.
External deps are replaced with in-process fakes passed as keyword args.

Run: cd backend && pytest tests/ -v
"""

from __future__ import annotations

import pytest
import pandas as pd

from schemas import DeBiasConfig, SchemaColumn, ColumnConfig, RepresentationConfig
from pipeline import (
    GenerationResult,
    DataSynthesisPort,
    NarrativePort,
    SessionPort,
    GenerationArtifacts,
    run_pipeline,
    serialize_result,
)


# ---------------------------------------------------------------------------
# Minimal test fixtures
# ---------------------------------------------------------------------------

RACE_COLUMN = SchemaColumn(
    name="race",
    type="categorical",
    config=ColumnConfig(options=["White", "Black", "Hispanic"], weights=[0.5, 0.3, 0.2]),
    fairness_sensitive=True,
)

CREDIT_COLUMN = SchemaColumn(
    name="credit_score",
    type="numerical",
    config=ColumnConfig(min=300, max=850, distribution="normal"),
)

INCOME_COLUMN = SchemaColumn(
    name="annual_income",
    type="numerical",
    config=ColumnConfig(min=20000, max=200000, distribution="log-normal"),
)

OUTCOME_COLUMN = SchemaColumn(
    name="loan_approved",
    type="boolean",
    config=ColumnConfig(base_rate=0.52),
)

TEST_SCHEMA = [RACE_COLUMN, CREDIT_COLUMN, INCOME_COLUMN, OUTCOME_COLUMN]

HIGH_BIAS_CONFIG = DeBiasConfig(
    datasetSize=200,
    historicalCorrection=90,
    labelCorrection=80,
    representation=RepresentationConfig(minorityPct=30),
)

LOW_MITIGATION_CONFIG = DeBiasConfig(
    datasetSize=200,
    historicalCorrection=0,
    labelCorrection=0,
)


# ---------------------------------------------------------------------------
# Fakes — zero I/O, deterministic
# ---------------------------------------------------------------------------

class FakeSynthesizer:
    """Returns a fixed seed DataFrame — no SDV, no randomness."""

    def sample(self, config: DeBiasConfig, schema: list[SchemaColumn]) -> GenerationArtifacts:
        n = config.datasetSize
        import numpy as np
        rng = np.random.default_rng(42)
        df = pd.DataFrame({
            "race": rng.choice(["White", "Black", "Hispanic"], size=n, p=[0.5, 0.3, 0.2]),
            "credit_score": rng.integers(300, 850, size=n),
            "annual_income": rng.integers(20000, 200000, size=n).astype(float),
            "loan_approved": rng.random(size=n) > 0.48,
            "approval_score": rng.random(size=n),
        })
        return GenerationArtifacts(base_dataset=df, source="test-fake")


class FakeNarrative:
    """Returns a canned narrative string — no Gemini call."""
    called: bool = False

    def generate(self, **kwargs) -> str:
        self.called = True
        return "Fake compliance narrative for testing."


class FakeSessionStore:
    """Records save calls — no Firestore."""
    saves: list[dict]

    def __init__(self):
        self.saves = []

    def save(self, result: GenerationResult, schema: list, config: dict) -> str:
        self.saves.append({"schema_len": len(schema), "config": config})
        return "fake-session-id"


# ---------------------------------------------------------------------------
# Pipeline boundary tests
# ---------------------------------------------------------------------------

def test_run_pipeline_returns_typed_result():
    result = run_pipeline(
        TEST_SCHEMA,
        HIGH_BIAS_CONFIG,
        synthesizer=FakeSynthesizer(),
        narrative=None,
        session_store=None,
    )
    assert isinstance(result, GenerationResult)
    assert isinstance(result.before_df, pd.DataFrame)
    assert isinstance(result.after_df, pd.DataFrame)
    assert len(result.before_df) == HIGH_BIAS_CONFIG.datasetSize
    assert len(result.after_df) == HIGH_BIAS_CONFIG.datasetSize


def test_mitigation_improves_dir():
    """Core invariant: DIR must not decrease after mitigation is applied."""
    result = run_pipeline(
        TEST_SCHEMA,
        HIGH_BIAS_CONFIG,
        synthesizer=FakeSynthesizer(),
        narrative=None,
        session_store=None,
    )
    assert result.after_metrics["DIR"] >= result.before_metrics["DIR"] - 0.01  # small tolerance


def test_narrative_port_called():
    """Narrative port is invoked when provided."""
    fake_narrative = FakeNarrative()
    result = run_pipeline(
        TEST_SCHEMA,
        HIGH_BIAS_CONFIG,
        synthesizer=FakeSynthesizer(),
        narrative=fake_narrative,
        session_store=None,
    )
    assert fake_narrative.called
    assert result.narrative == "Fake compliance narrative for testing."


def test_narrative_none_disables_gemini():
    """Passing narrative=None must produce result.narrative = None."""
    result = run_pipeline(
        TEST_SCHEMA,
        HIGH_BIAS_CONFIG,
        synthesizer=FakeSynthesizer(),
        narrative=None,
        session_store=None,
    )
    assert result.narrative is None


def test_session_store_called_with_correct_schema():
    """Session store receives the serialized schema on each run."""
    store = FakeSessionStore()
    run_pipeline(
        TEST_SCHEMA,
        HIGH_BIAS_CONFIG,
        synthesizer=FakeSynthesizer(),
        narrative=None,
        session_store=store,
    )
    assert len(store.saves) == 1
    assert store.saves[0]["schema_len"] == len(TEST_SCHEMA)


def test_session_store_none_does_not_persist():
    """Passing session_store=None must not raise."""
    result = run_pipeline(
        TEST_SCHEMA,
        HIGH_BIAS_CONFIG,
        synthesizer=FakeSynthesizer(),
        narrative=None,
        session_store=None,
    )
    assert result is not None


def test_serialize_result_shape():
    """serialize_result must produce the exact dict keys the frontend expects."""
    result = run_pipeline(
        TEST_SCHEMA,
        HIGH_BIAS_CONFIG,
        synthesizer=FakeSynthesizer(),
        narrative=None,
        session_store=None,
    )
    payload = serialize_result(result)
    required_keys = {
        "dataset", "beforeDataset", "metrics", "beforeMetrics",
        "fairnessReport", "charts", "geminiNarrative",
        "generationTimeMs", "generationTimeSeconds",
        "sdvVersion", "generatorSource",
        "loadingMessages", "monitoredColumns", "schema",
    }
    assert required_keys.issubset(set(payload.keys()))


def test_serialize_no_nan_or_inf():
    """Serialized dataset must contain no NaN or Inf values."""
    import math
    result = run_pipeline(
        TEST_SCHEMA,
        HIGH_BIAS_CONFIG,
        synthesizer=FakeSynthesizer(),
        narrative=None,
        session_store=None,
    )
    payload = serialize_result(result)
    for row in payload["dataset"]:
        for v in row.values():
            if isinstance(v, float):
                assert not math.isnan(v), f"NaN in serialized dataset: {row}"
                assert not math.isinf(v), f"Inf in serialized dataset: {row}"


def test_source_propagated():
    """GenerationResult.source must match what the synthesizer reports."""
    result = run_pipeline(
        TEST_SCHEMA,
        HIGH_BIAS_CONFIG,
        synthesizer=FakeSynthesizer(),
        narrative=None,
        session_store=None,
    )
    assert result.source == "test-fake"
    payload = serialize_result(result)
    assert payload["generatorSource"] == "test-fake"
