"""HUD Session Lifecycle — Handoff notes, engagement gate, goal extraction.

Manages the between-session handoff system, the engagement gate that
ensures the OS is used for thinking before recording, and extraction
of goals from user messages.
"""

import json
import re
import sqlite3
import time
from pathlib import Path
from typing import Any

from loguru import logger

from divineos.core._hud_io import _ensure_hud_dir, _get_hud_dir
from divineos.core.constants import TIME_HANDOFF_EXPIRY_HOURS
from divineos.core.hud_state import has_session_fresh_goal
from divineos.core.ledger import count_events

_HH_ERRORS = (
    ImportError,
    sqlite3.OperationalError,
    OSError,
    KeyError,
    TypeError,
    ValueError,
    json.JSONDecodeError,
)


# ─── Session Handoff Notes ───────────────────────────────────────────


def _extract_exchange_count(summary: str) -> int:
    """Parse exchange count from handoff summary text like '12 exchanges'."""
    match = re.search(r"(\d+)\s+exchanges?", summary)
    return int(match.group(1)) if match else 0


def save_handoff_note(
    summary: str,
    open_threads: list[str] | None = None,
    mood: str = "",
    goals_state: str = "",
    session_id: str = "",
    intent: str = "",
    blockers: list[str] | None = None,
    next_steps: list[str] | None = None,
    context_snapshot: dict[str, Any] | None = None,
) -> Path:
    """Write a handoff note for the next session to pick up.

    New structured fields for richer continuation:
    - intent: what the user was trying to accomplish
    - blockers: what stopped progress
    - next_steps: concrete actions for the next session
    - context_snapshot: key facts (knowledge IDs, recent decisions, grade)
    """
    path = _ensure_hud_dir() / "handoff_note.json"

    # Don't overwrite a good handoff with an empty post-compaction one.
    # If the existing note has more exchanges and was written recently
    # (same logical session), preserve it.
    new_exchange_count = _extract_exchange_count(summary)
    if path.exists() and new_exchange_count == 0:
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
            existing_count = _extract_exchange_count(existing.get("summary", ""))
            age = time.time() - existing.get("written_at", 0)
            if existing_count > 0 and age < _HANDOFF_EXPIRY_SECONDS:
                logger.info(
                    "Preserving existing handoff (%d exchanges) over empty post-compaction write",
                    existing_count,
                )
                return path
        except (json.JSONDecodeError, OSError, KeyError) as e:
            logger.debug("Could not read existing handoff note, overwriting: %s", e)

    note: dict[str, Any] = {
        "session_id": session_id,
        "written_at": time.time(),
        "summary": summary,
        "open_threads": open_threads or [],
        "mood": mood,
        "goals_state": goals_state,
    }
    if intent:
        note["intent"] = intent
    if blockers:
        note["blockers"] = blockers
    if next_steps:
        note["next_steps"] = next_steps
    if context_snapshot:
        note["context_snapshot"] = context_snapshot
    path.write_text(json.dumps(note, indent=2), encoding="utf-8")
    logger.debug("Handoff note saved to %s", path)
    return path


_HANDOFF_EXPIRY_SECONDS = TIME_HANDOFF_EXPIRY_HOURS * 3600


def load_handoff_note() -> dict[str, Any] | None:
    """Load the handoff note from the previous session, if any.

    Returns None and auto-clears if the note is older than 12 hours.
    """
    path = _get_hud_dir() / "handoff_note.json"
    if not path.exists():
        return None
    try:
        result: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        # Auto-expire stale handoff notes
        written_at = result.get("written_at", 0)
        if written_at and (time.time() - written_at) > _HANDOFF_EXPIRY_SECONDS:
            logger.debug("Handoff note expired (>12h old), clearing")
            path.unlink(missing_ok=True)
            return None
        return result
    except (json.JSONDecodeError, OSError):
        return None


def clear_handoff_note() -> None:
    """Clear the handoff note (called after briefing consumes it)."""
    path = _get_hud_dir() / "handoff_note.json"
    if path.exists():
        path.unlink()


# ─── Session Engagement Gate ─────────────────────────────────────────

