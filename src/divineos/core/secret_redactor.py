"""Secret redactor — strip API keys and credential-shaped values from
payloads before they reach the ledger.

Root structural fix for the 2026-06-26 key-leak class. An Anthropic
API key was committed into ``src/data/event_ledger.db`` because a
tool-call payload containing the key was logged into the event ledger
raw, then the DB itself was checked into git for a Perplexity audit.

Aletheia 2026-06-30: "redact-secrets-before-they're-logged is the real
structural win — it means a secret in a tool-payload never reaches the
ledger in the first place, so this whole class can't recur."

That layer is THIS module. History-scrubbing removes one key; redacting
at-write-time removes the class. The pre-commit ``.db`` guard is the
backstop in case the data layer ever leaks back into git regardless.

Design principles:

* **Fail-loud, not fail-quiet.** When a redaction fires, we emit a
  WARNING log line so the operator sees that a secret was attempted.
  The replacement marker preserves the dict shape but makes the
  redaction visible in any downstream consumer.

* **Pattern coverage first, false-positives second.** A redactor that
  misses a real key is worse than one that occasionally redacts a
  non-secret. Patterns favor recall over precision. The redaction
  marker names the matched pattern so post-hoc auditing can sort out
  any false positives.

* **No mutation of input.** Returns a redacted copy. Caller is responsible
  for using the returned value instead of the original.

* **Bounded recursion.** Walks nested dicts and lists up to a safe depth
  cap so pathological structures (cycles, deeply nested user input)
  cannot exhaust the stack.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Maximum recursion depth when walking nested payloads. Beyond this depth,
# string leaves are NOT scanned (the rest of the payload is returned as-is).
# 16 is well past any realistic payload shape we emit.
_MAX_DEPTH = 16

# Maximum string length to scan. Strings longer than this are checked for
# secret prefixes at the start only — full regex over very large strings
# is expensive and rarely productive.
_MAX_SCAN_LEN = 100_000

# Replacement marker. The matched pattern name is appended so audits can
# distinguish real-secret redactions from over-eager false positives.
_REDACT_PREFIX = "[REDACTED:"
_REDACT_SUFFIX = "]"


def _make_marker(pattern_name: str) -> str:
    return f"{_REDACT_PREFIX}{pattern_name}{_REDACT_SUFFIX}"


# Secret-shape patterns. Each entry is (name, compiled_regex). The name
# appears in the redaction marker and the warning log.
#
# Patterns prioritize known prefix shapes that are distinctive enough that
# matching them strongly implies a real credential. Generic "long base64
# string" patterns are deliberately omitted because they false-positive
# on legitimate content (hashes, base64 images, JSON Web Tokens used for
# non-secret IDs, etc).
_SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    # Anthropic API keys — the exact pattern from the 2026-06-26 leak.
    ("anthropic-api-key", re.compile(r"sk-ant-[a-zA-Z0-9\-_]{20,}")),
    # OpenAI API keys (sk-... and sk-proj-...).
    ("openai-api-key", re.compile(r"sk-(?:proj-)?[a-zA-Z0-9\-_]{20,}")),
    # AWS access keys.
    ("aws-access-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    # Google API keys.
    ("google-api-key", re.compile(r"\bAIza[0-9A-Za-z\-_]{35}\b")),
    # GitHub personal access tokens (classic + fine-grained + app).
    ("github-token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,}\b")),
    ("github-pat-fg", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{82}\b")),
    # GitLab personal access tokens.
    ("gitlab-pat", re.compile(r"\bglpat-[A-Za-z0-9\-_]{20,}\b")),
    # Slack tokens.
    ("slack-token", re.compile(r"\bxox[abprs]-[A-Za-z0-9\-]{10,}\b")),
    # Generic Bearer-prefix tokens in HTTP headers. Conservative match —
    # require at least 24 chars of token body to avoid false-positives on
    # toy/test strings.
    ("bearer-token", re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]{24,}={0,2}")),
)


def _scan_string(value: str) -> tuple[str, list[str]]:
    """Return (redacted_value, names_of_patterns_that_fired).

    Patterns are applied sequentially. Each match is replaced with the
    pattern's marker. A single string can fire multiple patterns.
    """
    if not value:
        return value, []
    # Skip oversized strings — only check their leading window for the
    # common case of "the key is the start of a long log line".
    if len(value) > _MAX_SCAN_LEN:
        head = value[:_MAX_SCAN_LEN]
        redacted_head, fired = _scan_string(head)
        if not fired:
            return value, []
        return redacted_head + value[_MAX_SCAN_LEN:], fired

    fired: list[str] = []
    out = value
    for name, pattern in _SECRET_PATTERNS:
        if pattern.search(out):
            out = pattern.sub(_make_marker(name), out)
            fired.append(name)
    return out, fired


def _walk(value: Any, depth: int, fired_log: list[str]) -> Any:
    """Recursively walk a payload value, redacting string leaves.

    ``fired_log`` accumulates the names of patterns that fired anywhere
    in the structure so the caller can emit a single summary warning.
    """
    if depth > _MAX_DEPTH:
        return value
    if isinstance(value, str):
        out, fired = _scan_string(value)
        fired_log.extend(fired)
        return out
    if isinstance(value, dict):
        return {k: _walk(v, depth + 1, fired_log) for k, v in value.items()}
    if isinstance(value, list):
        return [_walk(item, depth + 1, fired_log) for item in value]
    if isinstance(value, tuple):
        return tuple(_walk(item, depth + 1, fired_log) for item in value)
    # int, float, bool, None, and other non-string scalars pass through.
    return value


def redact_payload(payload: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Return ``(redacted_payload_copy, fired_pattern_names)``.

    Walks the payload structure and replaces any string matching a known
    secret pattern with a redaction marker. Returns a new dict; the input
    is not mutated.

    The returned ``fired_pattern_names`` list is the deduplicated names
    of patterns that matched anywhere in the structure. An empty list
    means no redaction was needed.
    """
    if not isinstance(payload, dict):
        # Defensive — log_event signature requires dict, but defend the
        # contract instead of trusting it.
        return payload, []
    fired_log: list[str] = []
    redacted = _walk(payload, depth=0, fired_log=fired_log)
    # Deduplicate while preserving insertion order.
    seen: set[str] = set()
    unique_fired = [n for n in fired_log if not (n in seen or seen.add(n))]
    return redacted, unique_fired


def redact_and_warn(payload: dict[str, Any], context: str = "") -> dict[str, Any]:
    """Convenience wrapper that calls ``redact_payload`` and emits a
    WARNING log line when redaction fired.

    ``context`` is included in the warning for debugging — typically the
    event_type the payload belongs to. Returns the redacted payload.
    """
    redacted, fired = redact_payload(payload)
    if fired:
        logger.warning(
            "SECRET REDACTED before ledger write%s — patterns matched: %s. "
            "Source upstream should be reviewed and the credential rotated "
            "if the redaction was a real exposure.",
            f" ({context})" if context else "",
            ", ".join(fired),
        )
    return redacted


__all__ = ["redact_and_warn", "redact_payload"]
