"""Export a time-boxed slice of the record as a portable, independently
verifiable bundle: one event per line (NDJSON) plus a manifest.

The point of the manifest is that a recipient, an auditor, an incident
responder, someone who does not have write access to (or trust in) the
live recorder, can recompute the chain over the exported events and check
that the resulting head hash matches the manifest. That check does not
prove the events are complete or that nothing was withheld; it proves that
the events included have not been altered relative to each other, and
that no entry among them was reordered or edited after being written.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import Event, ExportManifest, now
from .provenance import GENESIS_HASH, ProvenanceChain
from .storage import Store


def export_events(
    store: Store,
    out_path: str,
    agent_id: Optional[str] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    limit: int = 100_000,
) -> ExportManifest:
    events = store.query_events(agent_id=agent_id, since=since, until=until, limit=limit)

    out_file = Path(out_path)
    with out_file.open("w", encoding="utf-8") as f:
        for event in events:
            f.write(event.model_dump_json() + "\n")

    if events:
        first_previous_hash = events[0].previous_hash or GENESIS_HASH
        head_hash = events[-1].record_hash or GENESIS_HASH
    else:
        first_previous_hash = GENESIS_HASH
        head_hash = GENESIS_HASH

    manifest = ExportManifest(
        exported_at=now(),
        agent_id=agent_id,
        since=since,
        until=until,
        event_count=len(events),
        first_previous_hash=first_previous_hash,
        head_hash=head_hash,
    )

    manifest_path = out_file.with_suffix(out_file.suffix + ".manifest.json")
    manifest_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")

    return manifest


def verify_export(bundle_path: str, manifest_path: Optional[str] = None) -> tuple[bool, Optional[int]]:
    """Verify an exported bundle independently of the live recorder.

    Recomputes the hash chain over the events in the bundle using only the
    file on disk, and checks it against the accompanying manifest's
    first_previous_hash and head_hash. This is the check a recipient with
    no access to the live system can run for themselves.
    """
    bundle = Path(bundle_path)
    manifest_file = Path(manifest_path) if manifest_path else bundle.with_suffix(bundle.suffix + ".manifest.json")
    manifest = ExportManifest.model_validate_json(manifest_file.read_text(encoding="utf-8"))

    events: list[Event] = []
    with bundle.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(Event.model_validate_json(line))

    if len(events) != manifest.event_count:
        return False, 0

    if not events:
        return manifest.head_hash == GENESIS_HASH, None

    if (events[0].previous_hash or GENESIS_HASH) != manifest.first_previous_hash:
        return False, 0

    chain = ProvenanceChain()
    # Seed the chain's starting point so recomputed hashes line up with the
    # original chain segment rather than restarting from genesis.
    chain._entries = []  # noqa: SLF001 - intentional, this module owns the invariant
    expected_previous = manifest.first_previous_hash
    for i, event in enumerate(events):
        payload = json.loads(event.model_dump_json())
        payload["record_hash"] = None
        payload["previous_hash"] = None
        from .provenance import compute_hash

        recomputed = compute_hash(payload, expected_previous)
        if event.previous_hash != expected_previous or event.record_hash != recomputed:
            return False, i
        expected_previous = event.record_hash

    return expected_previous == manifest.head_hash, None