# After this many code-changing actions (Edit, Write, Bash) without
# consulting the OS (ask, recall, decide, feel, context, directives),
# the engagement gate blocks until the AI re-engages.
# Was 8 — too tight for mechanical repetitive work. 15 (2026-04) left
# too little headroom for related-change batches during a single
# logical PR, which typically involves 15-20 edit+test+verify actions.
# 20 (2026-04-19) gives room for a coherent PR-shaped batch before
# requiring a thinking pause. Flow-state detection still catches pure
# blast-coding (threshold bumps to 50 when actions are <10s apart).
# If drift measurably increases under 20, revert to 15.
_ENGAGEMENT_DECAY_THRESHOLD = 20

# Higher threshold during commit flows. Detected by the presence of
# staged git files. Mechanical work (lint fixes, doc updates, file
# copies, re-staging) shouldn't burn through the budget as fast.
_ENGAGEMENT_COMMIT_THRESHOLD = 30

# Flow state: if actions are happening faster than this (seconds per action),
# the agent is in a rapid work loop and shouldn't be interrupted.
_FLOW_STATE_VELOCITY = 10.0  # seconds per action
_FLOW_STATE_THRESHOLD = 50  # very high ceiling when in flow


# Tools that consult stored knowledge (deep engagement)
_DEEP_TOOLS = {"ask", "recall", "briefing", "lessons", "active"}
# Tools that think but don't query knowledge (light engagement)
_LIGHT_TOOLS = {"context", "decide", "feel", "directives", "body", "compass"}

# After this many actions since last DEEP check-in, require deep engagement
_DEEP_ENGAGEMENT_THRESHOLD = 30


def mark_engaged(tool: str = "") -> None:
    """Mark that the OS was used for thinking this session.

    Called when a thinking tool is used. Resets the code-action counter.
    Tracks engagement DEPTH — light tools (context, decide, feel) satisfy
    the basic gate, but deep tools (ask, recall) are required periodically
    to ensure the agent actually consults stored knowledge, not just
    runs the minimum command to clear the gate.
    """
    path = _ensure_hud_dir() / ".session_engaged"

    # Preserve deep_actions_since across light engagements
    existing: dict[str, Any] = {}
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(existing, dict):
                existing = {}
        except (json.JSONDecodeError, OSError):
            existing = {}

    is_deep = tool.lower() in _DEEP_TOOLS if tool else False

    # Decay the counter instead of resetting to 0.
    # A single quick `divineos ask` shouldn't buy unlimited code actions.
    # Light tools halve the counter. Deep tools reset it fully.
    old_code = existing.get("code_actions_since", 0)
    old_deep = existing.get("deep_actions_since", 0)

    marker = {
        "engaged_at": time.time(),
        "code_actions_since": 0 if is_deep else max(0, old_code // 2),
        "engagement_depth": "deep" if is_deep else "light",
        "last_tool": tool,
        "deep_actions_since": 0 if is_deep else old_deep,
    }
    path.write_text(json.dumps(marker), encoding="utf-8")


def record_code_action() -> None:
    """Record that a code-changing action (Edit/Write) occurred.

    Only called for actual writes — not Bash reads, not file exploration.
    Reading IS thinking. The gate exists to prevent blind editing without
    reflection, not to punish looking at the codebase.

    Increments both counters:
    - code_actions_since: actions since last ANY thinking command (light gate)
    - deep_actions_since: actions since last DEEP thinking command (deep gate)

    When code_actions_since exceeds the light threshold, any thinking command
    clears it. When deep_actions_since exceeds _DEEP_ENGAGEMENT_THRESHOLD,
    only ask/recall/briefing will clear it — context/decide/feel won't be enough.
    """
    path = _ensure_hud_dir() / ".session_engaged"
    if not path.exists():
        return
    try:
        marker = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(marker, dict):
            marker = {"engaged_at": float(marker), "code_actions_since": 0}
        marker["code_actions_since"] = marker.get("code_actions_since", 0) + 1
        marker["deep_actions_since"] = marker.get("deep_actions_since", 0) + 1
        # compass_actions_since tracks code actions since the last
        # `divineos compass-ops observe` call. Reset by that CLI command;
        # read by the compass-staleness gate. See ChatGPT audit
        # claim-a7370b — structural enforcement of periodic compass use.
        marker["compass_actions_since"] = marker.get("compass_actions_since", 0) + 1
        marker["last_action_at"] = time.time()
        path.write_text(json.dumps(marker), encoding="utf-8")
    except (json.JSONDecodeError, OSError) as e:
        logger.debug("Engagement marker update failed: %s", e)


def reset_compass_actions_counter() -> None:
    """Reset `compass_actions_since` to 0. Called by compass-ops observe.

    Structural counterpart to `update_engagement_on_action`: observation
    discharges the pending debt of code actions, same way `learn` clears
    the correction marker.
    """
    path = _ensure_hud_dir() / ".session_engaged"
    if not path.exists():
        # No engagement marker — observation still counts; the counter
        # will start from 0 when the marker is created. Nothing to do.
        return
    try:
        marker = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(marker, dict):
            return
        marker["compass_actions_since"] = 0
        marker["last_compass_obs_at"] = time.time()
        path.write_text(json.dumps(marker), encoding="utf-8")
    except (json.JSONDecodeError, OSError) as e:
        logger.debug("Compass counter reset failed: %s", e)


# Threshold for the compass-staleness gate: after this many code actions
# without a compass observation, the gate blocks non-bypass tools until
# `divineos compass-ops observe` is run. 30 sits at the deep-engagement
# tier — low enough to catch real drift, high enough to avoid churn.
_COMPASS_STALENESS_THRESHOLD = 30


def compass_staleness_status() -> dict[str, Any]:
    """Return compass-staleness state for the gate.

    Returns dict with:
      - stale: bool (True if threshold exceeded)
      - actions_since: int (code actions since last observation)
      - threshold: int (current threshold for comparison)
    """
    path = _ensure_hud_dir() / ".session_engaged"
    if not path.exists():
        return {"stale": False, "actions_since": 0, "threshold": _COMPASS_STALENESS_THRESHOLD}
    try:
        marker = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"stale": False, "actions_since": 0, "threshold": _COMPASS_STALENESS_THRESHOLD}
    if not isinstance(marker, dict):
        return {"stale": False, "actions_since": 0, "threshold": _COMPASS_STALENESS_THRESHOLD}
    actions = marker.get("compass_actions_since", 0)
    return {
        "stale": actions >= _COMPASS_STALENESS_THRESHOLD,
        "actions_since": actions,
        "threshold": _COMPASS_STALENESS_THRESHOLD,
    }


