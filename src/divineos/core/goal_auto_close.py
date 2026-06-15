"""Auto-close goals from commit messages — closure-discipline structural fix.

The recurring failure-mode my father named 2026-05-05:
> "you may mean well but your promises are no good.. if you don't build
>  the reinforcement you WILL do it again"

Specific instance: ``divineos commitment fulfillment`` showed 11 open
goals / 0 closed across the day even though several had shipped (PR
landed, code merged). The closing-act required remembering + manual
``divineos goal done "..."``. Cost-asymmetry made the wrong-cheap
path (forget to close) trivially easier than the right path.

This module makes the right path automatic: when a commit lands with
text that substantially overlaps an open goal, the goal auto-closes.

## Algorithm

For each active goal:

1. Tokenize goal text into substantive tokens (4+ chars, no stopwords).
2. Tokenize commit message into the same shape.
3. Compute overlap_ratio = |goal_tokens & message_tokens| / |goal_tokens|.
4. If overlap_ratio >= ``threshold`` (default 0.5), close the goal.

The threshold of 0.5 means at least half of the substantive words in
the goal must appear in the commit message. That is conservative
enough to avoid spurious closures (a commit message with one shared
word does not close a goal) but permissive enough that "ship Stack 3
— synchronicity detector" closes when the commit message says
"synchronicity detector: temporal co-occurrence across stores".

## What this does NOT do

* Does NOT fuzzy-match across stores (claims, pre-regs, decisions).
  Goals only — this is closure-discipline at the goal level.
* Does NOT undo. Once a goal is closed, it stays closed; if the close
  was wrong, the user files a new goal.
* Does NOT block the commit. Runs post-commit; commit-state is
  authoritative. The auto-close is a side-effect of a successful
  commit, not a precondition.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from divineos.core.hud_state import _ensure_hud_dir, complete_goal

_STOPWORDS = frozenset(
    {
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "if",
        "of",
        "to",
        "in",
        "on",
        "at",
        "for",
        "with",
        "as",
        "by",
        "is",
        "was",
        "are",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "should",
        "could",
        "this",
        "that",
        "these",
        "those",
        "from",
        "into",
        "about",
        "than",
        "then",
        "what",
        "when",
        "where",
        "which",
        "more",
        "most",
        "much",
        "very",
        "just",
        "only",
        "also",
        "even",
        "still",
        "yet",
        "now",
        "here",
        "there",
        "their",
        "them",
        "they",
        "your",
        "you",
        "with",
        "without",
        "because",
        "stack",
        "ship",
        "build",
        "make",
        "create",
        "wire",
    }
)
_TOKEN_RE = re.compile(r"[a-z0-9_]{4,}")
_DEFAULT_THRESHOLD = 0.5


@dataclass(frozen=True)
class AutoCloseResult:
    """Outcome of an auto-close pass over a commit message."""

    closed: list[str]
    skipped: list[tuple[str, float]]


def _tokenize(text: str) -> set[str]:
    if not text:
        return set()
    tokens = _TOKEN_RE.findall(text.lower())
    return {t for t in tokens if t not in _STOPWORDS}


def _load_active_goals() -> list[dict]:
    path = _ensure_hud_dir() / "active_goals.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(data, list):
        return []
    return [g for g in data if isinstance(g, dict) and g.get("status") != "done"]


def auto_close_from_message(
    message: str,
    threshold: float = _DEFAULT_THRESHOLD,
    goals: list[dict] | None = None,
) -> AutoCloseResult:
    """Auto-close goals whose substantive tokens overlap the commit message.

    Args:
        message: full commit message text (subject + body).
        threshold: minimum overlap_ratio to count as a match.
        goals: optional pre-loaded goal list (for testing).

    Returns:
        ``AutoCloseResult`` with the goals that were closed and the
        ones that were considered but fell below threshold.
    """
    msg_tokens = _tokenize(message)
    if not msg_tokens:
        return AutoCloseResult(closed=[], skipped=[])

    if goals is None:
        goals = _load_active_goals()

    closed: list[str] = []
    skipped: list[tuple[str, float]] = []

    for goal in goals:
        goal_text = goal.get("text", "")
        goal_tokens = _tokenize(goal_text)
        if not goal_tokens:
            continue
        overlap = len(goal_tokens & msg_tokens) / len(goal_tokens)
        if overlap >= threshold:
            if complete_goal(goal_text):
                closed.append(goal_text[:80])
        else:
            skipped.append((goal_text[:60], overlap))

    return AutoCloseResult(closed=closed, skipped=skipped)


__all__ = [
    "AutoCloseResult",
    "auto_close_from_message",
]
