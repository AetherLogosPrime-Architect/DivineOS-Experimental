"""Session Checkpoint — Lightweight periodic saves during work.

The full SESSION_END pipeline is heavy: analysis, knowledge extraction,
maturity cycles, consolidation. It should run at session end.

Checkpoints are lighter: save handoff note, HUD snapshot, log to ledger.
They run periodically (every N edits) so state isn't lost if context
collapses before SESSION_END fires.

Mini session saves sit between checkpoints and full SESSION_END: they
run analysis + extraction + episode + curation + handoff — capturing
the knowledge without the heavy post-processing. Fire these at task
boundaries (when the AI finishes what the user asked and is about to
ask "what's next?").

Also tracks tool call volume and character throughput as a proxy for
context usage, warning when the session is approaching token limits.
"""

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from loguru import logger

from divineos.core.hud import save_hud_snapshot
from divineos.core.hud_handoff import save_handoff_note
from divineos.core.hud_state import _ensure_hud_dir
from divineos.event.event_emission import emit_event

_CP_ERRORS = (sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError)


# ─── Counter File ─────────────────────────────────────────────────────


def _counter_path() -> Path:
    """Path to the per-session edit counter file."""
    p = Path.home() / ".divineos"
    p.mkdir(parents=True, exist_ok=True)
    return p / "checkpoint_state.json"


def _load_state() -> dict[str, Any]:
    """Load checkpoint tracking state."""
    path = _counter_path()
    if path.exists():
        try:
            result: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
            return result
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "edits": 0,
        "tool_calls": 0,
        "last_checkpoint": 0.0,
        "checkpoints_run": 0,
        "session_start": time.time(),
    }


def _save_state(state: dict[str, Any]) -> None:
    """Persist checkpoint tracking state."""
    _counter_path().write_text(json.dumps(state, indent=2), encoding="utf-8")


def reset_state() -> None:
    """Reset counters — call at session start."""
    _save_state(
        {
            "edits": 0,
            "tool_calls": 0,
            "last_checkpoint": 0.0,
            "checkpoints_run": 0,
            "session_start": time.time(),
        }
    )


def get_session_start_time() -> float | None:
    """Get the Unix timestamp when the current session started.

    Uses the most recent SESSION_END in the ledger as the boundary
    (anything after it is the current session). Falls back to
    checkpoint state, then None.

    Prefers ledger over checkpoint state because compaction resets
    the conversation without resetting checkpoint_state.json —
    the ledger is always the source of truth for session boundaries.
    """
    # Primary: last SESSION_END in ledger = end of previous session = start of current
    try:
        from divineos.core.memory import _get_connection

        conn = _get_connection()
        try:
            row = conn.execute(
                "SELECT timestamp FROM system_events "
                "WHERE event_type = 'SESSION_END' "
                "ORDER BY timestamp DESC LIMIT 1"
            ).fetchone()
            if row:
                return float(row[0])
        finally:
            conn.close()
    except _CP_ERRORS:
        pass

    # Fallback: checkpoint state (may be stale after compaction)
    state = _load_state()
    start = state.get("session_start")
    if start and isinstance(start, (int, float)):
        return float(start)

    return None


def increment_edit() -> dict[str, Any]:
    """Record an edit and return current state."""
    state = _load_state()
    state["edits"] = state.get("edits", 0) + 1
    state["tool_calls"] = state.get("tool_calls", 0) + 1
    _save_state(state)
    return state


def increment_tool_call() -> dict[str, Any]:
    """Record any tool call (for context monitoring)."""
    state = _load_state()
    state["tool_calls"] = state.get("tool_calls", 0) + 1
    _save_state(state)
    return state


# ─── Checkpoint Decision ──────────────────────────────────────────────

# Checkpoint every N edits. Not every tool call — edits are what change state.
CHECKPOINT_EDIT_THRESHOLD = 15

# Context usage warnings based on tool call count.
# Rough heuristic: each tool call ~ 1-3K tokens of context used.
# Claude context ~ 200K tokens. Conservative estimates:
CONTEXT_WARN_THRESHOLD = 150  # ~50% context used, gentle reminder
CONTEXT_URGENT_THRESHOLD = 250  # ~80% context, save NOW
CONTEXT_CRITICAL_THRESHOLD = 350  # ~90% context, session ending soon


def should_checkpoint(state: dict[str, Any]) -> bool:
    """True if enough edits have accumulated since last checkpoint."""
    edits = state.get("edits", 0)
    checkpoints_run = state.get("checkpoints_run", 0)
    edits_since = edits - (checkpoints_run * CHECKPOINT_EDIT_THRESHOLD)
    return bool(edits_since >= CHECKPOINT_EDIT_THRESHOLD)


