"""Structural fix tracker — reroute `learn` filings that name pending
structural fixes into a persistent obligation surface.

Andrew named the meta-failure 2026-05-14: I had been filing `learn`
entries that named structural fixes I should build, then treating the
filing itself as if it were the structural fix. Filing creates a
record; the structural fix is a code change that alters the execution
path. The substrate had no mechanism distinguishing record-from-fix,
so the optimizer routed to `learn` every time, called it done, and
the named fixes never got built.

This module is the structural fix for THAT meta-failure. The `learn`
CLI now inspects content for structural-fix-shape language; when
detected, it writes a parallel entry to a tracked-pending file. The
briefing dashboard surfaces unfulfilled pending entries at session
start so they become visible obligations, not silent records.
"""

from __future__ import annotations

# Module-level guardrail marker — Aletheia Finding 48 class-fix
# 2026-05-14. CI test (tests/test_guardrail_marker_consistency.py)
# walks src/ and asserts every file with this marker set to True is
# listed in scripts/guardrail_files.txt. Prevents the next refactor
# from silently removing self-enforcement code from multi-party review.
__guardrail_required__ = True

import json
import re
import time
import uuid
from divineos.core.paths import marker_path

# Patterns that name structural-fix-shape language. Order matters:
# more specific intent-of-building patterns ("should build", "the
# actual fix") come BEFORE generic build patterns so they win when
# both match (refined 2026-05-14 after test_detect_should_build
# initially routed to "build a detector" by ordering accident).
_STRUCTURAL_FIX_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("structural fix", re.compile(r"\bstructural fix(?:es)?\b", re.IGNORECASE)),
    ("structural change", re.compile(r"\bstructural change\b", re.IGNORECASE)),
    ("the actual fix", re.compile(r"\bthe (?:actual|real) fix (?:is|would be)\b", re.IGNORECASE)),
    ("should build", re.compile(r"\b(?:should|need to|going to|will)\s+build\b", re.IGNORECASE)),
    ("to prevent recurrence", re.compile(r"\bto prevent recurrence\b", re.IGNORECASE)),
    (
        "build a detector",
        re.compile(
            r"\bbuild(?:s|ing)?\s+(?:a|the|an)\s+(?:detector|gate|check|test|monitor|surface|probe)\b",
            re.IGNORECASE,
        ),
    ),
    (
        # Allow multi-token gap between the verb and the preposition
        # (e.g. "wiring THE DETECTOR into the hook"). Bounded to keep
        # cross-sentence matches from firing.
        "wire X into Y",
        re.compile(
            r"\b(?:wire(?:s|d)?|wiring)\b[^.\n]{1,80}\b(?:into|through)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "add a gate",
        re.compile(
            r"\badd(?:s|ing)?\s+(?:a|the|an)\s+(?:gate|guard|check|enforcement)\b",
            re.IGNORECASE,
        ),
    ),
)


def _excerpt(content: str) -> str:
    """The stored form of an obligation's text: 200 chars, stripped at BOTH
    ends of the truncation.

    STRIP-THEN-TRUNCATE LEAVES A TRAILING SPACE. (2026-08-25.)

    The original was ``content.strip()[:200]`` — stripped first, cut second.
    When character 200 lands on a space, the stored excerpt keeps it. The
    dedup then compared ``stored.strip()`` against a freshly-computed
    ``content.strip()[:200]``, one side stripped and the other not, so the two
    never matched and every later filing of that exact text opened a NEW row.

    A one-character coincidence, and it defeats the dedup completely for any
    text unlucky enough to break on a space. Found in the four rows the
    corrections-side backfill could not match: stored length 200, stripped
    length 199, identical once both sides were stripped.

    The dedup shipped 2026-08-24 to end duplicate rows and carried a silent
    generator for a slice of them. Both call sites go through here now so
    there is one definition of "the same obligation" instead of two that
    agree most of the time.
    """
    return content.strip()[:200].strip()


def _read_pending() -> list[dict]:
    """Read the MAIN list (entries that still need doing, not yet picked up).
    Fail-open on missing/malformed."""
    if not marker_path("pending_structural_fixes.json").exists():
        return []
    try:
        data = json.loads(marker_path("pending_structural_fixes.json").read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        return []
    except (OSError, json.JSONDecodeError, ValueError):
        return []


def _write_pending(entries: list[dict]) -> None:
    """Write the MAIN list back. Fail-open on I/O error."""
    try:
        marker_path("pending_structural_fixes.json").parent.mkdir(parents=True, exist_ok=True)
        marker_path("pending_structural_fixes.json").write_text(
            json.dumps(entries, indent=2), encoding="utf-8"
        )
    except OSError:
        pass


def _read_current() -> list[dict]:
    """Read the CURRENT working-list (entries actively picked up). Fail-open."""
    p = marker_path("current_structural_fixes.json")
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError, ValueError):
        return []


