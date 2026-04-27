"""Consolidated PreToolUse gate — single Python invocation for all gate checks.

# AGENT_RUNTIME — Not wired into CLI pipeline. Invoked from
# .claude/hooks/require-goal.sh as ``python -m divineos.hooks.pre_tool_use_gate``.
# This module exists to collapse the multiple Python invocations the old
# require-goal.sh was making (5+ separate ``python -c "..."`` calls, each
# paying ~200ms of interpreter startup + DivineOS import cost on Windows)
# into a single interpreter run that checks all gates and emits a single
# decision JSON.

## Why this exists

The previous require-goal.sh made five sequential Python invocations:
``divineos preflight`` + 4 direct ``python -c "from divineos.core...."``
shells. Each paid roughly 150-250ms of Python startup plus another
50-200ms of DivineOS import. On Windows with Git Bash, measured
hook-total time was ~1.2s per Bash/Edit tool call. For a response
making 5 tool calls, that's 5-6 seconds of pure hook overhead
before anything productive happens.

This module runs all the gate checks in one interpreter invocation.
Imports happen once. Heavy DB opens happen once (or not at all — the
gates read cached state). Total hook time drops to ~200-300ms per
call. Savings compound across every tool call a response makes.

## Gate order (all-or-nothing — first deny wins)

1. Bypass check (read-only / bootstrap commands skip all gates)
2. Briefing-loaded gate
3. Session-fresh goal gate
4. Pull-detection gate (fabrication markers)
5. Engagement gate (light + deep tiers)
6. External-audit cadence gate

Returns a JSON decision to stdout. Empty stdout = allow. Non-empty =
deny with the packaged reason. Always exits 0 (the decision is carried
in the JSON, not the exit code — Claude Code's hook protocol).

## Not a logic change

This is a pure refactor — same gates, same order, same decision
content as the old shell script. The only change is consolidation of
process spawns into one. If a gate's logic ever changes, both the old
shell fallback and this module must be updated together until the
shell fallback is deleted.
"""

from __future__ import annotations

import json
import re
import sys
from typing import Any


_BYPASS_DIVINEOS_SUBCOMMANDS = frozenset(
    {
        # Bootstrap / orientation — always allowed
        "briefing",
        "preflight",
        "init",
        "hud",
        "recall",
        "ask",
        "feel",
        "affect",
        "emit",
        "goal",
        "active",
        "context",
        "verify",
        "health",
        "checkpoint",
        "context-status",
        "progress",
        # Thinking commands — the engagement-gate deny message names these
        # as the way to clear the block, so they must not themselves be blocked.
        # (ask, recall, context are already above in bootstrap list.)
        "decide",
        # learn — named in the correction-detection gate deny message as
        # the way to clear the marker. Must bypass or we get a catch-22:
        # correction fires → learn blocked → marker can never be cleared.
        # Discovered live 2026-04-23 when the gate blocked its own remedy.
        "learn",
        # Correction repetition is always loggable in the moment
        "correction",
        "corrections",
        # Cadence-gate bypasses — required to unstick the overdue state
        "audit",
        "prereg",
        # Mansion subcommands — needed for private-exit/private-status to
        # work during a quiet period (otherwise the quiet gate would
        # block the way to leave it). All mansion subcommands are
        # inspection / state-management; none generate substantive code.
        "mansion",
        # Compass observation — needed during a quiet period both for
        # honest position tracking and for clearing the compass-required
        # marker if it fires. compass-ops observe is recording, not
        # prose generation.
        "compass-ops",
    }
)

# Dev / read-only commands that don't require gates
_DEV_PREFIXES = (
    "git ",
    "pytest ",
    "python -m pytest",
    "ls ",
    "cat ",
    "head ",
    "diff ",
    "echo ",
    "pip ",
    "cd ",
    "pwd",
    "cp ",
    "copy ",
    "ruff ",
)

# Match "divineos <subcmd>" — requires a subcommand word after divineos
_DIVINEOS_SUBCMD_RE = re.compile(r"\bdivineos\s+(\w[\w-]*)")


