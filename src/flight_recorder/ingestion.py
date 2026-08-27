"""Ingestion entry points: a direct record() call, and an OpenTelemetry-style
span adapter for agents already instrumented with OTel.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from .models import Event, EventKind, now
from .redaction import Redactor
from .storage import Store


def record(
    store: Store,
    agent_id: str,
    name: str,
    kind: EventKind = EventKind.CUSTOM,
    attributes: Optional[dict[str, Any]] = None,
    session_id: Optional[str] = None,
    redactor: Optional[Redactor] = None,
    occurred_at: Optional[datetime] = None,
) -> Event:
    """Record a single event. This is the primary integration point: call
    this directly from inside an agent's tool-call or decision loop."""
    attrs = attributes or {}
    redacted_fields: list[str] = []
    if redactor is not None:
        attrs, redacted_fields = redactor.apply(attrs)

    event = Event(
        agent_id=agent_id,
        session_id=session_id,
        kind=kind,
        name=name,
        attributes=attrs,
        occurred_at=occurred_at or now(),
        redacted_fields=redacted_fields,
    )
    return store.save_event(event)


def _parse_time(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1e9, tz=timezone.utc)
    return datetime.fromisoformat(str(value))


def record_span(
    store: Store,
    agent_id: str,
    span: dict[str, Any],
    redactor: Optional[Redactor] = None,
) -> Event:
    """Adapt an OpenTelemetry-shaped span dict into a recorded event."""
    return record(
        store,
        agent_id=agent_id,
        name=span.get("name", "unnamed_span"),
        kind=EventKind.CUSTOM,
        attributes=span.get("attributes", {}),
        session_id=span.get("trace_id"),
        redactor=redactor,
        occurred_at=_parse_time(span["start_time"]) if span.get("start_time") else None,
    )
