# Phase 1: Foundation

## Goal

Stand up the project skeleton and a reliable backend foundation that can generate a deterministic seed credit dataset, validate config, and compute fairness metrics locally.

## Scope

- Repository structure
- Shared schema definitions
- Seed data generator
- Fairness metric engine
- FastAPI `/health`
- Initial `/generate` stub using seed-only fallback
- Frontend scaffold placeholder

## Done When

- The repo has docs, backend, frontend, examples, and notebooks directories.
- FastAPI starts successfully without SDV installed.
- `/health` returns backend status and dependency availability.
- `/generate` returns a valid dataset plus fairness metrics from local seed-based generation.