def _write_current(entries: list[dict]) -> None:
    """Write the CURRENT working-list back. Fail-open."""
    try:
        p = marker_path("current_structural_fixes.json")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    except OSError:
        pass


def _append_archive(entry: dict) -> None:
    """Append a single completed entry to the archive (JSONL). Fail-open."""
    try:
        p = marker_path("archive_structural_fixes.jsonl")
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError:
        pass


def detect_structural_fix_shape(content: str) -> str | None:
    """Return the trigger phrase if structural-fix-shape language is
    present; None otherwise. Used by `learn` CLI to decide whether to
    record a pending entry alongside the knowledge filing."""
    if not content:
        return None
    for label, pattern in _STRUCTURAL_FIX_PATTERNS:
        if pattern.search(content):
            return label
    return None


def record_pending_fix(
    content: str,
    lesson_id: str = "",
    trigger: str = "",
    source_kind: str = "learn",
) -> str:
    """Record a pending structural-fix entry. Returns the psf id, or
    empty string on I/O failure.

    ``source_kind`` names the filing surface that produced this entry:
    "learn" (the original), "correction", "claim", or any future
    surface that scans for structural-fix-shape language. The field is
    stored so queries can distinguish where the obligation was named,
    and so the narrowness-of-wiring failure (only learn scanned, when
    most structural-fix naming actually happens via correction/claim/
    chat) is empirically visible in the data.

    Added 2026-05-18 after Andrew named: 'see you found this but were
    not aware of it.. is it even wired up and being used?' Two entries
    in five days was direct evidence the wiring was too narrow.
    """
    if not content:
        return ""
    excerpt = _excerpt(content)
    entries = _read_pending()

    # ONE ROW, MANY STAMPS. (Andrew 2026-08-09.)
    #
    # The backlog held 129 rows and 65 of them were the same text: the
    # emergency bypass of check-branch-on-push, fired across 11 days while I
    # was gate-locked. I first argued those 65 were signal rather than junk.
    # Andrew: "65 duplicate rows IS noise and is junk to be deleted.. it
    # should be a single row with 65 stamps on it, but the fact you are
    # ignoring them is the real issue.. you should only need to be told once,
    # if that one time doesnt work? then repeating it 64 more times wont."
    #
    # He is right and the distinction is exact. The FACT is signal -- this
    # happened 65 times and was never fixed. The STORAGE was junk: 64 rows
    # carrying no information the first row did not already carry, burying the
    # other 64 distinct obligations they shared a list with. A count preserves
    # every bit of the signal and costs one row.
    #
    # And the repetition was never going to work. A mechanism whose response
    # to being ignored is to say the same thing again is not escalating, it is
    # diluting -- each copy makes the list longer and every individual row
    # matter less. That is why `occurrences` exists: so the surface can rank
    # by how many times it has asked rather than by how recently, and being
    # ignored makes an item LOUDER instead of just more numerous.
    for e in entries:
        if e.get("status") == "done":
            continue
        if (e.get("content_excerpt") or "").strip() != excerpt:
            continue
        now = time.time()
        e["occurrences"] = int(e.get("occurrences", 1)) + 1
        e["last_seen"] = now
        # Bounded: the count is authoritative, the stamps are for reading the
        # shape of the recurrence. An unbounded list would re-grow the exact
        # problem this fix exists to remove.
        stamps = list(e.get("stamps") or [e.get("created_at", now)])
        stamps.append(now)
        e["stamps"] = stamps[-20:]
        _write_pending(entries)
        return str(e.get("id") or "")

    psf_id = f"psf-{uuid.uuid4().hex[:8]}"
    now = time.time()
    entry = {
        "id": psf_id,
        "created_at": now,
        "lesson_id": lesson_id,
        "content_excerpt": excerpt,
        "trigger": trigger,
        "source_kind": source_kind,
        "status": "pending",
        "occurrences": 1,
        "last_seen": now,
        "stamps": [now],
    }
    entries.append(entry)
    _write_pending(entries)
    return psf_id