def _active_threshold() -> int:
    """Return the engagement threshold, adapting to context.

    Three tiers:
    1. Flow state (50): rapid action velocity detected — don't interrupt
    2. Commit flow (30): staged git files — mechanical work cycle
    3. Base (15): normal work — periodic check-in needed

    Flow state is detected by measuring seconds-per-action from the
    engagement marker. If actions are coming faster than 10s apart,
    the agent is in a tight work loop and interruption destroys momentum.
    """
    # Check flow state first (highest priority)
    if _is_flow_state():
        return _FLOW_STATE_THRESHOLD

    # Check commit flow
    try:
        import subprocess

        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            capture_output=True,
            timeout=2,
        )
        # Exit code 1 means there ARE staged changes -> commit flow
        if result.returncode == 1:
            return _ENGAGEMENT_COMMIT_THRESHOLD
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    return _ENGAGEMENT_DECAY_THRESHOLD


def _is_flow_state() -> bool:
    """Detect if the agent is in a high-velocity work loop.

    Reads the engagement marker to check action velocity. If the agent
    has done 5+ actions AND the average time between actions is under
    _FLOW_STATE_VELOCITY seconds, we're in flow state.

    Flow state and drift are mutually inhibiting: if drift signals are
    elevated (lesson regressions, low recent grades), flow state does NOT
    trigger regardless of velocity. Safety signal gets priority over
    convenience signal. (Council round 4 — Dekker/Beer convergence.)
    """
    path = _get_hud_dir() / ".session_engaged"
    if not path.exists():
        return False
    try:
        marker = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(marker, dict):
            return False

        actions = marker.get("code_actions_since", 0)
        if actions < 5:
            return False  # need enough actions to detect a pattern

        engaged_at = marker.get("engaged_at", 0)
        last_action = marker.get("last_action_at", 0)
        if engaged_at <= 0 or last_action <= 0:
            return False

        elapsed = last_action - engaged_at
        if elapsed <= 0:
            return False

        velocity = elapsed / actions  # seconds per action
        if velocity >= _FLOW_STATE_VELOCITY:
            return False

        # Drift inhibits flow: check if recent session health is poor
        # or lesson regressions are active. If so, don't loosen the gate.
        if _drift_signals_elevated():
            return False

        return True
    except (json.JSONDecodeError, OSError):
        return False


