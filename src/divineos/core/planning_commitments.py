"""Planning Commitments — track promises, check fulfillment.

When the agent says "I'll fix X next" or "let me refactor Y", that's a
commitment. This module captures those promises and checks at session end
whether they were actually fulfilled.

The anti-pattern this prevents: confidently promising actions, then
quietly dropping them. If you say you'll do something, the OS remembers.

Commitments are lightweight — just text + status + timestamps. They live
in .hud/commitments.json alongside goals and task state.
"""

import json
import re
import time
from dataclasses import asdict, dataclass, field
from typing import Any

from divineos.core._hud_io import _ensure_hud_dir

_PC_ERRORS = (ImportError, OSError, json.JSONDecodeError, KeyError, TypeError, ValueError)

# ─── Commitment Detection ──────────────────────────────────────────

# Patterns that indicate the agent is making a commitment
# These match agent speech, not user speech
COMMITMENT_PATTERNS: tuple[str, ...] = (
    r"\bi'?ll (?:also |then |now |first |next )?(?:fix|add|update|refactor|clean|remove|write|create|build|implement|test|check|verify|handle|address)\b",
    r"\blet me (?:also |first |now |next )?(?:fix|add|update|refactor|clean|remove|write|create|build|implement|test|check|verify|handle|address)\b",
    r"\bnext i'?ll\b",
    r"\bafter (?:that|this) i'?ll\b",
    r"\bi need to (?:also )?(?:fix|add|update|refactor|clean|remove|write|create|build|implement|test|check|verify|handle|address)\b",
    r"\bi should (?:also )?(?:fix|add|update|refactor|clean|remove|write|create|build|implement|test|check|verify|handle|address)\b",
    r"\bthen i'?ll\b",
    r"\bmy plan is to\b",
    r"\bthe plan is to\b",
)

_COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in COMMITMENT_PATTERNS]

# Patterns that indicate fulfillment happened
FULFILLMENT_SIGNALS: tuple[str, ...] = (
    r"\bdone\b",
    r"\bcomplete[d]?\b",
    r"\bfinished\b",
    r"\bfixed\b",
    r"\badded\b",
    r"\bupdated\b",
    r"\bimplemented\b",
    r"\brefactored\b",
    r"\bcreated\b",
    r"\bbuilt\b",
    r"\bwritten\b",
    r"\bpassing\b",
    r"\bworks\b",
    r"\ball (?:\d+ )?tests pass\b",
)

_COMPILED_FULFILLMENT = [re.compile(p, re.IGNORECASE) for p in FULFILLMENT_SIGNALS]


# ─── Data Model ────────────────────────────────────────────────────


@dataclass
class Commitment:
    """A trackable promise the agent made."""

    text: str  # what was promised
    created_at: float = field(default_factory=time.time)
    status: str = "pending"  # pending | fulfilled | dropped | deferred
    fulfilled_at: float | None = None
    context: str = ""  # surrounding context when commitment was made

    def fulfill(self) -> None:
        self.status = "fulfilled"
        self.fulfilled_at = time.time()

    def drop(self, reason: str = "") -> None:
        self.status = "dropped"
        self.context = reason if reason else self.context

    def defer(self) -> None:
        self.status = "deferred"


# ─── Storage ───────────────────────────────────────────────────────

_COMMITMENTS_FILE = "commitments.json"


def _load_commitments() -> list[dict[str, Any]]:
    """Load commitments from disk."""
    path = _ensure_hud_dir() / _COMMITMENTS_FILE
    if not path.exists():
        return []
    try:
        result: list[dict[str, Any]] = json.loads(path.read_text(encoding="utf-8"))
        return result
    except _PC_ERRORS:
        return []


def _save_commitments(commitments: list[dict[str, Any]]) -> None:
    """Save commitments to disk."""
    path = _ensure_hud_dir() / _COMMITMENTS_FILE
    path.write_text(json.dumps(commitments, indent=2), encoding="utf-8")


def add_commitment(text: str, context: str = "") -> Commitment:
    """Record a new commitment."""
    commitment = Commitment(text=text.strip(), context=context.strip())
    entries = _load_commitments()

    # Deduplicate — don't add if same text already pending
    for entry in entries:
        if entry.get("text") == commitment.text and entry.get("status") == "pending":
            return Commitment(**entry)

    entries.append(asdict(commitment))
    _save_commitments(entries)
    return commitment


def get_pending_commitments() -> list[Commitment]:
    """Get all unfulfilled commitments."""
    entries = _load_commitments()
    return [Commitment(**e) for e in entries if e.get("status") == "pending"]


def fulfill_commitment(text: str) -> bool:
    """Mark a commitment as fulfilled by fuzzy text match.

    Returns True if a matching commitment was found and fulfilled.
    """
    entries = _load_commitments()
    text_lower = text.lower()
    text_words = set(text_lower.split())

    for entry in entries:
        if entry.get("status") != "pending":
            continue
        entry_words = set(entry.get("text", "").lower().split())
        if not entry_words:
            continue
        overlap = len(text_words & entry_words) / max(len(text_words | entry_words), 1)
        if overlap > 0.4:  # 40% word overlap = likely same commitment
            entry["status"] = "fulfilled"
            entry["fulfilled_at"] = time.time()
            _save_commitments(entries)
            return True

    return False


