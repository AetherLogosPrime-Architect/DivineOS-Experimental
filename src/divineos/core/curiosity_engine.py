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
from divineos.core.constants import SECONDS_PER_DAY

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


# ─── Decay ────────────────────────────────────────────────────────

# Questions older than this many days get auto-shelved during sleep.
_CURIOSITY_STALE_DAYS = 14
# Maximum open curiosities. Oldest get shelved when exceeded.
_CURIOSITY_MAX_OPEN = 15


def prune_stale_curiosities() -> int:
    """Auto-shelve curiosities that have gone stale.

    Called during sleep pruning phase. Two rules:
    1. OPEN curiosities older than 14 days -> DORMANT
    2. If more than 15 open, shelve the oldest until under cap

    Returns number of curiosities shelved.
    """
    curiosities = _load_curiosities()
    now = time.time()
    cutoff = now - (_CURIOSITY_STALE_DAYS * SECONDS_PER_DAY)
    shelved = 0

    # Rule 1: age-based decay
    for c in curiosities:
        if c.get("status") == "OPEN" and c.get("created_at", now) < cutoff:
            c["status"] = "DORMANT"
            c["shelved_reason"] = "stale"
            shelved += 1

    # Rule 2: cap enforcement (shelve oldest first)
    open_ones = [c for c in curiosities if c.get("status") in ("OPEN", "INVESTIGATING")]
    if len(open_ones) > _CURIOSITY_MAX_OPEN:
        # Sort by created_at ascending (oldest first)
        open_ones.sort(key=lambda x: x.get("created_at", 0))
        excess = len(open_ones) - _CURIOSITY_MAX_OPEN
        for c in open_ones[:excess]:
            c["status"] = "DORMANT"
            c["shelved_reason"] = "overflow"
            shelved += 1

    if shelved:
        _save_curiosities(curiosities)

    return shelved


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


# ─── Auto-generation from knowledge gaps ─────────────────────────


def generate_curiosities_from_gaps(max_questions: int = 5) -> list[dict[str, Any]]:
    """Scan the knowledge store for gaps and generate questions.

    This is the proactive mind. Instead of waiting for the Architect to
    ask, the OS looks at its own knowledge and asks: what's incomplete?
    what contradicts? what's stuck?

    Sources of curiosity:
    1. HYPOTHESIS entries with low corroboration — what evidence would promote them?
    2. High-access RAW entries — used often but never validated
    3. Lessons stuck at ACTIVE with 3+ occurrences — why can't we fix this?
    4. Shelved contradictions — what resolves them?
    5. Low-confidence TESTED entries — almost confirmed but not quite
    """
    import sqlite3

    generated: list[dict[str, Any]] = []
    existing_questions = {c.get("question", "") for c in get_open_curiosities()}

    try:
        from divineos.core.knowledge import _get_connection

        conn = _get_connection()
    except (ImportError, sqlite3.OperationalError):
        return generated

    try:
        # 1. Hypotheses needing evidence
        hypotheses = conn.execute(
            """SELECT knowledge_id, content, corroboration_count, access_count
               FROM knowledge
               WHERE maturity = 'HYPOTHESIS' AND superseded_by IS NULL
               ORDER BY access_count DESC LIMIT 5""",
        ).fetchall()

        for kid, content, corrob, access in hypotheses:
            if len(generated) >= max_questions:
                break
            q = f"What evidence would confirm or refute: {content[:120]}?"
            if q not in existing_questions:
                generated.append(
                    add_curiosity(
                        q,
                        context=f"HYPOTHESIS with {corrob} corroborations, {access} accesses",
                        category="validation",
                    )
                )

        # 2. High-access RAW entries — used but never promoted
        raw_popular = conn.execute(
            """SELECT knowledge_id, content, access_count
               FROM knowledge
               WHERE maturity = 'RAW' AND superseded_by IS NULL AND access_count >= 3
               ORDER BY access_count DESC LIMIT 3""",
        ).fetchall()

        for kid, content, access in raw_popular:
            if len(generated) >= max_questions:
                break
            q = f"Why is this still unvalidated despite {access} accesses: {content[:100]}?"
            if q not in existing_questions:
                generated.append(
                    add_curiosity(
                        q,
                        context=f"RAW entry accessed {access} times but never promoted",
                        category="stale_raw",
                    )
                )

        # 3. Recurring lessons — stuck problems
        try:
            from divineos.core.knowledge.lessons import get_lessons

            lessons = get_lessons(status="active")
            stuck = [ls for ls in lessons if ls["occurrences"] >= 3]
            for lesson in stuck[:2]:
                if len(generated) >= max_questions:
                    break
                cat = lesson["category"]
                occ = lesson["occurrences"]
                sessions = len(lesson.get("sessions", []))
                q = (
                    f"Why does '{cat}' keep recurring ({occ}x)? "
                    f"What structural fix would prevent it?"
                )
                if q not in existing_questions:
                    generated.append(
                        add_curiosity(
                            q,
                            context=f"Lesson with {occ} occurrences across {sessions} sessions",
                            category="recurring_lesson",
                        )
                    )
        except _CE_ERRORS:
            pass

        # 4. Shelved contradictions
        shelved = conn.execute(
            """SELECT knowledge_id, content, superseded_by
               FROM knowledge
               WHERE superseded_by LIKE 'FORGET:%Contradictory%'
               LIMIT 3""",
        ).fetchall()

        for kid, content, reason in shelved:
            if len(generated) >= max_questions:
                break
            q = f"What resolves this shelved contradiction: {content[:100]}?"
            if q not in existing_questions:
                generated.append(
                    add_curiosity(
                        q,
                        context=f"Superseded: {reason[:100]}",
                        category="contradiction",
                    )
                )

        # 5. Low-confidence TESTED entries — almost confirmed but not quite
        almost = conn.execute(
            """SELECT knowledge_id, content, confidence, corroboration_count
               FROM knowledge
               WHERE maturity = 'TESTED' AND superseded_by IS NULL AND confidence < 0.8
               ORDER BY corroboration_count DESC LIMIT 2""",
        ).fetchall()

        for kid, content, conf, corrob in almost:
            if len(generated) >= max_questions:
                break
            q = f"What would raise confidence from {conf:.0%} to confirm: {content[:100]}?"
            if q not in existing_questions:
                generated.append(
                    add_curiosity(
                        q,
                        context=f"TESTED but confidence only {conf:.0%}",
                        category="near_confirmation",
                    )
                )

    except (sqlite3.OperationalError, KeyError, TypeError) as e:
        from loguru import logger

        logger.debug(f"Curiosity generation hit error (partial results ok): {e}")
    finally:
        conn.close()

    return generated


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
        if len(q) > 140:
            q = q[:137] + "..."
        icon = "?" if status == "OPEN" else "->"
        lines.append(f"  {icon} {q}")
        notes = c.get("notes", [])
        if notes:
            lines.append(f"    ({len(notes)} note(s))")

    return "\n".join(lines)
