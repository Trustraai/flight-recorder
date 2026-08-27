import tempfile
from pathlib import Path

from flight_recorder.export import export_events, verify_export
from flight_recorder.ingestion import record
from flight_recorder.storage import Store


def test_export_and_verify_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = str(Path(tmp) / "test.db")
        store = Store(db_path)
        for i in range(5):
            record(store, agent_id="agent-1", name=f"event_{i}")

        out_path = str(Path(tmp) / "bundle.jsonl")
        manifest = export_events(store, out_path, agent_id="agent-1")

        assert manifest.event_count == 5
        assert Path(out_path).exists()
        assert Path(out_path + ".manifest.json").exists()

        is_valid, break_index = verify_export(out_path)
        assert is_valid is True
        assert break_index is None

        store.close()


def test_export_detects_tampered_bundle():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = str(Path(tmp) / "test.db")
        store = Store(db_path)
        for i in range(3):
            record(store, agent_id="agent-1", name=f"event_{i}")

        out_path = str(Path(tmp) / "bundle.jsonl")
        export_events(store, out_path, agent_id="agent-1")
        store.close()

        # Tamper with the exported bundle after the fact.
        lines = Path(out_path).read_text(encoding="utf-8").splitlines()
        import json

        tampered = json.loads(lines[1])
        tampered["name"] = "tampered_name"
        lines[1] = json.dumps(tampered)
        Path(out_path).write_text("\n".join(lines) + "\n", encoding="utf-8")

        is_valid, break_index = verify_export(out_path)
        assert is_valid is False