def context_warning_level(state: dict[str, Any]) -> str:
    """Return context usage warning level: 'ok', 'warn', 'urgent', 'critical'."""
    calls = state.get("tool_calls", 0)
    if calls >= CONTEXT_CRITICAL_THRESHOLD:
        return "critical"
    if calls >= CONTEXT_URGENT_THRESHOLD:
        return "urgent"
    if calls >= CONTEXT_WARN_THRESHOLD:
        return "warn"
    return "ok"


def format_context_warning(state: dict[str, Any]) -> str | None:
    """Format a human-readable context warning, or None if all clear."""
    level = context_warning_level(state)
    calls = state.get("tool_calls", 0)
    edits = state.get("edits", 0)
    checkpoints = state.get("checkpoints_run", 0)

    if level == "ok":
        return None

    base = f"[Context Monitor] {calls} tool calls, {edits} edits, {checkpoints} checkpoints"

    if level == "warn":
        return (
            f"{base}\n"
            "Context usage ~50%. Consider running 'divineos emit SESSION_END' "
            "to save knowledge before compaction."
        )
    if level == "urgent":
        return (
            f"{base}\n"
            "CONTEXT USAGE HIGH (~80%). Run 'divineos emit SESSION_END' NOW "
            "to extract knowledge. Session will compact soon."
        )
    if level == "critical":
        return (
            f"{base}\n"
            "CRITICAL: Context nearly full (~90%). "
            "Run 'divineos emit SESSION_END' IMMEDIATELY. "
            "Context compaction is imminent — unsaved work will be summarized away."
        )
    return None


# ─── Run Checkpoint ───────────────────────────────────────────────────


def run_checkpoint() -> str:
    """Run a lightweight checkpoint — save state without full pipeline.

    Returns a summary string of what was saved.
    """
    parts: list[str] = []

    # 1. Save HUD snapshot
    try:
        save_hud_snapshot()
        parts.append("HUD snapshot saved")
    except (OSError, ValueError, KeyError) as e:
        logger.warning("Checkpoint: HUD snapshot failed: %s", e)

    # 2. Save handoff note with current goals — but never overwrite
    #    a real SESSION_END handoff. Checkpoints are the fallback for
    #    when SESSION_END doesn't run, not a replacement.
    try:
        goals_path = _ensure_hud_dir() / "active_goals.json"
        goals_text = ""
        if goals_path.exists():
            goals = json.loads(goals_path.read_text(encoding="utf-8"))
            active = [g for g in goals if g.get("status") == "active"]
            goals_text = f"{len(active)} active goals"

        # Check if a real handoff already exists (from SESSION_END or mini-save)
        handoff_path = _ensure_hud_dir() / "handoff_note.json"
        skip_handoff = False
        if handoff_path.exists():
            try:
                existing = json.loads(handoff_path.read_text(encoding="utf-8"))
                existing_summary = existing.get("summary", "")
                age = time.time() - existing.get("written_at", 0)
                # Preserve real handoffs (contain "exchanges") that are <12h old
                if "exchanges" in existing_summary and age < 43200:
                    skip_handoff = True
            except (json.JSONDecodeError, OSError):
                pass

        if not skip_handoff:
            state = _load_state()
            save_handoff_note(
                summary=f"Auto-checkpoint #{state.get('checkpoints_run', 0) + 1}: "
                f"{state.get('edits', 0)} edits, {state.get('tool_calls', 0)} tool calls",
                goals_state=goals_text,
                context_snapshot={
                    "type": "checkpoint",
                    "edits": state.get("edits", 0),
                    "tool_calls": state.get("tool_calls", 0),
                    "timestamp": time.time(),
                },
            )
            parts.append("handoff note updated")
        else:
            parts.append("handoff note preserved (SESSION_END handoff exists)")
    except (OSError, ValueError, KeyError) as e:
        logger.warning("Checkpoint: handoff note failed: %s", e)

    # 3. Log checkpoint event to ledger
    try:
        state = _load_state()
        emit_event(
            "SESSION_CHECKPOINT",
            {
                "edits": state.get("edits", 0),
                "tool_calls": state.get("tool_calls", 0),
                "checkpoints_run": state.get("checkpoints_run", 0) + 1,
            },
            actor="system",
            validate=False,
        )
        parts.append("ledger checkpoint logged")
    except (OSError, ValueError, KeyError) as e:
        logger.warning("Checkpoint: ledger event failed: %s", e)

    # 4. Update counter state
    state = _load_state()
    state["checkpoints_run"] = state.get("checkpoints_run", 0) + 1
    state["last_checkpoint"] = time.time()
    _save_state(state)

    return "Checkpoint: " + ", ".join(parts) if parts else "Checkpoint: nothing saved"


