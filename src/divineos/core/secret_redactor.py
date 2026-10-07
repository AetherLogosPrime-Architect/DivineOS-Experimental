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

# THERE IS NO LENGTH CAP, and there used to be one (2026-10-07). Strings over
# 100,000 characters were scanned in their first 100,000 only, on the reasoning
# that full regex over large strings is expensive and rarely productive. Running
# that claim: a key placed just past the window, or 300,000 characters in, came
# out in the clear, in a ledger that is append-only. The cap was covering for two
# patterns that go quadratic on long runs (url credential on a run of letters:
# 4.7 s at 100,000 characters and 77 s at 400,000; PEM on a flood of BEGIN lines).
# Those two are linear now, so every position of every string is examined, and a
# cap anywhere would be the same hole one size larger. The promise is the one in
# the header, stated with its true limit: no key of a KNOWN shape survives. A shape
# not in the list below still would.

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
    # Stripe live secret keys (2026-07-02 Fable audit finding #6).
    # Live keys start with sk_live_; test keys sk_test_ are also secrets but
    # much lower blast radius — included at slightly reduced sensitivity.
    ("stripe-live-key", re.compile(r"\bsk_live_[0-9a-zA-Z]{24,}\b")),
    ("stripe-test-key", re.compile(r"\bsk_test_[0-9a-zA-Z]{24,}\b")),
    # HuggingFace API tokens (2026-07-02 Fable audit finding #6).
    ("huggingface-token", re.compile(r"\bhf_[A-Za-z0-9]{34,}\b")),
    # (PEM private key blocks are not in this list. They are found by a linear
    # pairing in _redact_pem below, because the lazy DOTALL regex this used to be
    # went quadratic on a flood of BEGIN lines with no END: 0.6 s at 100,000
    # characters, 10 s at 400,000. Fable audit finding #6, 2026-07-02, named them
    # the highest-severity gap; they are still redacted first, in _scan_string.)
    #
    # Credentials embedded in URLs (2026-07-02 Fable audit finding #6).
    # Matches the scheme://user:password@ prefix; the host/path after the
    # @ is preserved in the surrounding text (only this prefix is replaced
    # with the marker). This deletes the credential while keeping the URL
    # context visible for debugging/audit.
    #
    # THE SCHEME IS BOUNDED AT 32 CHARACTERS (2026-10-07). It was an unbounded run,
    # so on a long run of letters with no "://" every start position walked the whole
    # run again: 4.7 s at 100,000 characters, 77 s at 400,000. A real scheme is
    # shorter than this; a longer one starts its match later in the run, so the span
    # replaced is shorter, but the user:password@ after it is still caught.
    (
        "url-embedded-credential",
        re.compile(r"[a-z][a-z0-9+.\-]{0,31}://[^:/\s@]+:[^@/\s]+@"),
    ),
)

_PEM_BEGIN = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
_PEM_END = re.compile(r"-----END [A-Z ]*PRIVATE KEY-----")
_PEM_NAME = "pem-private-key"
_PEM_TRUNCATED_NAME = "pem-private-key-truncated"
_BLANK_LINE = re.compile(r"\n[ \t\r]*\n")

# A BEGIN line with no END line after it is most likely a key whose output was cut
# off, and the old pattern waited for an END that never came and stored the body in
# the clear (2026-10-07). The stretch redacted is bounded: to the next blank line or
# this many characters, whichever comes first. Roughly the length of a 4096-bit RSA
# key's PEM. The ledger is append-only, so a false positive loses prose for good and
# a false negative stores a live key for good; the ceiling is what keeps a bare header
# mentioned in prose from swallowing a document. A body longer than this, or split
# from its header by a blank line, still leaks its remainder: the bound is the price.
_PEM_TRUNCATED_REACH = 4096


def _redact_pem(value: str) -> tuple[str, list[str]]:
    """Replace each PRIVATE KEY block. Returns the new text and the marker names used.

    A BEGIN with an END after it: the BEGIN line through the nearest END line, the same
    result as the lazy regex this replaces (scanning resumes after the END), in one pass
    over each marker list instead of a rescan to the end of the string for every BEGIN.
    A BEGIN with no END after it: a bounded stretch, under its own marker name so a
    guessed stretch can be told from a whole block.
    """
    begins = [(m.start(), m.end()) for m in _PEM_BEGIN.finditer(value)]
    if not begins:
        return value, []
    ends = [(m.start(), m.end()) for m in _PEM_END.finditer(value)]
    whole = _make_marker(_PEM_NAME)
    guessed = _make_marker(_PEM_TRUNCATED_NAME)
    parts: list[str] = []
    fired: list[str] = []
    pos = 0
    nxt = 0
    for b_start, b_end in begins:
        if b_start < pos:
            continue  # inside a stretch already replaced
        while nxt < len(ends) and ends[nxt][0] < b_end:
            nxt += 1
        parts.append(value[pos:b_start])
        if nxt < len(ends):
            parts.append(whole)
            pos = ends[nxt][1]
            name = _PEM_NAME
        else:
            reach = b_end + _PEM_TRUNCATED_REACH
            blank = _BLANK_LINE.search(value, b_end, reach)
            parts.append(guessed)
            pos = blank.start() if blank else min(reach, len(value))
            name = _PEM_TRUNCATED_NAME
        if name not in fired:
            fired.append(name)
    if not fired:
        return value, []
    parts.append(value[pos:])
    return "".join(parts), fired


def _scan_string(value: str) -> tuple[str, list[str]]:
    """Return (redacted_value, names_of_patterns_that_fired).

    Patterns are applied sequentially. Each match is replaced with the
    pattern's marker. A single string can fire multiple patterns.
    """
    if not value:
        return value, []
    fired: list[str] = []
    out, pem_fired = _redact_pem(value)
    fired.extend(pem_fired)
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
    unique_fired: list[str] = []
    for n in fired_log:
        if n not in seen:
            seen.add(n)
            unique_fired.append(n)
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
