"""Gemini client for de.bias.

Auth modes (auto-detected):
  • ADC  — GOOGLE_CLOUD_PROJECT is set → uses vertexai SDK (Cloud Run / GCP)
  • Key  — GOOGLE_API_KEY is set       → uses google-genai SDK (local dev)
"""

from __future__ import annotations

import json
import os
from typing import Any

from google import genai
from google.genai import types as genai_types

try:
    import vertexai
    from vertexai.generative_models import GenerativeModel as VertexGenerativeModel
    _VERTEXAI_AVAILABLE = True
except ImportError:
    _VERTEXAI_AVAILABLE = False

from src.api.schemas import DeBiasConfig

_MODEL_NAME = "gemini-1.5-flash"


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def _use_adc() -> bool:
    """True when running on Cloud Run / GCP — switches to ADC via vertexai SDK."""
    return bool(os.getenv("GOOGLE_CLOUD_PROJECT")) and _VERTEXAI_AVAILABLE


def _genai_client() -> genai.Client:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY is not configured (local dev mode requires this)")
    return genai.Client(api_key=api_key)


def _configure_vertexai() -> None:
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    vertexai.init(project=project, location=location)  # ADC — no key needed


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_CONSTRAINT_SYSTEM = """You are a fairness constraint interpreter for de.bias, a synthetic
credit dataset generator powered by Google Gemini. The user describes a fairness
requirement in plain English — including quantitative constraints like
"within 5 percentage points" or "approval rate gap below 10%". Translate it
into a JSON config delta that will make the mitigation engine satisfy the constraint.

Respond ONLY with valid JSON — no preamble, no markdown fences.
Config schema you can modify:
{
  "datasetSize": number,
  "representation": {
    "femalePct": number,
    "minorityPct": number,
    "ruralPct": number
  },
  "historicalCorrection": number,       // 0-100: strength of resampling layer
  "labelCorrection": number,            // 0-100: strength of threshold adjustment
  "measurementNoise": {
    "enabled": boolean,
    "creditScoreSigma": number,
    "incomeSigma": number
  },
  "customFilters": [
    {
      "group": string,
      "incomeMin": number,
      "targetMinRepresentationPct": number
    }
  ],
  "explanation": string
}
Only include keys you want to change.
For quantitative constraints (e.g. "approval gap < 5pp"), increase
historicalCorrection and labelCorrection toward 100 proportionally.
Always include an "explanation" key: one sentence explaining what you changed and why."""

_SCHEMA_SYSTEM = """You are a dataset schema advisor for de.bias, a synthetic credit
data generator powered by Google Gemini. The user describes their use case. You
suggest additional columns they should include that they haven't already selected.

Already selected columns will be provided. Do not suggest them again.

Respond ONLY with valid JSON — no markdown, no preamble:
{
  "suggestions": [
    {
      "name": "string",
      "type": "numerical" | "categorical" | "boolean",
      "config": {
        "min": number,
        "max": number,
        "distribution": "normal" | "log-normal" | "uniform" | "weighted",
        "options": ["string"],
        "weights": [number],
        "base_rate": number
      },
      "fairness_sensitive": boolean,
      "reason": "string"
    }
  ]
}
Limit to 4-6 suggestions maximum. Prioritise columns relevant to fairness and
bias detection in credit/finance contexts."""

_NARRATIVE_SYSTEM = """You are a fair lending compliance analyst. Given the following fairness metrics
for a synthetic credit dataset, produce a plain-English compliance report.
No bullet points. Professional tone. No hedging language. Exactly four paragraphs:
  1. Overall finding.
  2. Specific metric changes.
  3. Remaining concerns.
  4. Recommendation."""


# ---------------------------------------------------------------------------
# Internal: generate content via whichever backend is active
# ---------------------------------------------------------------------------

def _generate_json(prompt: str, temperature: float = 0.3) -> str:
    """Returns raw JSON string from Gemini (structured output mode)."""
    if _use_adc():
        _configure_vertexai()
        model = VertexGenerativeModel(
            _MODEL_NAME,
            generation_config={"temperature": temperature, "response_mime_type": "application/json"},
        )
        response = model.generate_content(prompt)
        return response.text
    else:
        client = _genai_client()
        response = client.models.generate_content(
            model=_MODEL_NAME,
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                temperature=temperature,
                response_mime_type="application/json",
            ),
        )
        return response.text


def _generate_text(prompt: str, temperature: float = 0.35) -> str:
    """Returns plain text from Gemini."""
    if _use_adc():
        _configure_vertexai()
        model = VertexGenerativeModel(
            _MODEL_NAME,
            generation_config={"temperature": temperature},
        )
        response = model.generate_content(prompt)
        return response.text
    else:
        client = _genai_client()
        response = client.models.generate_content(
            model=_MODEL_NAME,
            contents=prompt,
            config=genai_types.GenerateContentConfig(temperature=temperature),
        )
        return response.text


