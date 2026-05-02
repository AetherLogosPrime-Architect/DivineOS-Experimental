"""Engagement relevance — does this thinking command relate to current work?

The engagement counter (in hud_handoff.mark_engaged) resets when any
thinking command runs. That's gameable: running `divineos recall` with
no intent is technically a thinking command, and technically resets the
counter, even though nothing in the agent's behavior changed.

This module adds the missing question: *was this thinking command about
anything the agent has been doing?* If the command's text shares at
least one keyword with recent work (file paths, function names, module
names drawn from recent TOOL_CALL events), the clearing is substantive.
If the overlap is zero, the clearing is a shell — the counter should
only partially decay, not fully reset.

Design choices:

* Keywords are drawn from ledger events in a bounded window so the
  check reflects *current* work, not a whole session's surface area.
* Only TOOL_CALL events contribute keywords. File paths and commands
  that the agent has actually touched are legible in a way that
  USER_INPUT (stream-of-consciousness prose) isn't.
* Overlap is case-insensitive substring on whitespace-split tokens.
  The bar is "one shared token." That bar is deliberately generous:
  the failure mode is false positive (too lenient), not false negative
  (too strict). We're guarding against *zero-effort* clears, not
  against operators with legitimate tangential thoughts.
* Empty command text (tool invoked with no query) always counts as
  non-substantive. An empty query IS a shell.

The module is pure functions — no side effects, no DB writes.
"""

from __future__ import annotations

import re
import time
from pathlib import PurePosixPath

KEYWORD_WINDOW_SECONDS = 10 * 60
"""Look back 10 minutes for recent-work keywords. Long enough to span
an exploration pause; short enough that last session's leftovers don't
pass through. Tunable — see pre-reg prereg-637ea9a0d852."""

_TOKEN_PATTERN = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]+")
"""Pull identifier-ish tokens from free text. Minimum 2 chars so we
don't collide with noise like 'a', 'i', 'is'."""

_STOPWORDS = frozenset(
    {
        "the",
        "and",
        "but",
        "for",
        "with",
        "from",
        "this",
        "that",
        "into",
        "just",
        "like",
        "was",
        "are",
        "not",
        "have",
        "has",
        "you",
        "your",
        "its",
        "our",
        "their",
        "what",
        "why",
        "how",
        "when",
        "where",
        "who",
        "which",
        "some",
        "any",
        "all",
        "one",
        "two",
        "three",
        "new",
        "old",
        "use",
        "get",
        "set",
        "make",
        "run",
        "ran",
        "test",
        "tests",
        "file",
        "files",
        "code",
        "work",
        "about",
        "over",
        "under",
        "above",
        "below",
        "because",
        "than",
        "then",
        "also",
        "here",
        "there",
        "only",
        "more",
        "less",
        "very",
        "really",
        "actually",
        "can",
        "will",
        "would",
        "should",
        "could",
        "may",
        "might",
        "must",
        "let",
        "lets",
    }
)
"""Words too common to carry meaning. Thinking commands that contain
only stopwords are treated as shells. These are the words you'd find
in *any* sentence — they can't distinguish substantive-recall from
shell-recall."""


def _tokenize(text: str) -> set[str]:
    """Lowercased identifier-ish tokens, stopwords filtered."""
    if not text:
        return set()
    return {
        match.lower() for match in _TOKEN_PATTERN.findall(text) if match.lower() not in _STOPWORDS
    }


def _path_tokens(path: str) -> set[str]:
    """Extract tokens from a file path — directory names, stem, extension.

    A path like 'src/divineos/core/compass_rudder.py' contributes
    {'src', 'divineos', 'core', 'compass_rudder', 'py', 'compass',
    'rudder'} (the last two from splitting on underscores).
    """
    if not path:
        return set()
    tokens: set[str] = set()
    pp = PurePosixPath(path.replace("\\", "/"))
    for part in pp.parts:
        tokens.update(_tokenize(part))
        # Also split on underscores so compass_rudder contributes
        # 'compass' and 'rudder' as separate keywords.
        for sub in part.split("_"):
            sub_clean = _tokenize(sub)
            tokens.update(sub_clean)
    return tokens


def extract_recent_keywords(
    window_seconds: float = KEYWORD_WINDOW_SECONDS,
    now: float | None = None,
) -> set[str]:
    """Keywords from recent TOOL_CALL events in the ledger.

    Returns the empty set if the ledger is unavailable — the caller
    must treat "no keywords" as "everything is shell" (strict) or
    "nothing is shell" (lenient). The relevance check treats it as
    lenient: if we can't compute a keyword set, we don't penalize.
    Otherwise a broken ledger would block every thinking command.
    """
    ts = now if now is not None else time.time()
    cutoff = ts - window_seconds

    try:
        from divineos.core.ledger import get_connection
    except ImportError:
        return set()

    keywords: set[str] = set()
    try:
        conn = get_connection()
    except Exception:  # noqa: BLE001
        return set()
    try:
        rows = conn.execute(
            "SELECT payload FROM system_events "
            "WHERE event_type = 'TOOL_CALL' AND timestamp >= ? "
            "ORDER BY timestamp DESC LIMIT 200",
            (cutoff,),
        ).fetchall()
    except Exception:  # noqa: BLE001
        return set()
    finally:
        try:
            conn.close()
        except Exception:  # noqa: BLE001
            pass

    import json

    for (payload_text,) in rows:
        try:
            payload = json.loads(payload_text) if payload_text else {}
        except (json.JSONDecodeError, TypeError):
            continue
        tool_input = payload.get("tool_input", {})
        if not isinstance(tool_input, dict):
            continue
        # File path tokens — the strongest signal of what the agent touched.
        for key in ("file_path", "path"):
            val = tool_input.get(key)
            if isinstance(val, str):
                keywords.update(_path_tokens(val))
        # Search patterns — Grep queries reveal what the agent was looking for.
        for key in ("pattern", "query"):
            val = tool_input.get(key)
            if isinstance(val, str):
                keywords.update(_tokenize(val))
        # Edit old_string — the thing being modified.
        old_str = tool_input.get("old_string")
        if isinstance(old_str, str):
            keywords.update(_tokenize(old_str[:500]))  # cap to avoid huge edits
    return keywords


def is_substantive(
    command_text: str,
    keywords: set[str] | None = None,
) -> bool:
    """True when command_text shares at least one non-stopword token with keywords.

    Empty command_text → False (an empty query is always a shell).
    Empty keywords → True (lenient default when ledger is unavailable;
    don't let infrastructure failure punish real thinking commands).
    """
    if not command_text:
        return False
    if keywords is None:
        keywords = extract_recent_keywords()
    if not keywords:
        return True
    cmd_tokens = _tokenize(command_text)
    return bool(cmd_tokens & keywords)
