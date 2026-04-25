from __future__ import annotations

import json
import os
from typing import Any

from openai import OpenAI

from src.api.schemas import DeBiasConfig


SYSTEM_PROMPT = """You are a fairness constraint interpreter for de.bias, a synthetic
credit dataset generator. The user will describe a fairness requirement
in plain English. Translate it into a JSON config delta.

Respond ONLY with valid JSON — no preamble, no markdown fences.
Config schema you can modify:
{
  "datasetSize": number,
  "representation": {
    "femalePct": number,
    "minorityPct": number,
    "ruralPct": number
  },
  "historicalCorrection": number,
  "labelCorrection": number,
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
Only include keys you want to change."""

SCHEMA_SUGGESTION_PROMPT = """You are a dataset schema advisor for de.bias, a synthetic credit
data generator. The user will describe their use case. You will
suggest additional columns they should include in their dataset
that they haven't already selected.

Already selected columns will be provided. Do not suggest columns
already in the list.

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
Limit to 4-6 suggestions maximum. Prioritize columns that are
relevant to fairness and bias detection in credit/finance contexts."""


def _client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    return OpenAI(api_key=api_key)


def parse_json_response(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.replace("json", "", 1).strip()
    return json.loads(cleaned)


def test_connection() -> tuple[bool, str]:
    try:
        client = _client()
        client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            max_tokens=1,
            messages=[{"role": "user", "content": "ping"}],
        )
        return True, "Connected"
    except Exception as exc:
        return False, str(exc)


def interpret_fairness_prompt(instruction: str, current_config: DeBiasConfig) -> dict[str, Any]:
    client = _client()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.3,
        max_tokens=800,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps(
                    {"instruction": instruction, "currentConfig": current_config.model_dump()},
                    ensure_ascii=True,
                ),
            },
        ],
    )
    content = response.choices[0].message.content or "{}"
    return parse_json_response(content)


def suggest_schema_columns(description: str, already_selected: list[str]) -> dict[str, Any]:
    client = _client()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.4,
        max_tokens=1200,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SCHEMA_SUGGESTION_PROMPT},
            {
                "role": "user",
                "content": json.dumps(
                    {"description": description, "alreadySelected": already_selected},
                    ensure_ascii=True,
                ),
            },
        ],
    )
    content = response.choices[0].message.content or '{"suggestions":[]}'
    return parse_json_response(content)
