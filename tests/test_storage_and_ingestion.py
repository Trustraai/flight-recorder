import tempfile
from pathlib import Path

from flight_recorder.ingestion import record
from flight_recorder.models import EventKind
from flight_recorder.storage import Store


def test_record_and_retrieve_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = str(Path(tmp) / "test.db")
        store = Store(db_path)

        event = record(store, agent_id="agent-1", name="tool_call", kind=EventKind.TOOL_CALL)

        assert event.record_hash is not None
        fetched = store.get_event(event.id)
        assert fetched is not None
        assert fetched.record_hash == event.record_hash

        is_valid, break_index = store.chain.verify()
        assert is_valid is True
        assert break_index is None

        store.close()


def test_query_filters_by_agent_id():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = str(Path(tmp) / "test.db")
        store = Store(db_path)

        record(store, agent_id="agent-a", name="e1")
        record(store, agent_id="agent-b", name="e2")
        record(store, agent_id="agent-a", name="e3")

        results = store.query_events(agent_id="agent-a")
        assert len(results) == 2
        assert all(e.agent_id == "agent-a" for e in results)

        store.close()


def test_chain_persists_across_reopen():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = str(Path(tmp) / "test.db")
        store = Store(db_path)
        record(store, agent_id="agent-1", name="e1")
        record(store, agent_id="agent-1", name="e2")
        head = store.chain.head_hash
        store.close()

        reopened = Store(db_path)
        assert reopened.chain.head_hash == head
        is_valid, break_index = reopened.chain.verify()
        assert is_valid is True
        assert break_index is None
        reopened.close()