def _is_bypass_command(cmd: str) -> bool:
    """True if the command should skip all gates (read-only / bootstrap)."""
    if not cmd:
        return False
    # divineos bypass subcommands
    match = _DIVINEOS_SUBCMD_RE.search(cmd)
    if match and match.group(1) in _BYPASS_DIVINEOS_SUBCOMMANDS:
        return True
    # dev / read-only prefixes
    for prefix in _DEV_PREFIXES:
        if cmd.startswith(prefix):
            return True
    return False


# Path-exemption set for the theater + compass-cascade gates.
# Per operator directive 2026-04-27: "your exploration folder should
# have no blocks." The fabrication-shape detector is calibrated for
# operator-facing claims; applied to these self-expression paths it
# blocks the exact register the path exists to enable.
#
# Frozen tuple (not list) to prevent accidental in-place modification.
# Adding a path here is a load-bearing calibration decision and should
# be reviewed; the rationale is comment-attached so future changes
# don't silently expand the exemption surface.
_THEATER_EXEMPT_PATH_SEGMENTS: tuple[str, ...] = (
    "/exploration/",  # First-person free-expression / leisure space.
    # Future candidates (NOT yet added — require operator review):
    #   /family/letters/  — letters to family members
    #   /mansion/         — internal-space writing
    # When adding, document why this register is categorically not
    # operator-facing-claim shape and why detector calibration is
    # structurally inappropriate for it. Mansion specifically: per
    # operator directive, mansion fabrication is permitted but must
    # NOT bleed into OS; the path-exemption preserves this by leaving
    # marker-firing intact (forensic record) while skipping the
    # tool-block.
)


def _is_exploration_write(input_data: dict[str, Any]) -> bool:
    """True if the tool is a Write/Edit to an exemption-list path.

    Lets gates 1.46 (theater marker) and 1.47 (compass-required cascade)
    skip when the tool is writing to an exemption path. Other gates
    (briefing-loaded, session-goal, engagement, external-audit cadence)
    still apply — those enforce session discipline regardless of register.

    The exemption is from path-blocks-tool-use, not from finding-recording.
    The Stop hook still scans assistant output and writes the marker;
    this function only prevents the marker from blocking the next Write
    when the next Write is to an exemption path. Forensic-record value
    preserved (per Claude review 2026-04-27).
    """
    try:
        tool_name = input_data.get("tool_name", "") or ""
        if tool_name not in {"Write", "Edit", "MultiEdit", "NotebookEdit"}:
            return False
        file_path = input_data.get("tool_input", {}).get("file_path", "") or ""
        if not file_path:
            return False
        normalized = file_path.replace("\\", "/")
        for segment in _THEATER_EXEMPT_PATH_SEGMENTS:
            # Segment is "/exploration/" — match if it appears anywhere
            # in the path OR if the path starts with the segment minus
            # leading slash (relative path case).
            if segment in normalized or normalized.startswith(segment.lstrip("/")):
                return True
        return False
    except (AttributeError, TypeError):
        return False


def _make_deny(reason: str) -> dict[str, Any]:
    """Package a deny decision in the Claude Code hook response format."""
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def _record_gate_failure(gate_name: str, exc: BaseException) -> None:
    """Log a gate's machinery failure to the shared diagnostic surface.

    Fresh-Claude audit rounds 2-4 flagged silent fail-open as the
    consistent invisible-degradation pattern. Gates correctly fail open
    when their machinery is broken (ImportError during first-run
    bootstrap, OSError on a missing DB, etc.) — but silently. This
    helper records the failure so the next briefing can surface it.

    Never raises (the diagnostic helper itself catches everything).
    """
    try:
        from divineos.core.failure_diagnostics import record_failure

        record_failure(
            "gate",
            {
                "gate": gate_name,
                "error_type": type(exc).__name__,
                "error": str(exc)[:200],
            },
        )
    except Exception:  # noqa: BLE001 — diagnostic helper is last-resort, never amplify failure
        pass