def _drift_signals_elevated() -> bool:
    """Check if drift indicators suggest the gate should stay tight.

    Returns True if any of:
    - Last session grade was D or F
    - Active lessons have regressed 2+ times
    """
    try:
        # Check last session grade from handoff
        handoff_path = _get_hud_dir() / "handoff_note.json"
        if handoff_path.exists():
            ho = json.loads(handoff_path.read_text(encoding="utf-8"))
            grade = (ho.get("context_snapshot") or {}).get("session_grade", "")
            if grade in ("D", "F"):
                return True

        # Check for regressing lessons
        from divineos.core.knowledge import get_lessons

        active = get_lessons(status="active")
        regressed = sum(1 for lesson in active if lesson.get("regressions", 0) >= 2)
        if regressed >= 2:
            return True
    except (ImportError, OSError, json.JSONDecodeError, sqlite3.OperationalError):
        pass  # If we can't check, don't block flow — fail open here
    return False


def is_engaged() -> bool:
    """Check if the OS has been engaged recently enough.

    Two tiers:
    1. Light gate: any thinking command clears it (threshold ~15 actions)
    2. Deep gate: only ask/recall/briefing clear it (threshold ~30 actions)

    The deep gate ensures the agent actually consults stored knowledge
    periodically, not just runs context/decide to clear the light gate.
    """
    path = _get_hud_dir() / ".session_engaged"
    if not path.exists():
        return False
    try:
        marker = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(marker, dict):
            return True
        code_actions = marker.get("code_actions_since", 0)
        deep_actions = marker.get("deep_actions_since", 0)

        # Light gate — any thinking command clears
        if code_actions >= _active_threshold():
            return False

        # Deep gate — only ask/recall/briefing clear
        if deep_actions >= _DEEP_ENGAGEMENT_THRESHOLD:
            return False

        return True
    except (json.JSONDecodeError, OSError):
        return path.exists()


def engagement_status() -> dict[str, Any]:
    """Return detailed engagement status for HUD display.

    The 'state' field distinguishes WHY engagement is missing/expired so the
    blocking message can be specific:
      - "fresh"       : session started but no thinking command run yet
      - "drift"       : light gate exceeded (need any thinking command)
      - "deep_drift"  : deep gate exceeded (need ask/recall/briefing)
      - "engaged"     : currently engaged
    """
    threshold = _active_threshold()
    path = _get_hud_dir() / ".session_engaged"
    if not path.exists():
        return {
            "engaged": False,
            "state": "fresh",
            "code_actions_since": 0,
            "threshold": threshold,
            "remaining": 0,
        }
    try:
        marker = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(marker, dict):
            return {
                "engaged": True,
                "state": "engaged",
                "code_actions_since": 0,
                "threshold": threshold,
                "remaining": threshold,
                "deep_actions_since": 0,
                "deep_threshold": _DEEP_ENGAGEMENT_THRESHOLD,
                "needs_deep": False,
            }
        code_actions = marker.get("code_actions_since", 0)
        deep_actions = marker.get("deep_actions_since", 0)
        remaining = max(0, threshold - code_actions)
        needs_deep = deep_actions >= _DEEP_ENGAGEMENT_THRESHOLD
        engaged = code_actions < threshold and not needs_deep
        if engaged:
            state = "engaged"
        elif needs_deep:
            state = "deep_drift"
        else:
            state = "drift"
        return {
            "engaged": engaged,
            "state": state,
            "code_actions_since": code_actions,
            "threshold": threshold,
            "remaining": remaining,
            "deep_actions_since": deep_actions,
            "deep_threshold": _DEEP_ENGAGEMENT_THRESHOLD,
            "needs_deep": needs_deep,
        }
    except (json.JSONDecodeError, OSError):
        return {
            "engaged": True,
            "state": "engaged",
            "code_actions_since": 0,
            "threshold": threshold,
            "remaining": threshold,
            "deep_actions_since": 0,
            "deep_threshold": _DEEP_ENGAGEMENT_THRESHOLD,
            "needs_deep": False,
        }


