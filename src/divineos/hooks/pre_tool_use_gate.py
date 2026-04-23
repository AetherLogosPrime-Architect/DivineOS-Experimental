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
        # Correction repetition is always loggable in the moment
        "correction",
        "corrections",
        # Cadence-gate bypasses — required to unstick the overdue state
        "audit",
        "prereg",
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


def _make_deny(reason: str) -> dict[str, Any]:
    """Package a deny decision in the Claude Code hook response format."""
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def _check_gates() -> dict[str, Any] | None:
    """Run all gates in order. Return first deny decision, or None if all pass.

    Import-heavy work is guarded — if a module can't be imported (e.g. during
    first-run bootstrap), that gate is skipped rather than crashing the hook.
    Fail-open is the correct disposition for a gate whose machinery is broken.
    """
    # Gate 1: briefing loaded
    try:
        from divineos.core.hud_handoff import was_briefing_loaded

        if not was_briefing_loaded():
            return _make_deny("BLOCKED: Briefing not loaded. Run: divineos briefing")
    except (ImportError, OSError, AttributeError):
        pass  # fail open — gate machinery unavailable

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
    except (ImportError, OSError, AttributeError):
        pass

    # Gate 1.45: hedge-unresolved. Closes the hedge-claim enforcement gap —
    # when my last assistant output had >= 2 hedge flags (detected by the
    # Stop hook), a claim must be filed before further tool use. Hedge
    # without claim is floating doubt; claim discharges it into the
    # investigation queue.
    try:
        from divineos.core.hedge_marker import format_gate_message as _hm_msg
        from divineos.core.hedge_marker import read_marker as _hm_read

        h = _hm_read()
        if h is not None:
            return _make_deny(_hm_msg(h))
    except (ImportError, OSError, AttributeError):
        pass

    # Gate 1.5: correction detected but not logged.
    # Closes ChatGPT audit claim-964493 (theater-learning bypass) by making
    # "log the correction" a structural requirement, not intent. The
    # UserPromptSubmit hook (detect-correction.sh) sets the marker when a
    # user message matches CORRECTION_PATTERNS; `divineos learn` and
    # `divineos correction` clear it. Fail open on missing machinery.
    try:
        from divineos.core.correction_marker import format_gate_message, read_marker

        marker = read_marker()
        if marker is not None:
            return _make_deny(format_gate_message(marker))
    except (ImportError, OSError, AttributeError):
        pass

    # Gate 2: session-fresh goal
    try:
        from divineos.core.hud_state import has_session_fresh_goal

        if not has_session_fresh_goal():
            return _make_deny(
                "BLOCKED: No goal set for this session. "
                'Run: divineos goal add "what you are working on"'
            )
    except (ImportError, OSError, AttributeError):
        pass

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
    except (ImportError, OSError, AttributeError):
        pass

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
    except (ImportError, OSError, AttributeError):
        pass

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

    decision = _check_gates()
    if decision is not None:
        json.dump(decision, sys.stdout)

    return 0


if __name__ == "__main__":
    sys.exit(main())
