"""Firestore session persistence helpers.

Stores experiment sessions keyed by a client-generated UUID.
Each document shape:
{
    "createdAt": Timestamp,
    "schema": [...],
    "config": {...},
    "metrics": {...},
    "beforeMetrics": {...},
    "geminiNarrative": str | None,
    "generationTimeSeconds": float,
}

Auth: uses Application Default Credentials (ADC) automatically on Cloud Run.
Local dev: run `gcloud auth application-default login` first.

Usage
-----
    from src.adapters.firestore_client import save_session, load_session, list_sessions

    session_id = save_session(result_payload, schema, config)
    session    = load_session(session_id)
    history    = list_sessions(limit=10)
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
_COLLECTION = "debias_sessions"

# Lazy singleton — only initialised if GOOGLE_CLOUD_PROJECT is set.
_db = None


def _get_db():
    global _db
    if _db is not None:
        return _db
    if not _PROJECT:
        raise RuntimeError("GOOGLE_CLOUD_PROJECT is not set — Firestore unavailable")
    from google.cloud import firestore  # type: ignore
    _db = firestore.Client(project=_PROJECT)  # ADC
    return _db


def save_session(
    result: dict[str, Any],
    schema: list[dict],
    config: dict[str, Any],
) -> str:
    """Persist a generation result and return the Firestore document ID."""
    db = _get_db()
    doc_ref = db.collection(_COLLECTION).document()
    doc_ref.set({
        "createdAt": datetime.now(timezone.utc),
        "schema": schema,
        "config": config,
        "metrics": result.get("metrics", {}),
        "beforeMetrics": result.get("beforeMetrics", {}),
        "geminiNarrative": result.get("geminiNarrative"),
        "generationTimeSeconds": result.get("generationTimeSeconds"),
        "datasetSize": len(result.get("dataset", [])),
    })
    return doc_ref.id


def load_session(session_id: str) -> dict[str, Any] | None:
    """Retrieve a session by Firestore document ID."""
    db = _get_db()
    doc = db.collection(_COLLECTION).document(session_id).get()
    return doc.to_dict() if doc.exists else None


def list_sessions(limit: int = 10) -> list[dict[str, Any]]:
    """Return the most recent N sessions (id + summary fields only)."""
    db = _get_db()
    docs = (
        db.collection(_COLLECTION)
        .order_by("createdAt", direction="DESCENDING")
        .limit(limit)
        .stream()
    )
    return [
        {
            "id": doc.id,
            "createdAt": doc.get("createdAt"),
            "datasetSize": doc.get("datasetSize"),
            "ofsScore": doc.get("metrics", {}).get("OFS"),
        }
        for doc in docs
    ]