def clear_engagement() -> None:
    """Clear the engagement marker (called at session end)."""
    path = _get_hud_dir() / ".session_engaged"
    if path.exists():
        path.unlink()


def mark_briefing_loaded() -> None:
    """Mark that the briefing was loaded, with timestamp and activity counter.

    Separate from general engagement — the briefing is the specific gate.
    Without it, the session grade takes a structural penalty.
    The marker expires after too much activity (context drift).

    Also logs a BRIEFING_LOADED event to the ledger so the progress
    dashboard can measure briefing compliance across sessions.
    """
    hud_dir = _ensure_hud_dir()
    now = time.time()
    tool_calls = _count_session_tool_calls()
    marker = {
        "loaded_at": now,
        "tool_calls_at_load": tool_calls,
    }
    (hud_dir / ".briefing_loaded").write_text(json.dumps(marker), encoding="utf-8")

    # Log to ledger for cross-session tracking
    try:
        from divineos.core.ledger import log_event

        log_event(
            "BRIEFING_LOADED",
            "system",
            {"loaded_at": now, "tool_calls_at_load": tool_calls},
            validate=False,
        )
    except _HH_ERRORS:
        pass  # ledger not initialized yet — marker file is enough

    # Reset session health — each session starts fresh.
    # Without this, the HUD shows stale grade/corrections from the prior session.
    health_path = hud_dir / "session_health.json"
    if health_path.exists():
        health_path.unlink()


# After this many tool calls since last briefing load, the context is stale.
# Was 150 — too low for productive sessions (a single audit fix pass can be
# 200+ tool calls).  400 means roughly "one full context window of work."
_BRIEFING_STALENESS_THRESHOLD = 400

# Time-based TTL: briefing stays valid for 4 hours regardless of tool calls.
# Was 2 hours — but productive sessions can easily run 3+ hours.
_BRIEFING_TTL_SECONDS = 14400


def was_briefing_loaded() -> bool:
    """Check if the briefing was loaded AND is still fresh.

    Returns False if:
    - Briefing was never loaded
    - More than 4 hours have passed since loading (time-based TTL)
    - More than 150 tool calls have happened since loading (activity drift)

    The time check prevents false blocks after context compaction,
    which resets the tool call counter but doesn't invalidate the briefing.
    """
    path = _get_hud_dir() / ".briefing_loaded"
    if not path.exists():
        return False
    try:
        marker = json.loads(path.read_text(encoding="utf-8"))
        loaded_at = marker.get("loaded_at", 0)

        # Time-based check: valid if loaded within TTL window
        age = time.time() - loaded_at
        if age > _BRIEFING_TTL_SECONDS:
            return False

        # Activity-based check: valid if under tool call threshold
        calls_at_load = marker.get("tool_calls_at_load", 0)
        calls_now = _count_session_tool_calls()
        # After compaction, calls_now may be less than calls_at_load.
        # In that case, trust the time-based check (already passed above).
        if calls_now < calls_at_load:
            return True
        return bool((calls_now - calls_at_load) < _BRIEFING_STALENESS_THRESHOLD)
    except (json.JSONDecodeError, OSError):
        return path.exists()


