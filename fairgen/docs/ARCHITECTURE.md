# de.bias Architecture

## System Flow

1. React frontend captures configuration and AI fairness instructions.
2. FastAPI backend generates a seed credit dataset.
3. SDV synthesizes correlated synthetic records.
4. de.bias bias mitigation layers transform the dataset in order.
5. Fairness metrics are computed for raw and mitigated outputs.
6. The frontend renders tables, charts, reports, and export actions.

## Backend Modules

- `main.py`: API routes and response assembly
- `generator.py`: metadata, seed dataset, SDV sampling
- `bias_layers.py`: fairness mitigation layers
- `fairness.py`: metric computation and report helpers
- `openai_client.py`: GPT-4o mini constraint interpreter
- `schemas.py`: shared config and response models

## Frontend Modules

- `frontend/src/App.jsx`: overall composition and state orchestration
- `frontend/src/components/ConfigPanel.jsx`: configuration controls
- `frontend/src/components/AIPromptBox.jsx`: constraint input and explanation panel
- `frontend/src/components/DataTable.jsx`: tabular dataset preview
- `frontend/src/components/DistributionCharts.jsx`: before/after charts
- `frontend/src/components/FairnessReport.jsx`: score and metric cards
- `frontend/src/components/DownloadPanel.jsx`: download and export actions

## Delivery Notes

- SDV should be optional at import time so the app can still boot without it.
- OpenAI and HuggingFace integrations should fail gracefully when keys are missing.
- "Before" metrics should be calculated from a deliberately biased baseline to make the mitigation effect visible.
