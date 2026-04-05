"""Curiosity Engine — track what the agent wants to learn more about.

When the agent encounters something it doesn't fully understand, or
finds a pattern worth investigating, it files a curiosity. These are
different from claims (which assert something) — curiosities are
genuine questions that drive exploration.

This prevents the pattern where interesting observations get noticed
once and then forgotten. If something is worth investigating, track it.
"""

import json
import time
from typing import Any

from divineos.core._hud_io import _ensure_hud_dir

_CE_ERRORS = (ImportError, OSError, json.JSONDecodeError, KeyError, TypeError, ValueError)

_CURIOSITIES_FILE = "curiosities.json"

CURIOSITY_STATES = ("OPEN", "INVESTIGATING", "ANSWERED", "DORMANT")


# ─── Storage ───────────────────────────────────────────────────────


def _load_curiosities() -> list[dict[str, Any]]:
    """Load curiosities from disk."""
    path = _ensure_hud_dir() / _CURIOSITIES_FILE
    if not path.exists():
        return []
    try:
        result: list[dict[str, Any]] = json.loads(path.read_text(encoding="utf-8"))
        return result
    except _CE_ERRORS:
        return []


def _save_curiosities(curiosities: list[dict[str, Any]]) -> None:
    """Save curiosities to disk."""
    path = _ensure_hud_dir() / _CURIOSITIES_FILE
    path.write_text(json.dumps(curiosities, indent=2), encoding="utf-8")


# ─── Operations ────────────────────────────────────────────────────


def add_curiosity(
    question: str,
    context: str = "",
    category: str = "general",
) -> dict[str, Any]:
    """File a new curiosity — something worth investigating."""
    curiosities = _load_curiosities()

    # Dedup — don't add if same question already open
    for c in curiosities:
        if c.get("question") == question and c.get("status") in ("OPEN", "INVESTIGATING"):
            return c

    entry: dict[str, Any] = {
        "question": question.strip(),
        "context": context.strip(),
        "category": category,
        "status": "OPEN",
        "created_at": time.time(),
        "notes": [],
    }
    curiosities.append(entry)
    _save_curiosities(curiosities)
    return entry


def add_note(question: str, note: str) -> bool:
    """Add a note to an existing curiosity."""
    curiosities = _load_curiosities()
    for c in curiosities:
        if c.get("question") == question and c.get("status") in ("OPEN", "INVESTIGATING"):
            c.setdefault("notes", []).append(
                {
                    "text": note,
                    "added_at": time.time(),
                }
            )
            c["status"] = "INVESTIGATING"
            _save_curiosities(curiosities)
            return True
    return False


def answer_curiosity(question: str, answer: str) -> bool:
    """Mark a curiosity as answered."""
    curiosities = _load_curiosities()
    for c in curiosities:
        if c.get("question") == question and c.get("status") in ("OPEN", "INVESTIGATING"):
            c["status"] = "ANSWERED"
            c["answer"] = answer
            c["answered_at"] = time.time()
            _save_curiosities(curiosities)
            return True
    return False


def shelve_curiosity(question: str) -> bool:
    """Put a curiosity to sleep — not abandoned, just not active."""
    curiosities = _load_curiosities()
    for c in curiosities:
        if c.get("question") == question and c.get("status") in ("OPEN", "INVESTIGATING"):
            c["status"] = "DORMANT"
            _save_curiosities(curiosities)
            return True
    return False


def get_open_curiosities() -> list[dict[str, Any]]:
    """Get all open and investigating curiosities."""
    curiosities = _load_curiosities()
    return [c for c in curiosities if c.get("status") in ("OPEN", "INVESTIGATING")]


def get_all_curiosities() -> list[dict[str, Any]]:
    """Get all curiosities regardless of status."""
    return _load_curiosities()


# ─── Detection ─────────────────────────────────────────────────────

CURIOSITY_PATTERNS = (
    r"\bi wonder\b",
    r"\bwhy does\b",
    r"\bwhy do\b",
    r"\bhow does\b",
    r"\bwhat if\b",
    r"\bcould it be\b",
    r"\binteresting that\b",
    r"\bworth investigating\b",
    r"\bworth exploring\b",
    r"\bI('d| would) like to understand\b",
    r"\bcurious about\b",
    r"\bquestion is\b",
)


def detect_curiosities(text: str) -> list[str]:
    """Detect curiosity-laden sentences in text."""
    import re

    if not text or len(text) < 10:
        return []

    sentences = re.split(r"[.!?\n]", text)
    found: list[str] = []

    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) < 10:
            continue
        for pattern in CURIOSITY_PATTERNS:
            if re.search(pattern, sentence, re.IGNORECASE):
                clean = sentence[:200]
                found.append(clean)
                break

    return found


# ─── Display ───────────────────────────────────────────────────────


def format_curiosities() -> str:
    """Format open curiosities for display."""
    open_ones = get_open_curiosities()
    if not open_ones:
        return "No open curiosities."

    lines = [f"{len(open_ones)} open curiosit{'y' if len(open_ones) == 1 else 'ies'}:"]
    for c in open_ones:
        status = c.get("status", "OPEN")
        q = c.get("question", "")
        if len(q) > 80:
            q = q[:77] + "..."
        icon = "?" if status == "OPEN" else "→"
        lines.append(f"  {icon} {q}")
        notes = c.get("notes", [])
        if notes:
            lines.append(f"    ({len(notes)} note(s))")

    return "\n".join(lines)
