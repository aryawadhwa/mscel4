# fairgen

`fairgen` is a hardware-accelerated, physics-based degradation simulation engine and generative data augmentation pipeline built for Apple Silicon (MLX/MPS).

## Architecture

The repository enforces a strict Domain-Driven Design (DDD) layout:

- **`backend/src/api/`**: FastAPI routing and Pydantic validation boundaries.
- **`backend/src/adapters/`**: I/O drivers for volatile external services (Firestore, Gemini, OpenAI, HuggingFace).
- **`backend/src/core/`**: Orchestration logic and ML fairness metrics evaluation.
- **`backend/src/domain/`**: Financial heuristics, deterministic latent profiles, and statistical perturbation mechanics strictly decoupled from state.
- **`frontend/src/`**: React/Vite UI split into `pages/` (views), `components/` (reusable blocks), and `config/`.

## Hardware Acceleration

Tensor operations within the data generation and fairness metric pipelines are explicitly optimized for Apple Silicon via `mlx` and PyTorch MPS backends. 

## Local Setup

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run the API server
PYTHONPATH=./ uvicorn src.api.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Testing

Validation is strictly boundary-focused. Pure heuristics and statistical engines are tested independently of external data synthesis models.

```bash
cd backend
PYTHONPATH=./ pytest tests/ -v
```