def _parse_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.replace("json", "", 1).strip()
    return json.loads(cleaned)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def test_connection() -> tuple[bool, str]:
    try:
        if _use_adc():
            _configure_vertexai()
            model = VertexGenerativeModel(_MODEL_NAME)
            model.generate_content("ping")
            project = os.getenv("GOOGLE_CLOUD_PROJECT")
            return True, f"Connected via ADC — project: {project}, model: {_MODEL_NAME}"
        else:
            client = _genai_client()
            client.models.generate_content(
                model=_MODEL_NAME,
                contents="ping",
                config=genai_types.GenerateContentConfig(max_output_tokens=1),
            )
            return True, f"Connected via API key — model: {_MODEL_NAME}"
    except Exception as exc:
        return False, str(exc)


def interpret_fairness_prompt(
    instruction: str,
    current_config: DeBiasConfig,
) -> dict[str, Any]:
    prompt = (
        f"{_CONSTRAINT_SYSTEM}\n\n"
        f"Current config: {current_config.model_dump_json()}\n"
        f"User instruction: {instruction}"
    )
    return _parse_json(_generate_json(prompt, temperature=0.3))


def suggest_schema_columns(
    description: str,
    already_selected: list[str],
) -> dict[str, Any]:
    prompt = (
        f"{_SCHEMA_SYSTEM}\n\n"
        f"Already selected: {json.dumps(already_selected)}\n"
        f"Use case: {description}"
    )
    return _parse_json(_generate_json(prompt, temperature=0.4))


def generate_fairness_narrative(
    before_metrics: dict[str, float],
    after_metrics: dict[str, float],
    before_approval_by_group: list[dict],
    after_approval_by_group: list[dict],
    dataset_size: int,
    active_layers: list[str] | None = None,
) -> str:
    """Build the structured compliance prompt and call Gemini for a 4-paragraph report.

    Metric mapping to standard fair-lending terminology:
      DPD  → Statistical Parity Difference (SPD)  — approval rate gap
      DIR  → Disparate Impact Ratio (DIR)          — 0.8 = EEOC threshold
      LCS  → Equal Opportunity Difference (EOD)   — borderline label consistency
      REI  → Representation Equity Index

    Upgrade path: replace this function with Vertex AI Model Evaluation +
    fairness slicing for dual-source evaluation:
        model.evaluate(
            slicing_specs=[aiplatform.slices.Slice(spec="race")],
            explanation_specs=[aiplatform.explain.ExplanationSpec()]
        )
    That gives Google's official fairness metrics alongside ours — two independent
    evaluations on the same model, which is a strong signal of thoroughness.
    """
    def _fmt_rates(approval_list: list[dict]) -> str:
        lines = []
        for entry in approval_list:
            col = entry.get("column", "attribute")
            for g in entry.get("groups", []):
                name = g.get("name", "unknown")
                rate = g.get("approvalRate", 0)
                lines.append(f"  {col}/{name}: {rate:.1%}")
        return "\n".join(lines) if lines else "  (no group data)"

    layers_str = ", ".join(active_layers) if active_layers else "all mitigation layers"

    prompt = f"""{_NARRATIVE_SYSTEM}

## Dataset Summary
- Records: {dataset_size}
- Mitigation layers applied: {layers_str}

## Before Mitigation
- Approval rates by group:
{_fmt_rates(before_approval_by_group)}
- Disparate impact ratio (DIR): {before_metrics.get('DIR', 'N/A')}
- Statistical parity difference (SPD ≈ DPD): {before_metrics.get('DPD', 'N/A')}
- Equal opportunity difference (EOD ≈ LCS): {before_metrics.get('LCS', 'N/A')}
- Representation equity (REI): {before_metrics.get('REI', 'N/A')}
- Overall fairness score: {before_metrics.get('OFS', 'N/A')} / 100

## After Mitigation
- Approval rates by group:
{_fmt_rates(after_approval_by_group)}
- Disparate impact ratio (DIR): {after_metrics.get('DIR', 'N/A')}
- Statistical parity difference (SPD ≈ DPD): {after_metrics.get('DPD', 'N/A')}
- Equal opportunity difference (EOD ≈ LCS): {after_metrics.get('LCS', 'N/A')}
- Representation equity (REI): {after_metrics.get('REI', 'N/A')}
- Overall fairness score: {after_metrics.get('OFS', 'N/A')} / 100

## Instructions
Write 4 paragraphs. First paragraph: overall finding. Second: specific metric
changes. Third: remaining concerns. Fourth: recommendation.
No bullet points. Professional tone. No hedging language."""

    return _generate_text(prompt, temperature=0.35)
