"""Hash-chain provenance for recorded events.

Each event embeds the hash of the event before it. Recomputing the chain in
order and comparing hashes surfaces any retroactive edit or deletion. This
module makes no claim beyond tamper evidence within the deployment that
holds the chain; it does not make the record independently verified, that
depends on who operates this software and what they do with its output.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Optional

GENESIS_HASH = "0" * 64


def canonical_json(payload: dict[str, Any]) -> str:
    """Deterministic JSON serialization used for hashing."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def compute_hash(payload: dict[str, Any], previous_hash: str) -> str:
    body = canonical_json(payload) + "|" + previous_hash
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


@dataclass
class ChainEntry:
    payload: dict[str, Any]
    previous_hash: str
    record_hash: str


class ProvenanceChain:
    """An in-memory, append-only hash chain."""

    def __init__(self, entries: Optional[list[ChainEntry]] = None):
        self._entries: list[ChainEntry] = list(entries) if entries else []

    @property
    def head_hash(self) -> str:
        if not self._entries:
            return GENESIS_HASH
        return self._entries[-1].record_hash

    def append(self, payload: dict[str, Any]) -> ChainEntry:
        previous_hash = self.head_hash
        record_hash = compute_hash(payload, previous_hash)
        entry = ChainEntry(payload=payload, previous_hash=previous_hash, record_hash=record_hash)
        self._entries.append(entry)
        return entry

    def verify(self) -> tuple[bool, Optional[int]]:
        """Recompute every hash in order. Returns (is_valid, break_index)."""
        expected_previous = GENESIS_HASH
        for i, entry in enumerate(self._entries):
            if entry.previous_hash != expected_previous:
                return False, i
            if compute_hash(entry.payload, entry.previous_hash) != entry.record_hash:
                return False, i
            expected_previous = entry.record_hash
        return True, None

    def __len__(self) -> int:
        return len(self._entries)

    def __iter__(self):
        return iter(self._entries)