def clear_commitments() -> None:
    """Clear all commitments (called at session end after review)."""
    path = _ensure_hud_dir() / _COMMITMENTS_FILE
    if path.exists():
        path.unlink()


# ─── Detection ─────────────────────────────────────────────────────


def detect_commitments(text: str) -> list[str]:
    """Extract commitment phrases from agent text.

    Returns the sentences containing commitment language.
    """
    if not text or len(text) < 10:
        return []

    # Split into sentences
    sentences = re.split(r"[.!?\n]", text)
    commitments: list[str] = []

    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) < 10:
            continue
        for pattern in _COMPILED_PATTERNS:
            if pattern.search(sentence):
                # Clean up the sentence
                clean = sentence.strip()
                if len(clean) > 200:
                    clean = clean[:197] + "..."
                commitments.append(clean)
                break  # one match per sentence is enough

    return commitments


# ─── Fulfillment Check ─────────────────────────────────────────────


def check_fulfillment(
    commitment_text: str,
    session_events: list[str],
) -> dict[str, Any]:
    """Check whether a commitment was likely fulfilled during the session.

    Uses word overlap between the commitment and session events to detect
    whether the promised action was carried out.

    Returns:
      - likely_fulfilled: bool
      - confidence: float (0.0 to 1.0)
      - matching_event: str or None
    """
    if not session_events:
        return {"likely_fulfilled": False, "confidence": 0.0, "matching_event": None}

    commitment_words = set(commitment_text.lower().split())
    # Extract action words from commitment (verbs that describe what was promised)
    action_words = commitment_words - {
        "i",
        "ll",
        "i'll",
        "let",
        "me",
        "also",
        "then",
        "now",
        "first",
        "next",
        "need",
        "to",
        "should",
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "in",
        "on",
        "for",
        "with",
        "this",
        "that",
        "it",
        "is",
        "will",
        "be",
        "my",
        "plan",
        "after",
    }

    best_overlap = 0.0
    best_event = None

    for event in session_events:
        event_lower = event.lower()

        # Check for fulfillment signal words
        has_signal = any(p.search(event_lower) for p in _COMPILED_FULFILLMENT)

        event_words = set(event_lower.split())
        if not action_words:
            continue

        overlap = len(action_words & event_words) / max(len(action_words), 1)

        # Boost score if fulfillment signals present
        if has_signal:
            overlap = min(overlap * 1.3, 1.0)

        if overlap > best_overlap:
            best_overlap = overlap
            best_event = event

    return {
        "likely_fulfilled": best_overlap >= 0.3,
        "confidence": round(best_overlap, 2),
        "matching_event": best_event if best_overlap >= 0.3 else None,
    }


# ─── Session-End Review ───────────────────────────────────────────


def review_commitments(
    session_events: list[str] | None = None,
) -> dict[str, Any]:
    """Review all pending commitments at session end.

    Returns a summary with counts and details for each commitment.
    """
    pending = get_pending_commitments()
    if not pending:
        return {
            "total": 0,
            "fulfilled": 0,
            "dropped": 0,
            "deferred": 0,
            "details": [],
        }

    events = session_events or []
    results: list[dict[str, Any]] = []
    fulfilled_count = 0
    dropped_count = 0

    entries = _load_commitments()

    for commitment in pending:
        check = check_fulfillment(commitment.text, events)
        if check["likely_fulfilled"]:
            # Auto-fulfill
            for entry in entries:
                if entry.get("text") == commitment.text and entry.get("status") == "pending":
                    entry["status"] = "fulfilled"
                    entry["fulfilled_at"] = time.time()
                    break
            fulfilled_count += 1
            results.append(
                {
                    "text": commitment.text,
                    "status": "fulfilled",
                    "confidence": check["confidence"],
                    "matching_event": check["matching_event"],
                }
            )
        else:
            # Mark as dropped — wasn't done
            for entry in entries:
                if entry.get("text") == commitment.text and entry.get("status") == "pending":
                    entry["status"] = "dropped"
                    break
            dropped_count += 1
            results.append(
                {
                    "text": commitment.text,
                    "status": "dropped",
                    "confidence": check["confidence"],
                    "matching_event": None,
                }
            )

    _save_commitments(entries)

    return {
        "total": len(pending),
        "fulfilled": fulfilled_count,
        "dropped": dropped_count,
        "deferred": 0,
        "details": results,
    }


def format_commitment_review(review: dict[str, Any]) -> str:
    """Format commitment review for display."""
    if review["total"] == 0:
        return ""

    lines = [f"Commitments: {review['fulfilled']}/{review['total']} fulfilled"]

    for detail in review["details"]:
        status = detail["status"].upper()
        icon = "✓" if status == "FULFILLED" else "✗"
        text = detail["text"]
        if len(text) > 80:
            text = text[:77] + "..."
        lines.append(f"  {icon} [{status}] {text}")

    if review["dropped"] > 0:
        lines.append(f"  → {review['dropped']} commitment(s) not fulfilled this session")

    return "\n".join(lines)
