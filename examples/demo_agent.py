"""Emits a handful of sample events, used by the README quickstart.

Run: python examples/demo_agent.py
"""

from flight_recorder.ingestion import record
from flight_recorder.models import EventKind, RedactionRule
from flight_recorder.redaction import FieldPathRedactor
from flight_recorder.storage import Store


def main() -> None:
    store = Store("flight_recorder.db")
    redactor = FieldPathRedactor([RedactionRule(field_path="user.email", strategy="hash")])

    record(
        store,
        agent_id="demo-agent",
        name="user_message_received",
        kind=EventKind.USER_INPUT,
        attributes={"user": {"email": "alice@example.com"}, "text": "What is my account balance?"},
        redactor=redactor,
    )
    record(
        store,
        agent_id="demo-agent",
        name="lookup_balance",
        kind=EventKind.TOOL_CALL,
        attributes={"tool": "billing_api", "args": {"account_id": "acc_123"}},
    )
    record(
        store,
        agent_id="demo-agent",
        name="respond_to_user",
        kind=EventKind.AGENT_OUTPUT,
        attributes={"text": "Your balance is $42.00."},
    )

    is_valid, break_index = store.chain.verify()
    print(f"Recorded 3 events. Chain valid: {is_valid} (break at {break_index})")
    store.close()


if __name__ == "__main__":
    main()
