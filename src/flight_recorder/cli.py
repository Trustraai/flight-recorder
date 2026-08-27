"""Command-line interface for the Flight Recorder."""

from __future__ import annotations

import sys
from datetime import datetime
from typing import Optional

import typer

from .export import export_events, verify_export
from .storage import Store

app = typer.Typer(help="Trustra Flight Recorder CLI")


@app.command()
def init(db: str = typer.Option("flight_recorder.db", help="Path to the SQLite database file")):
    """Initialize a fresh local database."""
    store = Store(db)
    typer.echo(f"Initialized database at {db}")
    store.close()


@app.command()
def query(
    agent_id: Optional[str] = typer.Option(None),
    limit: int = typer.Option(20),
    db: str = typer.Option("flight_recorder.db"),
):
    """Print the most recent recorded events."""
    store = Store(db)
    events = store.query_events(agent_id=agent_id, limit=limit)
    for event in events:
        typer.echo(f"{event.recorded_at.isoformat()}  {event.agent_id}  {event.kind.value}  {event.name}")
    typer.echo(f"\n{len(events)} event(s)")
    store.close()


@app.command()
def verify(db: str = typer.Option("flight_recorder.db")):
    """Verify the integrity of the live event chain."""
    store = Store(db)
    is_valid, break_index = store.chain.verify()
    typer.echo(f"Chain valid: {is_valid} (break at {break_index}), {len(store.chain)} event(s)")
    store.close()
    if not is_valid:
        sys.exit(1)


@app.command()
def export(
    out: str = typer.Option(..., help="Output NDJSON file path"),
    agent_id: Optional[str] = typer.Option(None),
    since: Optional[str] = typer.Option(None, help="ISO 8601 timestamp"),
    until: Optional[str] = typer.Option(None, help="ISO 8601 timestamp"),
    db: str = typer.Option("flight_recorder.db"),
):
    """Export a slice of the record as a portable, verifiable bundle."""
    store = Store(db)
    since_dt = datetime.fromisoformat(since) if since else None
    until_dt = datetime.fromisoformat(until) if until else None
    manifest = export_events(store, out, agent_id=agent_id, since=since_dt, until=until_dt)
    typer.echo(f"Exported {manifest.event_count} event(s) to {out}")
    typer.echo(f"Manifest: {out}.manifest.json")
    typer.echo(f"Head hash: {manifest.head_hash}")
    store.close()


@app.command("verify-export")
def verify_export_cmd(
    bundle: str = typer.Argument(..., help="Path to an exported NDJSON bundle"),
):
    """Verify a previously exported bundle, independently of the live database."""
    is_valid, break_index = verify_export(bundle)
    typer.echo(f"Bundle valid: {is_valid} (break at {break_index})")
    if not is_valid:
        sys.exit(1)


if __name__ == "__main__":
    app()
