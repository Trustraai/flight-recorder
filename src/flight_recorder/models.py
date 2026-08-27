"""Core data model for the Flight Recorder.

An Event is the atomic unit captured: one tool call, one model call, one
decision point, one error. Nothing here judges the event; it only describes
what it was and when it happened.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


def now() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class EventKind(str, Enum):
    MODEL_CALL = "model_call"
    TOOL_CALL = "tool_call"
    DECISION = "decision"
    ERROR = "error"
    USER_INPUT = "user_input"
    AGENT_OUTPUT = "agent_output"
    CUSTOM = "custom"


class Event(BaseModel):
    """A single captured event from a live agent."""

    id: str = Field(default_factory=lambda: new_id("evt"))
    agent_id: str
    session_id: Optional[str] = None
    kind: EventKind = EventKind.CUSTOM
    name: str
    attributes: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime = Field(default_factory=now)
    recorded_at: datetime = Field(default_factory=now)

    # Set by the redaction pipeline before the event is hashed and stored.
    redacted_fields: list[str] = Field(default_factory=list)

    # Populated once the event is written to the provenance chain.
    record_hash: Optional[str] = None
    previous_hash: Optional[str] = None


class RedactionRule(BaseModel):
    """Describes one field to scrub before an event is persisted."""

    field_path: str  # dotted path into attributes, e.g. "user.email"
    strategy: str = "hash"  # "hash", "remove", or "mask"


class ExportManifest(BaseModel):
    """Accompanies an exported bundle of events.

    Anyone receiving the bundle can recompute the chain over the included
    events and confirm the resulting head hash matches this manifest,
    without needing write access to (or trust in) the live recorder.
    """

    exported_at: datetime = Field(default_factory=now)
    agent_id: Optional[str] = None
    since: Optional[datetime] = None
    until: Optional[datetime] = None
    event_count: int
    first_previous_hash: str
    head_hash: str
