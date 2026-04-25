import io
import os

import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

load_dotenv()

from src.adapters.firestore_client import list_sessions, load_session
from src.adapters.gemini_client import interpret_fairness_prompt, suggest_schema_columns, test_connection
from src.adapters.export_adapters import export_to_huggingface, export_to_googlesheets, ExportDependencyError
from src.domain.generator import SDV_AVAILABLE, SDV_VERSION
from src.core.pipeline import run_pipeline, serialize_result
from src.scripts.vertex_trainer import evaluate_model_fairness
from src.api.schemas import (
    ExportGoogleSheetsRequest,
    ExportHuggingFaceRequest,
    GenerateRequest,
    ModelEvalRequest,
    PromptRequest,
    SchemaColumn,
    SuggestColumnsRequest,
    SuggestColumnsResponse,
)

app = FastAPI(title="de.bias API", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "message": str(exc)},
        headers={
            "Access-Control-Allow-Origin": request.headers.get("Origin", "*"),
            "Access-Control-Allow-Credentials": "true",
        },
    )


# ---------------------------------------------------------------------------
# Schema validation — HTTP concern (raises HTTPException), stays in main.py
# ---------------------------------------------------------------------------

def _validate_schema(schema: list[SchemaColumn]) -> None:
    names = [c.name for c in schema]
    if len(set(names)) != len(names):
        raise HTTPException(status_code=400, detail="Schema column names must be unique.")
    if "loan_approved" not in names:
        raise HTTPException(status_code=400, detail="Schema must include the required loan_approved outcome column.")
    if not any(c.fairness_sensitive for c in schema):
        raise HTTPException(
            status_code=400,
            detail="de.bias needs at least one protected attribute column (e.g. race, gender, age) to compute fairness metrics.",
        )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    has_creds = bool(os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_CLOUD_PROJECT"))
    connected, message = (
        test_connection() if has_creds
        else (False, "No credentials — set GOOGLE_API_KEY or GOOGLE_CLOUD_PROJECT")
    )
    return {
        "status": "ok",
        "sdvVersion": SDV_VERSION,
        "sdvAvailable": SDV_AVAILABLE,
        "geminiConnected": connected,
        "geminiMessage": message,
        "authMode": "adc" if os.getenv("GOOGLE_CLOUD_PROJECT") else "apikey",
    }


@app.post("/generate")
def generate(payload: GenerateRequest):
    _validate_schema(payload.schema)
    result = run_pipeline(payload.schema, payload.config)
    return serialize_result(result)


@app.post("/suggest-columns", response_model=SuggestColumnsResponse)
def suggest_columns(payload: SuggestColumnsRequest):
    try:
        result = suggest_schema_columns(payload.description, payload.alreadySelected)
        return SuggestColumnsResponse.model_validate(result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Column suggestion failed: {exc}") from exc


@app.post("/prompt")
def prompt(payload: PromptRequest):
    try:
        result = interpret_fairness_prompt(payload.instruction, payload.currentConfig)
        explanation = result.pop("explanation", "Applied the requested fairness constraint changes.")
        return {"configDelta": result, "explanation": explanation}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Prompt interpretation failed: {exc}") from exc


@app.post("/model/evaluate")
def model_evaluate(payload: ModelEvalRequest):
    try:
        return evaluate_model_fairness(
            before_df_records=payload.beforeDataset,
            after_df_records=payload.dataset,
            schema=payload.schema,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Model evaluation failed: {exc}") from exc


@app.get("/sessions")
def get_sessions(limit: int = 10):
    try:
        return {"sessions": list_sessions(limit=limit)}
    except RuntimeError:
        return {"sessions": [], "note": "Firestore not configured (GOOGLE_CLOUD_PROJECT unset)"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/sessions/{session_id}")
def get_session(session_id: str):
    try:
        session = load_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return session
    except HTTPException:
        raise
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Firestore not configured")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/export/huggingface")
def export_huggingface(payload: ExportHuggingFaceRequest):
    try:
        url = export_to_huggingface(payload.dataset, payload.repoName, payload.hfToken)
        return {"url": url}
    except ExportDependencyError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Export failed: {exc}") from exc


@app.post("/export/googlesheets")
def export_googlesheets(payload: ExportGoogleSheetsRequest):
    try:
        url = export_to_googlesheets(payload.dataset, payload.accessToken)
        return {"url": url}
    except ExportDependencyError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        # Note: We rely on the adapter to throw RuntimeError if gspread API errors occur
        if "API Error" in str(exc):
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        raise HTTPException(status_code=500, detail=f"Google Sheets export failed: {exc}") from exc


@app.get("/")
def root():
    return {"name": "de.bias API", "version": "0.3.0", "status": "running", "ai": "Gemini 1.5 Flash"}
