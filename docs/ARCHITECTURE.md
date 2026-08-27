# Architecture

## Scope of this repository

This repository captures a tamper-evident record of what a live AI agent did. It is intentionally narrow: it does not decide whether that behavior was correct, safe, or compliant, and it does not issue attestations or claim independence. Those require a named, accountable human and are out of scope for automated software by design.

## Components

**Event model (`models.py`).** An Event captures one thing that happened: a tool call, a model call, a decision point, an error, user input, or agent output. `EventKind` categorizes it. `RedactionRule` and `ExportManifest` support the redaction and export features below.

**Provenance chain (`provenance.py`).** The same hash-chain approach as Trustra's Agent Eval Harness: each event's hash depends on its content and the previous event's hash, so recomputing the chain from the start detects any retroactive edit. Deliberately simple and single-writer, not a distributed ledger; the goal is tamper evidence within one deployment.

**Redaction (`redaction.py`).** Runs before hashing, not after. This matters: redacting a field after an event has already been hashed and chained would either break the chain (if you actually change the stored bytes) or leave sensitive data sitting in a "tamper-evident" record forever (if you don't). Redacting at capture time avoids both problems. Two redactors ship in this repository: `FieldPathRedactor` for known-sensitive fields (hash, mask, or remove by dotted path) and `PatternRedactor` for best-effort scanning of free text (email, phone). They compose via `ChainedRedactor`.

**Storage (`storage.py`).** SQLite by default, one file. The chain is reconstructed from the database on startup by replaying stored entries, so the database is the source of truth and the in-memory chain is a derived, verifiable view of it.

**Ingestion (`ingestion.py`).** Two entry points: `record()` for direct instrumentation inside an agent's own code (the primary integration path), and `record_span()` for agents already emitting OpenTelemetry-shaped spans.

**Export (`export.py`).** Produces a portable bundle: one JSON event per line, plus a manifest recording the exported segment's boundary hashes. `verify_export()` recomputes the chain over the bundle file alone and checks it against the manifest, so a recipient with no access to (or trust in) the live recorder, an auditor, an incident responder, opposing counsel, can independently confirm the exported events were not reordered or edited after being written. This does not prove completeness (that nothing outside the export window was withheld); it proves internal consistency of what was handed over.

**API (`api/app.py`).** A small FastAPI service: post and list events, fetch a single event, verify the live chain, trigger an export.

**CLI (`cli.py`).** `flight-recorder init | query | verify | export | verify-export`.

## Design decisions worth flagging

- **Redact before hash, not after.** See above. Any contribution touching redaction must preserve this ordering.
- **SQLite by default.** Chosen for zero-dependency self-hosting at M0 scale. High-throughput production deployments will want a different backend; see the roadmap.
- **The manifest is proof of consistency, not completeness.** Anyone relying on an exported bundle for an investigation should understand this distinction. Consider it a design constraint for any future work on export formats: do not let documentation or tooling imply a stronger guarantee than the hash chain actually provides.

## What is intentionally not in this repository

- Attestation, certification, or any statement that recorded behavior was acceptable. That is a separate, accountable, human layer.
- A claim of independence. Anyone can self-host this on their own infrastructure. Independence is a property of who operates it, not of the code.
- Interpretation or scoring of events. This project answers "what happened," not "was that okay." Pair it with an evaluation layer (for example, Trustra's Agent Eval Harness) for the latter.

## Roadmap (open to contribution)

- A higher-throughput storage backend (Postgres, or a queue-fed sink) for production event volumes beyond what a single SQLite file comfortably handles.
- Batched/streaming ingestion for high-frequency agents.
- A minimal web dashboard for browsing and searching events.
- Additional built-in redactors (structured PII detectors beyond email/phone, secret-pattern detectors for common API key formats).
- Signed, periodic checkpoints of the chain head (for example, published to an external timestamping service) as an optional integrity anchor beyond the local database.