def list_pending(include_done: bool = False) -> list[dict]:
    """Return pending structural fixes. By default, excludes entries
    marked done. Used by the briefing dashboard row-builder."""
    entries = _read_pending()
    if include_done:
        return entries
    return [e for e in entries if e.get("status") != "done"]


def mark_done(psf_id: str, note: str = "") -> bool:
    """Move an entry from the CURRENT working-list to the ARCHIVE.

    Andrew architecture 2026-06-27: an item only lives in one place at a
    time based on its state. mark_done is the current → archive transition.
    Falls back to MAIN if the id isn't in current (backward-compat for
    items that were never picked but got marked done directly).
    """
    # Try current first (the proper flow).
    current = _read_current()
    found_entry = None
    remaining = []
    for entry in current:
        if entry.get("id") == psf_id and found_entry is None:
            found_entry = entry
        else:
            remaining.append(entry)
    if found_entry:
        found_entry["status"] = "done"
        found_entry["done_at"] = time.time()
        if note:
            found_entry["done_note"] = note
        _append_archive(found_entry)
        _write_current(remaining)
        return True

    # Fallback: try main (item was never picked but is being closed directly).
    pending = _read_pending()
    found_entry = None
    remaining = []
    for entry in pending:
        if entry.get("id") == psf_id and found_entry is None:
            found_entry = entry
        else:
            remaining.append(entry)
    if found_entry:
        found_entry["status"] = "done"
        found_entry["done_at"] = time.time()
        if note:
            found_entry["done_note"] = note
        _append_archive(found_entry)
        _write_pending(remaining)
        return True

    return False


def close_twin_for_text(text: str, note: str, source_kind: str = "correction") -> list[str]:
    """Close any pending entry whose excerpt came from ``text``. Returns the
    ids closed.

    THE MIRROR HAD NO RETURN PATH. (2026-08-25.)

    ``correction`` and ``claim`` both file a parallel psf row when their text
    is structural-fix-shaped — 187 of the 334 rows in the backlog came in that
    way. Neither surface ever closed one. So a correction could be marked
    INTEGRATED with evidence in ``andrew_corrections.db`` while its twin sat
    in this list forever, indistinguishable from work nobody had touched. On
    the day this was measured, 50 of the 187 were already closed on the
    corrections side and still pending here.

    That is not a stale backlog, it is two stores disagreeing, and the one
    without a close verb is the one the briefing reads out. A mirror that
    copies the filing and not the closing reports a debt that has been paid.

    Matched on the excerpt rather than a stored id because the 187 existing
    rows predate any linking field, and a fix that only works for future rows
    would leave exactly the pile it was written for — the same shape as the
    dedup that shipped without a backfill (see ``collapse_duplicates``).
    """
    if not text:
        return []
    excerpt = _excerpt(text)
    closed: list[str] = []
    for entry in list(_read_pending()):
        if entry.get("status") == "done":
            continue
        if entry.get("source_kind") != source_kind:
            continue
        if (entry.get("content_excerpt") or "").strip() != excerpt:
            continue
        psf_id = str(entry.get("id") or "")
        if psf_id and mark_done(psf_id, note):
            closed.append(psf_id)
    return closed