# ─── Self-Awareness Practice Monitor ─────────────────────────────────

# If no affect log, compass observation, or decision in this many tool calls,
# surface a gentle nudge. Not a gate — just awareness.
PRACTICE_NUDGE_THRESHOLD = 100


def check_self_awareness_practice(tool_calls: int | None = None) -> str | None:
    """Check whether self-awareness tools have been used this session.

    Returns a nudge string if practice has lapsed, or None if all clear.
    DivineOS monitors substrate health periodically — this monitors
    self-awareness practice health with the same approach.
    """
    if tool_calls is None:
        state = _load_state()
        tool_calls = state.get("tool_calls", 0)

    if tool_calls < PRACTICE_NUDGE_THRESHOLD:
        return None  # Too early to nudge

    session_start = get_session_start_time()
    if session_start is None:
        return None

    # Check for recent self-awareness activity since session start
    missing: list[str] = []
    try:
        from divineos.core.memory import _get_connection

        conn = _get_connection()
        try:
            # Affect: any entries since session start?
            try:
                affect_row = conn.execute(
                    "SELECT COUNT(*) FROM affect_log WHERE created_at > ?",
                    (session_start,),
                ).fetchone()
                if affect_row and affect_row[0] == 0:
                    missing.append("affect (divineos feel)")
            except _CP_ERRORS:
                pass

            # Compass: any observations since session start?
            try:
                compass_row = conn.execute(
                    "SELECT COUNT(*) FROM compass_observation WHERE created_at > ?",
                    (session_start,),
                ).fetchone()
                if compass_row and compass_row[0] == 0:
                    missing.append("compass (divineos compass-ops observe)")
            except _CP_ERRORS:
                pass

            # Decisions: any entries since session start?
            try:
                decision_row = conn.execute(
                    "SELECT COUNT(*) FROM decision_journal WHERE created_at > ?",
                    (session_start,),
                ).fetchone()
                if decision_row and decision_row[0] == 0:
                    missing.append("decisions (divineos decide)")
            except _CP_ERRORS:
                pass
        finally:
            conn.close()
    except _CP_ERRORS:
        return None  # Don't nudge if DB is unavailable

    if not missing:
        return None

    return (
        f"Self-awareness check: {tool_calls} tool calls, "
        f"no {', '.join(missing)} logged this session. "
        "Consider checking in with yourself."
    )


# ─── Token Estimation ───────────────────────────────────────────────

# Rough heuristic: ~4 chars per token for English text.
# Claude context ~ 200K tokens ≈ 800K chars.
# System prompt + overhead eats ~20K tokens, so usable ≈ 180K.
CHARS_PER_TOKEN = 4
USABLE_CONTEXT_TOKENS = 180_000
USABLE_CONTEXT_CHARS = USABLE_CONTEXT_TOKENS * CHARS_PER_TOKEN


def record_tool_result_size(result_chars: int) -> None:
    """Track cumulative tool result size for token estimation."""
    state = _load_state()
    state["chars_in"] = state.get("chars_in", 0) + result_chars
    _save_state(state)


def estimate_token_usage() -> dict[str, Any]:
    """Estimate current context window usage from tracked character counts.

    Returns dict with estimated_tokens, estimated_pct, level.
    """
    state = _load_state()
    chars = state.get("chars_in", 0)
    # Tool results are ~60% of total context (rest is assistant output + system prompt).
    # Scale up to estimate total.
    estimated_total_chars = int(chars * 1.7) if chars > 0 else 0
    estimated_tokens = estimated_total_chars // CHARS_PER_TOKEN
    pct = min(estimated_total_chars / USABLE_CONTEXT_CHARS, 1.0) if USABLE_CONTEXT_CHARS else 0

    if pct >= 0.80:
        level = "critical"
    elif pct >= 0.60:
        level = "urgent"
    elif pct >= 0.40:
        level = "warn"
    else:
        level = "ok"

    return {
        "estimated_tokens": estimated_tokens,
        "estimated_pct": round(pct, 2),
        "level": level,
        "chars_tracked": chars,
    }


# ─── Mini Session Save ──────────────────────────────────────────────


