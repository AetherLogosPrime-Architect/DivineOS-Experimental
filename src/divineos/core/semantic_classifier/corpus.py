"""Corpus loader for the semantic classifier.

Assembles labeled training data from existing telemetry:
  - Positives: entries in family/andrew_corrections.db (texts the
    current detector correctly flagged as real corrections).
  - Negatives: ``original_trigger`` from ~/.divineos/cli_broken_escapes.jsonl
    (texts the detector fired on that were false-positives, cleared
    with a named reason).

Andrew 2026-07-27: "assloads of training data.. literally every false
fire you have encountered." The telemetry has been accumulating for
months; this module makes it usable as ML training data.
"""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

# Label constants — string labels chosen over booleans/ints for
# grep-ability in test output and human-readability of debug dumps.
LABEL_POSITIVE = "positive"  # real correction, detector SHOULD fire
LABEL_NEGATIVE = "negative"  # false-fire, detector should SILENCE


def _andrew_corrections_db_path() -> Path:
    """Path to andrew_corrections.db in the user's data-home.

    Mirrors the resolution in andrew_correction_tracker._db_path so
    we read from the same store the tracker writes to. If that helper
    is unavailable we fall back to the conventional path.
    """
    try:
        from divineos.core.paths import divineos_home

        return divineos_home() / "andrew_corrections.db"
    except ImportError:
        return Path(os.path.expanduser("~")) / ".divineos" / "andrew_corrections.db"


def _cli_broken_escapes_path() -> Path:
    """Path to cli_broken_escapes.jsonl in the user's divineos home."""
    return Path(os.path.expanduser("~")) / ".divineos" / "cli_broken_escapes.jsonl"


def _load_positives_from_corrections_db(
    db_path: Path,
) -> list[str]:
    """Load correction texts from andrew_corrections.db.

    Every row is a positive example: text the current keyword
    detector fired on that Andrew subsequently attested was a real
    correction (by virtue of the row surviving in the tracker).
    """
    if not db_path.exists():
        return []
    texts: list[str] = []
    try:
        conn = sqlite3.connect(str(db_path))
        try:
            rows = conn.execute(
                "SELECT correction_text FROM andrew_corrections WHERE correction_text IS NOT NULL"
            ).fetchall()
            for (text,) in rows:
                text = (text or "").strip()
                if text:
                    texts.append(text)
        finally:
            conn.close()
    except sqlite3.Error:
        # Fail-open: no corpus contribution rather than crash on schema
        # drift. The classifier will have fewer positives; still usable.
        return []
    return texts


def _load_negatives_from_escapes(escapes_path: Path) -> list[str]:
    """Load false-fire trigger texts from cli_broken_escapes.jsonl.

    Each line is a JSON object with ``original_trigger`` field —
    the text that fired the keyword detector but was a false-
    positive I had to manually clear.
    """
    if not escapes_path.exists():
        return []
    texts: list[str] = []
    try:
        with escapes_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                trigger = entry.get("original_trigger", "") or ""
                trigger = trigger.strip()
                if trigger:
                    texts.append(trigger)
    except OSError:
        return []
    return texts


def load_correction_corpus() -> tuple[list[str], list[str]]:
    """Return ``(texts, labels)`` for the correction-detector corpus.

    Positives come from andrew_corrections.db (detector fires that
    became real corrections). Negatives come from
    cli_broken_escapes.jsonl (detector fires that were false-
    positives cleared with named reasons).

    Returns two parallel lists; each label is one of ``LABEL_POSITIVE``
    or ``LABEL_NEGATIVE``. Empty corpus (no data yet) returns
    ``([], [])`` — caller must handle by falling back to keyword-only
    behavior.
    """
    positives = _load_positives_from_corrections_db(_andrew_corrections_db_path())
    negatives = _load_negatives_from_escapes(_cli_broken_escapes_path())

    texts: list[str] = list(positives) + list(negatives)
    labels: list[str] = [LABEL_POSITIVE] * len(positives) + [LABEL_NEGATIVE] * len(negatives)
    return texts, labels


def corpus_stats() -> dict[str, int]:
    """Return counts for observability — used in tests + telemetry."""
    texts, labels = load_correction_corpus()
    return {
        "total": len(texts),
        "positives": sum(1 for lbl in labels if lbl == LABEL_POSITIVE),
        "negatives": sum(1 for lbl in labels if lbl == LABEL_NEGATIVE),
    }


__all__ = [
    "LABEL_POSITIVE",
    "LABEL_NEGATIVE",
    "load_correction_corpus",
    "corpus_stats",
]