def collapse_duplicates() -> dict[str, int]:
    """Collapse pre-existing exact-duplicate rows in MAIN into one row each,
    carrying the count forward as ``occurrences``. Returns a summary dict.

    THE DEDUP HAD NO BACKFILL. (2026-08-25.)

    ``record_pending_fix`` grew the one-row-many-stamps behaviour on
    2026-08-24 (06e3de62) in answer to Andrew 2026-08-09: "it should be a
    single row with 65 stamps on it." That stops NEW duplicates. It never
    looked backward, so the 92 rows the correction was about were still
    sitting in the list the day after the fix shipped — the pile the fix
    existed to remove, untouched by it, with the fix reported as done.

    Fifteen days also separate the correction from the code. During those
    fifteen days the duplicates kept arriving through the un-deduped writer,
    which is why the backlog is 92 redundant rows and not 65.

    Collapse rules:
      - group by exact ``content_excerpt.strip()``
      - the EARLIEST-created row survives and keeps its id, so any must-read
        or briefing surface already pointing at that id still resolves
      - ``occurrences`` becomes the sum across the group (rows written before
        the field existed count as 1)
      - ``stamps`` merges every group member's stamps, sorted, last 20 kept —
        the same bound ``record_pending_fix`` uses, for the same reason
      - absorbed rows go to the ARCHIVE with ``collapsed_into`` naming the
        survivor, so no row is silently dropped

    Idempotent: running it on an already-collapsed list changes nothing.
    """
    entries = _read_pending()
    groups: dict[str, list[dict]] = {}
    for entry in entries:
        if entry.get("status") == "done":
            continue
        groups.setdefault((entry.get("content_excerpt") or "").strip(), []).append(entry)

    survivors: dict[str, dict] = {}
    absorbed: list[dict] = []
    for excerpt, rows in groups.items():
        rows.sort(key=lambda e: e.get("created_at", 0))
        keeper = rows[0]
        if len(rows) > 1:
            total = sum(int(r.get("occurrences") or 1) for r in rows)
            stamps: list[float] = []
            for r in rows:
                stamps.extend(r.get("stamps") or [r.get("created_at", 0)])
            keeper["occurrences"] = total
            keeper["stamps"] = sorted(s for s in stamps if s)[-20:]
            keeper["last_seen"] = max(
                [r.get("last_seen") or r.get("created_at", 0) for r in rows] or [0]
            )
            keeper["collapsed_from"] = [r.get("id") for r in rows[1:]]
            for r in rows[1:]:
                r["collapsed_into"] = keeper.get("id")
                r["status"] = "collapsed"
                r["collapsed_at"] = time.time()
                absorbed.append(r)
        survivors[excerpt] = keeper

    if not absorbed:
        return {"rows_before": len(entries), "rows_after": len(entries), "collapsed": 0}

    for row in absorbed:
        _append_archive(row)

    done_rows = [e for e in entries if e.get("status") == "done"]
    kept = list(survivors.values()) + done_rows
    kept.sort(key=lambda e: e.get("created_at", 0))
    _write_pending(kept)
    return {
        "rows_before": len(entries),
        "rows_after": len(kept),
        "collapsed": len(absorbed),
    }


def pick_to_current(psf_id: str) -> bool:
    """Move an entry from MAIN to CURRENT (the "I'm picking this up" step).

    Andrew architecture 2026-06-27: picking is an atomic move, not a copy.
    The entry leaves main and lives in current until done. Returns True if
    found and moved, False if the id wasn't in main.
    """
    pending = _read_pending()
    found_entry = None
    remaining = []
    for entry in pending:
        if entry.get("id") == psf_id and found_entry is None:
            found_entry = entry
        else:
            remaining.append(entry)
    if not found_entry:
        return False
    found_entry["picked_at"] = time.time()
    found_entry["status"] = "current"
    current = _read_current()
    current.append(found_entry)
    _write_current(current)
    _write_pending(remaining)
    return True


def list_current() -> list[dict]:
    """Return entries actively picked up (in the working-list)."""
    return _read_current()


def sweep_stale_from_main(days_threshold: float = 30.0) -> list[str]:
    """Walk MAIN for entries older than the threshold. Returns the list of
    psf_ids that look stale — caller decides whether to archive-as-stale or
    delete or leave them. v1 of the sweep is just surfacing; cleanup is a
    separate explicit action so we don't silently lose work.
    """
    now = time.time()
    cutoff = now - (days_threshold * 86400)
    pending = _read_pending()
    stale = []
    for entry in pending:
        created = entry.get("created_at", 0)
        if created and created < cutoff:
            stale.append(entry.get("id", "?"))
    return stale


def archive_stale_from_main(psf_ids: list[str], reason: str = "stale-sweep") -> int:
    """Move the named ids from MAIN directly to ARCHIVE (skipping current).
    Used after sweep_stale_from_main surfaces candidates and the operator
    confirms. Returns the count actually archived.
    """
    pending = _read_pending()
    archived = 0
    remaining = []
    target_set = set(psf_ids)
    for entry in pending:
        if entry.get("id") in target_set:
            entry["status"] = "stale-archived"
            entry["archived_at"] = time.time()
            entry["archive_reason"] = reason
            _append_archive(entry)
            archived += 1
        else:
            remaining.append(entry)
    if archived:
        _write_pending(remaining)
    return archived


__all__ = [
    "archive_stale_from_main",
    "detect_structural_fix_shape",
    "list_current",
    "list_pending",
    "mark_done",
    "pick_to_current",
    "record_pending_fix",
    "sweep_stale_from_main",
]