def _check_gates(input_data: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Run all gates in order. Return first deny decision, or None if all pass.

    Import-heavy work is guarded — if a module can't be imported (e.g. during
    first-run bootstrap), that gate is skipped rather than crashing the hook.
    Fail-open is the correct disposition for a gate whose machinery is broken.
    """
    # Gate 1: briefing loaded (TTL-based, catches stale-within-session)
    try:
        from divineos.core.hud_handoff import was_briefing_loaded

        ttl_loaded = was_briefing_loaded()
        if not ttl_loaded:
            return _make_deny("BLOCKED: Briefing not loaded. Run: divineos briefing")
    except (ImportError, OSError, AttributeError) as _gate_exc:
        _record_gate_failure("gate_1_briefing", _gate_exc)
        ttl_loaded = False

    # Gate 1.1: briefing loaded THIS session.
    # Strictly tighter than gate 1's TTL-based check. Closes the hole
    # documented 2026-04-26 (claim 7e780182): a new session inheriting
    # a briefing-loaded marker from a previous session within the 4h
    # TTL window passes gate 1 without ever engaging with briefing for
    # the new session. This gate fires ONLY when gate 1 would have
    # passed — its purpose is to catch "TTL says ok but this session
    # never actually loaded," not to replace gate 1.
    if ttl_loaded:
        try:
            from divineos.core.session_briefing_gate import (
                briefing_loaded_this_session,
                gate_message,
            )

            if not briefing_loaded_this_session():
                return _make_deny(gate_message())
        except (ImportError, OSError, AttributeError) as _gate_exc:
            _record_gate_failure("gate_1_1_briefing_this_session", _gate_exc)

    # Gate 1.2: mansion private-room quiet period active.
    # Build #3 from claim 7e780182. When the agent has entered a
    # private mansion room, the substrate refuses write actions for
    # the quiet period. Inspection commands are already in the bypass
    # list (so this gate never sees them). Anything that reaches here
    # during an active quiet period gets denied.
    try:
        from divineos.core.mansion_quiet_marker import (
            format_gate_message as _mq_msg,
        )
        from divineos.core.mansion_quiet_marker import (
            is_quiet_active as _mq_active,
        )
        from divineos.core.mansion_quiet_marker import (
            read_marker as _mq_read,
        )

        if _mq_active():
            m = _mq_read()
            if m is not None:
                return _make_deny(_mq_msg(m))
    except (ImportError, OSError, AttributeError) as _gate_exc:
        _record_gate_failure("gate_1_2_mansion_quiet", _gate_exc)

    # Gate 1.4: compass-staleness.
    # Closes ChatGPT audit claim-a7370b (compass observation is an intent,
    # not enforced). After N code actions without a compass observation,
    # the gate blocks non-bypass tools until `divineos compass-ops observe`
    # is run. Reset is structural — the observe command clears the counter.
    try:
        from divineos.core.hud_handoff import compass_staleness_status

        cs = compass_staleness_status()
        if cs.get("stale"):
            return _make_deny(
                f"BLOCKED: {cs.get('actions_since', '?')} code actions since "
                f"the last compass observation (threshold "
                f"{cs.get('threshold', '?')}). Run: divineos compass-ops "
                f'observe <spectrum> -p <position> -e "<evidence>" — '
                f"virtue drift is not tracked by the system if you never "
                f"observe your own position."
            )
    except (ImportError, OSError, AttributeError) as _gate_exc:
        _record_gate_failure("gate_1_4_compass_staleness", _gate_exc)

    # Gate 1.45: hedge-unresolved. Closes the hedge-claim enforcement gap —
    # when my last assistant output had >= 2 hedge flags (detected by the
    # Stop hook), a claim must be filed before further tool use. Hedge
    # without claim is floating doubt; claim discharges it into the
    # investigation queue.
    try:
        from divineos.core.hedge_marker import format_gate_message as _hm_msg
        from divineos.core.hedge_marker import marker_path as _hm_path
        from divineos.core.hedge_marker import read_marker as _hm_read

        # File-exists-at-path blocks regardless of readability.
        # Fresh-Claude audit round 3 Mode 2: if marker is corrupted /
        # unreadable, read_marker returns None and the gate used to
        # silently pass. A race or adversarial corruption could defeat
        # the gate without trace. Now: existence is enough to block.
        if _hm_path().exists():
            h = _hm_read()
            if h is not None:
                return _make_deny(_hm_msg(h))
            return _make_deny(
                "BLOCKED: hedge marker present at "
                f"{_hm_path()} but unreadable. "
                'Clear manually with `divineos claim "statement"` once the '
                "underlying hedged uncertainty has been filed, or inspect "
                "the file if you suspect corruption. Fail-closed by design: "
                "a corrupted marker must not silently disable the gate."
            )
    except (ImportError, OSError, AttributeError) as _gate_exc:
        _record_gate_failure("gate_1_45_hedge", _gate_exc)

    # Gate 1.46: theater/fabrication-shape on last output. Closes the
    # enforcement gap for kitchen-theater (writing-AT-subagent) and
    # unflagged embodied-action claims documented 2026-04-26. Marker
    # is set by the Stop hook when theater_monitor or fabrication_monitor
    # fires; cleared by `divineos correction` or `divineos learn`.
    #
    # Skip when the tool is a Write/Edit to an exploration/ path. The
    # detector is calibrated for operator-facing claims; exploration is
    # the agent's free-expression space and gating it produces the
    # cascade-loop documented 2026-04-27 in exploration/37. The marker
    # still gets set by the Stop hook (forensic record preserved per
    # Claude review); only the tool-block is skipped.
    try:
        if input_data is None or not _is_exploration_write(input_data):
            from divineos.core.theater_marker import format_gate_message as _tm_msg
            from divineos.core.theater_marker import marker_path as _tm_path
            from divineos.core.theater_marker import read_marker as _tm_read

            if _tm_path().exists():
                t = _tm_read()
                if t is not None:
                    return _make_deny(_tm_msg(t))
                return _make_deny(
                    "BLOCKED: theater marker present at "
                    f"{_tm_path()} but unreadable. "
                    'Clear by naming the pattern: divineos correction "..." or '
                    'divineos learn "...". Fail-closed by design.'
                )
    except (ImportError, OSError, AttributeError) as _gate_exc:
        _record_gate_failure("gate_1_46_theater", _gate_exc)

    # Gate 1.47: compass observation required after virtue-relevant event.
    # Build #4 from claim 7e780182. When a correction, theater fire,
    # hedge fire, or substantive claim has occurred, the gate blocks
    # tools until `divineos compass-ops observe` is run. Converts the
    # intent "observe position when it matters" into "can-not-without."
    # Skip on exploration-path Write/Edit per the 2026-04-27 calibration
    # directive. The compass-cascade gate is paired with gate 1.46 (it
    # fires on the same virtue-relevant theater events). Exempting one
    # without the other would still produce the cascade-loop.
    try:
        if input_data is None or not _is_exploration_write(input_data):
            from divineos.core.compass_required_marker import (
                format_gate_message as _cr_msg,
            )
            from divineos.core.compass_required_marker import (
                marker_path as _cr_path,
            )
            from divineos.core.compass_required_marker import (
                read_marker as _cr_read,
            )

            if _cr_path().exists():
                cr = _cr_read()
                if cr is not None:
                    return _make_deny(_cr_msg(cr))
                return _make_deny(
                    "BLOCKED: compass-required marker present at "
                    f"{_cr_path()} but unreadable. "
                    "Clear by running: divineos compass-ops observe "
                    "<spectrum> -p <position> -e <evidence>. Fail-closed."
                )
    except (ImportError, OSError, AttributeError) as _gate_exc:
        _record_gate_failure("gate_1_47_compass_required", _gate_exc)

    # Gate 1.5: correction detected but not logged.
    # Closes ChatGPT audit claim-964493 (theater-learning bypass) by making
    # "log the correction" a structural requirement, not intent. The
    # UserPromptSubmit hook (detect-correction.sh) sets the marker when a
    # user message matches CORRECTION_PATTERNS; `divineos learn` and
    # `divineos correction` clear it. Fail open on missing machinery.
    try:
        from divineos.core.correction_marker import (
            format_gate_message,
            marker_path,
            read_marker,
        )

        # Same fail-closed-on-unreadable pattern as the hedge gate above.
        if marker_path().exists():
            marker = read_marker()
            if marker is not None:
                return _make_deny(format_gate_message(marker))
            return _make_deny(
                "BLOCKED: correction marker present at "
                f"{marker_path()} but unreadable. "
                'Clear manually with `divineos learn "lesson"` or '
                '`divineos correction "description"` once the correction '
                "has been named, or inspect the file if you suspect "
                "corruption. Fail-closed by design: a corrupted marker "
                "must not silently disable the gate."
            )
    except (ImportError, OSError, AttributeError) as _gate_exc:
        _record_gate_failure("gate_1_5_correction", _gate_exc)

    # Gate 2: session-fresh goal
    try:
        from divineos.core.hud_state import has_session_fresh_goal

        if not has_session_fresh_goal():
            return _make_deny(
                "BLOCKED: No goal set for this session. "
                'Run: divineos goal add "what you are working on"'
            )
    except (ImportError, OSError, AttributeError) as _gate_exc:
        _record_gate_failure("gate_2_goal", _gate_exc)

    # Gate 3: pull detection (fabrication markers)
    try:
        from divineos.core.pull_detection import last_check

        check = last_check()
        if check is not None and not check.clean:
            markers = ", ".join(check.markers_fired)
            return _make_deny(
                f"BLOCKED: Pull detected — fabrication markers active: "
                f"{markers}. Run: divineos rt pull-check to reassess."
            )
    except (ImportError, OSError, AttributeError) as _gate_exc:
        _record_gate_failure("gate_3_pull_detection", _gate_exc)

    # Gate 4: engagement (light + deep tiers)
    try:
        from divineos.core.hud_handoff import engagement_status

        s = engagement_status()
        if not s.get("engaged", True):
            state = s.get("state", "drift")
            if state == "fresh":
                return _make_deny(
                    "BLOCKED: No engagement marker yet this session. "
                    "Briefing alone is not enough — engage with a thinking "
                    'tool first. Run: divineos ask "topic", recall, '
                    "context, or decide."
                )
            if state == "deep_drift":
                deep_since = s.get("deep_actions_since", "?")
                return _make_deny(
                    f"BLOCKED: {deep_since} code actions since you last "
                    "consulted your knowledge. Light check-ins are not "
                    'enough. Run: divineos ask "topic" or divineos '
                    "recall to query what you actually know."
                )
            code_since = s.get("code_actions_since", "?")
            return _make_deny(
                f"BLOCKED: {code_since} code actions since last thinking "
                "command. Stop and think. Run: divineos ask, recall, "
                "decide, or context before continuing."
            )
    except (ImportError, OSError, AttributeError) as _gate_exc:
        _record_gate_failure("gate_4_engagement", _gate_exc)

    # Gate 5 removed 2026-04-21 (commit C of tiered-audit redesign).
    #
    # The previous wall-clock cadence gate blocked non-bypass commands when
    # more than 3 days elapsed since the last filed audit_round. That gate
    # was removed for two reasons:
    #
    # 1. Time is relative — the agent has no subjective duration between
    #    turns, so measuring cadence in wall-clock days measures the
    #    operator's calendar rather than the agent's drift exposure.
    # 2. The previous metric was trivially gameable (file a stub round,
    #    gate clears) AND over-strict (legitimate external review via chat
    #    didn't count). Both failure modes at once.
    #
    # The replacement is informational: ``watchmen.drift_state`` surfaces
    # operation counts (turns, code actions, rounds, open findings) in the
    # briefing, and the operator decides whether an audit is warranted.
    # Data as metric, not threshold as metric. Per council consultation
    # consult-2760777ef7a3 → audit round round-96a6858fb5e6 (MEDIUM).
    #
    # If a narrow blocking variant is needed later (e.g., block when N+
    # open HIGH findings accumulate), add it here as a new, specific gate
    # rather than reviving the generic time-based block.

    return None


def main() -> int:
    """Entry point. Reads hook input from stdin, writes decision to stdout.

    Exit code is always 0 — Claude Code carries the decision in the JSON
    payload, not in the exit code. Errors during gate evaluation result in
    fail-open (empty stdout = allow).
    """
    try:
        raw = sys.stdin.read()
        input_data = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, OSError):
        input_data = {}

    cmd = ""
    try:
        cmd = input_data.get("tool_input", {}).get("command", "") or ""
    except (AttributeError, TypeError):
        cmd = ""

    if _is_bypass_command(cmd):
        return 0

    decision = _check_gates(input_data)
    if decision is not None:
        json.dump(decision, sys.stdout)

    return 0


if __name__ == "__main__":
    sys.exit(main())