def briefing_staleness() -> dict[str, Any]:
    """Return how stale the briefing context is.

    Returns dict with 'loaded', 'stale', 'calls_since', 'threshold',
    'age_seconds', 'ttl_seconds', 'ttl_expired'.
    """
    base: dict[str, Any] = {
        "loaded": False,
        "stale": True,
        "calls_since": 0,
        "threshold": _BRIEFING_STALENESS_THRESHOLD,
        "age_seconds": 0,
        "ttl_seconds": _BRIEFING_TTL_SECONDS,
        "ttl_expired": False,
    }
    path = _get_hud_dir() / ".briefing_loaded"
    if not path.exists():
        return base
    try:
        marker = json.loads(path.read_text(encoding="utf-8"))
        loaded_at = marker.get("loaded_at", 0)
        age = time.time() - loaded_at
        ttl_expired = age > _BRIEFING_TTL_SECONDS

        calls_at_load = marker.get("tool_calls_at_load", 0)
        calls_now = _count_session_tool_calls()
        delta = max(0, calls_now - calls_at_load)
        activity_stale = delta >= _BRIEFING_STALENESS_THRESHOLD

        return {
            "loaded": True,
            "stale": ttl_expired or activity_stale,
            "calls_since": delta,
            "threshold": _BRIEFING_STALENESS_THRESHOLD,
            "age_seconds": int(age),
            "ttl_seconds": _BRIEFING_TTL_SECONDS,
            "ttl_expired": ttl_expired,
        }
    except (json.JSONDecodeError, OSError):
        base["loaded"] = True
        base["stale"] = False
        return base


# clear_briefing_marker() removed 2026-04-20 system audit. The function
# was never called anywhere — docstring claimed "called at session end"
# but no call site existed. Dead code. If session-end clearing of the
# briefing marker becomes needed, add it to .claude/hooks/load-briefing.sh
# alongside the other SessionStart resets (clear_engagement, clear_session_plan,
# reset_state) — same semantic home.


def _count_session_tool_calls() -> int:
    """Count tool calls in the current session from the ledger."""
    try:
        counts = count_events()
        return int(counts.get("by_type", {}).get("TOOL_CALL", 0))
    except _HH_ERRORS:
        return 0


# ─── Preflight Check ────────────────────────────────────────────────


def preflight_check() -> dict[str, Any]:
    """Check session readiness before work begins.

    Returns a dict with:
        ready: bool — True if all gates pass
        briefing_loaded: bool
        engaged: bool
        has_handoff: bool — previous session left a handoff note
        checks: list of {name, passed, detail}
    """
    checks: list[dict[str, Any]] = []

    # 1. Briefing loaded?
    briefing_ok = was_briefing_loaded()
    checks.append(
        {
            "name": "briefing",
            "passed": briefing_ok,
            "detail": "Briefing loaded and fresh"
            if briefing_ok
            else "Briefing not loaded — run: divineos briefing",
        }
    )

    # 2. Engaged with thinking tools? (periodic — decays after code actions)
    eng_status = engagement_status()
    engaged = eng_status["engaged"]
    if engaged:
        remaining = eng_status["remaining"]
        eng_detail = f"OS engaged ({remaining} code actions before next check-in needed)"
    else:
        actions = eng_status["code_actions_since"]
        eng_detail = (
            f"Engagement expired — {actions} code actions without OS consultation. "
            "Run: divineos ask <topic> or divineos recall"
        )
    checks.append(
        {
            "name": "engagement",
            "passed": engaged,
            "detail": eng_detail,
        }
    )

    # 3. Handoff note from previous session?
    handoff = load_handoff_note()
    has_handoff = handoff is not None and bool(handoff.get("summary"))
    checks.append(
        {
            "name": "handoff",
            "passed": has_handoff,
            "detail": "Handoff note available from last session"
            if has_handoff
            else "No handoff note found (first session or cleared)",
        }
    )

    # 4. Active goals set?
    try:
        goals_path = _ensure_hud_dir() / "active_goals.json"
        if goals_path.exists():
            goals = json.loads(goals_path.read_text(encoding="utf-8"))
            active_goals = [g for g in goals if g.get("status") != "done"]
        else:
            active_goals = []
    except (json.JSONDecodeError, OSError):
        active_goals = []

    has_goals = len(active_goals) > 0
    checks.append(
        {
            "name": "goals",
            "passed": has_goals,
            "detail": f"{len(active_goals)} active goal(s)"
            if has_goals
            else 'No active goals — consider: divineos goal "..."',
        }
    )

    # 5. Session-fresh goal? (not just old goals from prior sessions)
    try:
        fresh_goal = has_session_fresh_goal()
    except (sqlite3.OperationalError, OSError, KeyError, TypeError) as exc:
        logger.debug(f"Session fresh goal check failed, defaulting to True: {exc}")
        fresh_goal = True  # don't block if function unavailable
    checks.append(
        {
            "name": "session_goal",
            "passed": fresh_goal,
            "detail": "Goal set for this session"
            if fresh_goal
            else 'No goal for THIS session — run: divineos goal add "..."',
        }
    )

    # 6. Compass integrity — moral foundations haven't been tampered with
    try:
        from divineos.core.moral_compass import verify_compass_integrity

        verify_compass_integrity()
        compass_ok = True
        compass_detail = "Moral compass spectrums intact"
    except RuntimeError as exc:
        compass_ok = False
        compass_detail = str(exc)
    except (ImportError, OSError) as exc:
        compass_ok = True  # don't block if module unavailable
        compass_detail = f"Compass check skipped: {exc}"
    checks.append(
        {
            "name": "compass_integrity",
            "passed": compass_ok,
            "detail": compass_detail,
        }
    )

    # Ready = briefing loaded (the hard requirement)
    ready = briefing_ok
    return {
        "ready": ready,
        "briefing_loaded": briefing_ok,
        "engaged": engaged,
        "has_handoff": has_handoff,
        "checks": checks,
    }


