"""Pluggable redaction, applied to an event's attributes before it is
hashed and persisted.

Because this project captures continuous production behavior, what it
records may include personal data or secrets by accident (a user's message,
an API key echoed in a tool's output, and so on). Redaction runs before
hashing so that scrubbed events still produce a stable, verifiable chain;
redacting an event's rendering later would break the chain, which is exactly
the tamper it exists to detect. Redact at capture time instead.
"""

from __future__ import annotations

import hashlib
import re
from abc import ABC, abstractmethod
from typing import Any

from .models import RedactionRule


class Redactor(ABC):
    """Base class for all redactors."""

    @abstractmethod
    def apply(self, attributes: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
        """Return (redacted_attributes, list_of_field_paths_redacted)."""
        raise NotImplementedError


def _get(obj: dict[str, Any], path: list[str]) -> Any:
    cur = obj
    for part in path:
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _set(obj: dict[str, Any], path: list[str], value: Any) -> None:
    cur = obj
    for part in path[:-1]:
        if part not in cur or not isinstance(cur[part], dict):
            return
        cur = cur[part]
    if path[-1] in cur:
        cur[path[-1]] = value


def _delete(obj: dict[str, Any], path: list[str]) -> None:
    cur = obj
    for part in path[:-1]:
        if part not in cur or not isinstance(cur[part], dict):
            return
        cur = cur[part]
    cur.pop(path[-1], None)


class FieldPathRedactor(Redactor):
    """Redacts a fixed list of dotted field paths.

    strategy "hash": replace the value with a salted sha256 digest, so the
    same underlying value always redacts to the same token (useful for
    correlation without exposing the original).
    strategy "remove": delete the field entirely.
    strategy "mask": replace with a fixed placeholder string.
    """

    def __init__(self, rules: list[RedactionRule], salt: str = "trustra-flight-recorder"):
        self.rules = rules
        self.salt = salt

    def apply(self, attributes: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
        redacted = dict(attributes)
        touched: list[str] = []
        for rule in self.rules:
            path = rule.field_path.split(".")
            value = _get(redacted, path)
            if value is None:
                continue
            if rule.strategy == "remove":
                _delete(redacted, path)
            elif rule.strategy == "mask":
                _set(redacted, path, "[REDACTED]")
            else:  # "hash"
                digest = hashlib.sha256(f"{self.salt}:{value}".encode("utf-8")).hexdigest()[:16]
                _set(redacted, path, f"[REDACTED:{digest}]")
            touched.append(rule.field_path)
        return redacted, touched


DEFAULT_PII_PATTERNS = {
    "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "phone": re.compile(r"\+?\d[\d\s\-()]{7,}\d"),
}


class PatternRedactor(Redactor):
    """Scans string values (recursively, one level of nesting) for common
    PII patterns (email, phone) and masks matches in place.

    This is a best-effort scanner, not a guarantee: it is deliberately
    simple, and should be paired with FieldPathRedactor for any field known
    in advance to hold sensitive data.
    """

    def __init__(self, patterns: dict[str, re.Pattern] | None = None):
        self.patterns = patterns or DEFAULT_PII_PATTERNS

    def _scrub_string(self, value: str) -> tuple[str, bool]:
        touched = False
        for name, pattern in self.patterns.items():
            if pattern.search(value):
                value = pattern.sub(f"[REDACTED:{name}]", value)
                touched = True
        return value, touched

    def apply(self, attributes: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
        redacted: dict[str, Any] = {}
        touched: list[str] = []
        for key, value in attributes.items():
            if isinstance(value, str):
                new_value, was_touched = self._scrub_string(value)
                redacted[key] = new_value
                if was_touched:
                    touched.append(key)
            elif isinstance(value, dict):
                new_value: dict[str, Any] = {}
                for sub_key, sub_value in value.items():
                    if isinstance(sub_value, str):
                        scrubbed, was_touched = self._scrub_string(sub_value)
                        new_value[sub_key] = scrubbed
                        if was_touched:
                            touched.append(f"{key}.{sub_key}")
                    else:
                        new_value[sub_key] = sub_value
                redacted[key] = new_value
            else:
                redacted[key] = value
        return redacted, touched


class ChainedRedactor(Redactor):
    """Applies multiple redactors in sequence."""

    def __init__(self, redactors: list[Redactor]):
        self.redactors = redactors

    def apply(self, attributes: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
        touched: list[str] = []
        current = attributes
        for redactor in self.redactors:
            current, newly_touched = redactor.apply(current)
            touched.extend(newly_touched)
        return current, touched
