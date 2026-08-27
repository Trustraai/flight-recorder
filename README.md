# Trustra Flight Recorder

A continuous, tamper-evident black-box recorder for AI agents: capture every decision, tool call, and model interaction a live agent makes, append it to a hash-chained log the moment it happens, and be able to answer, after the fact, exactly what the agent did and when.

The analogy is deliberate. An aircraft flight recorder does not decide whether a flight went well. It just makes sure that, whatever happened, there is an unaltered record to examine afterward. This project does the same thing for AI agents.

This repository is a below-the-trust-line rails component of Trustra's broader independent AI verification product. It captures and preserves evidence. It does not interpret that evidence, does not certify anything, and does not claim independence, those require a named, accountable human and are out of scope here by design. See `docs/ARCHITECTURE.md`.

## What it does

- Ingests events from a live agent (tool calls, model calls, decisions, errors) via a simple `record()` call or an OpenTelemetry-style HTTP endpoint.
- Appends every event to a hash chain: each event's hash depends on its own content and the hash of the event before it, so retroactively editing or deleting an event is detectable.
- Supports pluggable redaction, so sensitive fields (PII, secrets, free-text user input) can be scrubbed or hashed at capture time, before anything touches disk.
- Persists to SQLite by default, one file, no external services required to get started.
- Exports a time-boxed slice of the record as a portable, independently verifiable bundle (NDJSON plus a manifest with the chain's head hash), for handing to an auditor or incident responder without giving them write access to the live system.
- Ships a CLI (`flight-recorder`) and a small FastAPI service for ingestion, querying, verification, and export.

## What it deliberately does not do

- It does not decide whether an agent's behavior was correct, safe, or compliant. It records what happened; judgment is a separate, human, accountable layer.
- It does not issue attestations or certifications.
- It does not claim to be independent of the system it is recording. Anyone can self-host this on their own infrastructure; independence is a property of who operates it, not of the code.

## Quickstart

```bash
pip install -e .
flight-recorder init
python examples/demo_agent.py       # emits a handful of sample events
flight-recorder query --limit 10
flight-recorder verify
flight-recorder export --since 2026-01-01 --out incident_bundle.jsonl
```

## Project layout

```
src/flight_recorder/
  models.py       Event, RedactionRule, ExportManifest
  provenance.py    Hash-chain implementation for tamper-evident records
  storage.py       SQLite-backed event store
  redaction.py     Pluggable redaction interface plus a regex-based default
  ingestion.py     record() API and OpenTelemetry-style span ingestion
  export.py        Portable, independently verifiable export bundles
  api/             FastAPI service
  cli.py           Command-line interface
tests/             Unit tests
docs/              Architecture notes
```

## Status

Early stage (M0). Core event model, hash-chain provenance, SQLite storage, regex-based redaction, ingestion, export, API, and CLI are implemented and tested. Not yet implemented: streaming ingestion at scale, a Postgres/Kafka-backed storage option, and a web dashboard. See `docs/ARCHITECTURE.md` for the roadmap.

## Contributing

Contributions are welcome, see `CONTRIBUTING.md`. Licensed under AGPL-3.0-or-later specifically so improvements made by anyone running this as a service flow back to the community.

## License

GNU Affero General Public License v3.0 or later. See `LICENSE`.