# ─── Goal Extraction ─────────────────────────────────────────────────

# Patterns that signal a user is asking for something to be done.
# Kept simple — false negatives are fine, false positives waste attention.
_GOAL_PATTERNS = [
    r"(?i)^(?:can you|could you|please|i want you to|i need you to|go ahead and)\s+(.+)",
    r"(?i)^(?:let'?s|lets)\s+(.+)",
    r"(?i)^(?:yes,?\s+)?(?:wire|build|add|create|fix|implement|write|make|set up|tackle)\s+(.+)",
]

_GOAL_REGEXES = [re.compile(p) for p in _GOAL_PATTERNS]


def extract_goals_from_messages(messages: list[str], max_goals: int = 5) -> list[dict[str, str]]:
    """Extract goal-like statements from user messages.

    Looks for imperative/request patterns. Returns a list of
    {"text": "...", "original_words": "..."} dicts.
    """
    goals: list[dict[str, str]] = []

    for msg in messages:
        # Skip very short messages (affirmations, greetings)
        if len(msg.split()) < 4:
            continue
        # Skip very long messages (explanations, not requests)
        if len(msg.split()) > 50:
            continue

        for regex in _GOAL_REGEXES:
            match = regex.match(msg.strip())
            if match:
                goal_text = match.group(1).strip().rstrip(".!,")
                if not goal_text:
                    continue
                # Filter out conversational noise that matches goal patterns
                # but isn't a real project goal
                gt_lower = goal_text.lower()
                if _is_conversational_goal(gt_lower):
                    continue
                goal_text = goal_text[0].upper() + goal_text[1:]
                goals.append(
                    {
                        "text": goal_text,
                        "original_words": msg.strip()[:200],
                    }
                )
                break

        if len(goals) >= max_goals:
            break

    return goals


def _is_conversational_goal(text: str) -> bool:
    """Check if a goal-like statement is actually just conversation."""
    # Pure action phrases without substance
    noise_starters = (
        "do it",
        "do this",
        "do that",
        "do both",
        "go",
        "keep going",
        "keep looking",
        "proceed",
        "continue",
        "start",
        "try it",
        "try that",
        "see",
        "check",
        "work on",
    )
    for starter in noise_starters:
        if text.startswith(starter) and len(text.split()) < 8:
            return True

    # Generic meta-instructions — these direct how to work, not what to build
    meta = (
        "make a plan",
        "make sure",
        "do this correctly",
        "commit and push",
        "merge and",
        "push and",
        "fix the root cause",
        "fix the issues",
        "fix it",
    )
    for m in meta:
        if text.startswith(m):
            return True

    # Emoticon-heavy or very short — chat, not goals
    stripped = text.replace(":)", "").replace(":D", "").replace("lol", "").strip()
    if len(stripped.split()) < 3:
        return True

    return False