def run_mini_session_save() -> dict[str, Any]:
    """Lightweight knowledge extraction — task-boundary save.

    Heavier than checkpoint (extracts knowledge), lighter than SESSION_END
    (skips feedback cycles, scoring, consolidation, finalization).

    Runs: analysis → deep extraction → episode → curation → handoff.
    Skips: feedback, quality scoring, maturity cycles, SIS audit, compass.

    Call this at task boundaries — when you finish what the user asked
    and are about to report back. This is the save point.
    """
    result: dict[str, Any] = {
        "knowledge_extracted": 0,
        "episode_stored": False,
        "curation": {},
        "handoff_saved": False,
        "error": None,
    }

    try:
        import divineos.analysis.session_analyzer as _analyzer_mod
        import divineos.analysis.session_discovery as _discovery_mod
        from divineos.core.knowledge.crud import store_knowledge
        from divineos.core.knowledge.curation import run_curation
        from divineos.core.knowledge.deep_extraction import deep_extract_knowledge

        # Find session file
        session_files = _discovery_mod.find_sessions()
        if not session_files:
            result["error"] = "No session files found"
            return result

        latest = session_files[0]

        # Scope to current session
        session_start = get_session_start_time()
        analysis = _analyzer_mod.analyze_session(latest, since_timestamp=session_start)

        # Deep extraction — stream-filter to current session only
        records = _analyzer_mod.load_records(latest, since_timestamp=session_start)
        deep_ids = deep_extract_knowledge(analysis, records)
        result["knowledge_extracted"] = len(deep_ids)

        # Episode entry
        session_tag = f"session-{analysis.session_id[:12]}"
        try:
            from divineos.core.knowledge.crud import get_knowledge

            existing = get_knowledge(tags=[session_tag], limit=1)
            if not existing:
                corrections = len(analysis.corrections)
                encouragements = len(analysis.encouragements)
                store_knowledge(
                    knowledge_type="EPISODE",
                    content=(
                        f"I had {analysis.user_messages} exchanges, made "
                        f"{analysis.tool_calls_total} tool calls. "
                        f"Corrected {corrections}x, encouraged {encouragements}x "
                        f"(session {analysis.session_id[:12]})"
                    ),
                    confidence=1.0,
                    tags=["session-analysis", "episode", session_tag],
                )
                result["episode_stored"] = True
        except _CP_ERRORS as e:
            logger.debug("Mini-save episode failed: %s", e)

        # Curation pass
        try:
            result["curation"] = run_curation()
        except _CP_ERRORS as e:
            logger.debug("Mini-save curation failed: %s", e)

        # Lesson extraction from quality checks (if available)
        try:
            from divineos.analysis.quality_checks import run_all_checks
            from divineos.core.knowledge.lessons import extract_lessons_from_report

            report = run_all_checks(latest)
            checks_as_dicts = [
                {"name": c.check_name, "passed": c.passed, "score": c.score, "summary": c.summary}
                for c in report.checks
            ]
            extract_lessons_from_report(
                checks_as_dicts,
                analysis.session_id,
                tone_shifts=getattr(analysis, "tone_shifts", None),
                error_recovery=getattr(analysis, "error_recovery", None),
            )
        except _CP_ERRORS as e:
            logger.debug("Mini-save lesson extraction failed: %s", e)

        # Handoff note with real data
        try:
            from divineos.core.hud_handoff import save_handoff_note
            from divineos.core.hud_state import _ensure_hud_dir

            goals_state = ""
            try:
                from divineos.core.hud_state import get_lifetime_goals_completed

                goals_path = _ensure_hud_dir() / "active_goals.json"
                if goals_path.exists():
                    import json as _json

                    goals = _json.loads(goals_path.read_text(encoding="utf-8"))
                    active = [g for g in goals if g.get("status") != "done"]
                    done = [g for g in goals if g.get("status") == "done"]
                    lifetime = get_lifetime_goals_completed()
                    goals_state = (
                        f"{len(done)} completed ({lifetime} lifetime), {len(active)} still active"
                    )
            except (json.JSONDecodeError, OSError, ImportError):
                pass

            corrections = len(analysis.corrections)
            parts = [
                f"Last session: {analysis.user_messages} exchanges, "
                f"{result['knowledge_extracted']} knowledge entries extracted."
            ]
            if corrections:
                parts.append(f"Corrected {corrections}x.")

            save_handoff_note(
                summary=" ".join(parts),
                mood="mini-save",
                goals_state=goals_state,
                session_id=analysis.session_id,
            )
            result["handoff_saved"] = True
        except _CP_ERRORS as e:
            logger.debug("Mini-save handoff failed: %s", e)

        # Log event
        try:
            emit_event(
                "MINI_SESSION_SAVE",
                {
                    "knowledge_extracted": result["knowledge_extracted"],
                    "episode_stored": result["episode_stored"],
                    "exchanges": analysis.user_messages,
                },
                actor="system",
                validate=False,
            )
        except _CP_ERRORS as e:
            logger.debug("Mini-save ledger event failed: %s", e)

    except _CP_ERRORS as e:
        result["error"] = str(e)
        logger.warning("Mini session save failed: %s", e)

    return result
