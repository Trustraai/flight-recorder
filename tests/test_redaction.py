from flight_recorder.models import RedactionRule
from flight_recorder.redaction import FieldPathRedactor, PatternRedactor


def test_field_path_hash_redaction():
    redactor = FieldPathRedactor([RedactionRule(field_path="user.email", strategy="hash")])
    attrs = {"user": {"email": "alice@example.com", "name": "Alice"}}
    redacted, touched = redactor.apply(attrs)
    assert "alice@example.com" not in redacted["user"]["email"]
    assert redacted["user"]["email"].startswith("[REDACTED:")
    assert redacted["user"]["name"] == "Alice"
    assert touched == ["user.email"]


def test_field_path_hash_is_deterministic():
    redactor = FieldPathRedactor([RedactionRule(field_path="user.email", strategy="hash")])
    a, _ = redactor.apply({"user": {"email": "alice@example.com"}})
    b, _ = redactor.apply({"user": {"email": "alice@example.com"}})
    assert a["user"]["email"] == b["user"]["email"]


def test_field_path_remove():
    redactor = FieldPathRedactor([RedactionRule(field_path="secret", strategy="remove")])
    redacted, touched = redactor.apply({"secret": "sk-12345", "other": "x"})
    assert "secret" not in redacted
    assert touched == ["secret"]


def test_pattern_redactor_email():
    redactor = PatternRedactor()
    redacted, touched = redactor.apply({"text": "reach me at bob@example.com please"})
    assert "bob@example.com" not in redacted["text"]
    assert "[REDACTED:email]" in redacted["text"]
    assert touched == ["text"]


def test_pattern_redactor_nested_dict():
    redactor = PatternRedactor()
    redacted, touched = redactor.apply({"user": {"note": "call 555-123-4567 anytime"}})
    assert "555-123-4567" not in redacted["user"]["note"]
    assert touched == ["user.note"]
