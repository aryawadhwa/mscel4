# Phase 2: Backend Pipeline

## Goal

Implement the full synthetic generation pipeline with SDV integration and bias mitigation layers.

## Scope

- SDV `GaussianCopulaSynthesizer`
- Single table metadata
- Historical bias layer
- Representation layer
- Label correction layer
- Measurement noise layer
- Before/after metric computation
- OpenAI prompt interpreter endpoint
- HuggingFace export endpoint

## Risks

- SDV may be unavailable in some environments.
- LLM responses must be parsed defensively.
- Representation constraints need to preserve plausible distributions.

## Done When

- `/generate` uses SDV when available and falls back predictably otherwise.
- `/prompt` returns config deltas plus explanation text.
- `/export/huggingface` can publish a dataset when credentials are provided.
