"""SQLite-backed storage for recorded events.

A single-file database is enough for M0 and for most self-hosted use. A
higher-throughput backend (Postgres, or a Kafka-fed sink for very high
event volumes) is a natural follow-up contribution; see
docs/ARCHITECTURE.md.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional

from .models import Event
from .provenance import ChainEntry, ProvenanceChain

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    payload TEXT NOT NULL,
    record_hash TEXT NOT NULL,
    previous_hash TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    recorded_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_events_agent_id ON events (agent_id);
CREATE INDEX IF NOT EXISTS idx_events_recorded_at ON events (recorded_at);
"""


class Store:
    """Owns one SQLite connection and one event provenance chain."""

    def __init__(self, db_path: str = "flight_recorder.db"):
        self.db_path = db_path
        parent = Path(db_path).parent
        if str(parent) not in (".", ""):
            parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.executescript(SCHEMA)
        self._conn.commit()
        self.chain = ProvenanceChain(self._load_chain())

    @contextmanager
    def _cursor(self) -> Iterator[sqlite3.Cursor]:
        cur = self._conn.cursor()
        try:
            yield cur
            self._conn.commit()
        finally:
            cur.close()

    def _load_chain(self) -> list[ChainEntry]:
        entries: list[ChainEntry] = []
        cur = self._conn.execute(
            "SELECT payload, previous_hash, record_hash FROM events ORDER BY recorded_at ASC"
        )
        for payload_json, previous_hash, record_hash in cur.fetchall():
            payload = json.loads(payload_json)
            # Chain metadata is written back onto the object after hashing;
            # reset it to null (its value at hash time) so recomputing the
            # hash matches what was originally hashed.
            payload["record_hash"] = None
            payload["previous_hash"] = None
            entries.append(
                ChainEntry(payload=payload, previous_hash=previous_hash, record_hash=record_hash)
            )
        return entries

    def save_event(self, event: Event) -> Event:
        payload = event.model_dump(mode="json")
        entry = self.chain.append(payload)
        event.record_hash = entry.record_hash
        event.previous_hash = entry.previous_hash
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO events (id, agent_id, payload, record_hash, previous_hash, occurred_at, recorded_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    event.id,
                    event.agent_id,
                    event.model_dump_json(),
                    entry.record_hash,
                    entry.previous_hash,
                    event.occurred_at.isoformat(),
                    event.recorded_at.isoformat(),
                ),
            )
        return event

    def get_event(self, event_id: str) -> Optional[Event]:
        cur = self._conn.execute("SELECT payload FROM events WHERE id = ?", (event_id,))
        row = cur.fetchone()
        return Event.model_validate_json(row[0]) if row else None

    def query_events(
        self,
        agent_id: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[Event]:
        clauses = []
        params: list[str] = []
        if agent_id:
            clauses.append("agent_id = ?")
            params.append(agent_id)
        if since:
            clauses.append("recorded_at >= ?")
            params.append(since.isoformat())
        if until:
            clauses.append("recorded_at <= ?")
            params.append(until.isoformat())
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        query = f"SELECT payload FROM events {where} ORDER BY recorded_at ASC LIMIT ?"
        params.append(str(limit))
        cur = self._conn.execute(query, params)
        return [Event.model_validate_json(r[0]) for r in cur.fetchall()]

    def close(self) -> None:
        self._conn.close()
