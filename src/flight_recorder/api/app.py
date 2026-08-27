"""Minimal FastAPI service for ingestion, querying, verification, and export.

Run with: uvicorn flight_recorder.api.app:app --reload
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Optional

from fastapi import FastAPI, HTTPException

from ..export import export_events
from ..models import Event, EventKind, ExportManifest
from ..storage import Store

DB_PATH = os.environ.get("FLIGHT_RECORDER_DB_PATH", "flight_recorder.db")

app = FastAPI(title="Trustra Flight Recorder", version="0.1.0")
store = Store(DB_PATH)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


class RecordRequest(Event):
    pass


@app.post("/events", response_model=Event)
def post_event(payload: dict[str, Any]) -> Event:
    event = Event(
        agent_id=payload["agent_id"],
        session_id=payload.get("session_id"),
        kind=payload.get("kind", EventKind.CUSTOM),
        name=payload.get("name", "unnamed_event"),
        attributes=payload.get("attributes", {}),
    )
    return store.save_event(event)


@app.get("/events/{event_id}", response_model=Event)
def get_event(event_id: str) -> Event:
    event = store.get_event(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="event not found")
    return event


@app.get("/events", response_model=list[Event])
def list_events(
    agent_id: Optional[str] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    limit: int = 100,
) -> list[Event]:
    return store.query_events(agent_id=agent_id, since=since, until=until, limit=limit)


@app.get("/verify")
def verify_chain() -> dict[str, Any]:
    is_valid, break_index = store.chain.verify()
    return {"valid": is_valid, "break_index": break_index, "length": len(store.chain)}


@app.post("/export", response_model=ExportManifest)
def export(
    out_path: str,
    agent_id: Optional[str] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
) -> ExportManifest:
    return export_events(store, out_path, agent_id=agent_id, since=since, until=until)
