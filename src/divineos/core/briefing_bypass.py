"""Briefing-gate bypass list — substrate-portable.

Per prereg-7bba8b123d42 (2026-06-24) and council walk (Carmack
scope-down): a single small module holding the bypass-prefix list +
segment-split + is_bypass helper, separate from the guardrail-listed
briefing_freshness.py.

Why split: the bypass-list and segment-split are genuinely portable
(any AI substrate calling DivineOS needs the same "let bootstrap
commands through" routing). The deny-message construction returned
to the bash hook because it produces Claude-Code-specific
hookSpecificOutput JSON, which other substrates have different
formats for.

This file is NOT on the guardrail list — it's the data-and-helper
layer, not the safety mechanism itself. The actual gate decision
still lives behind staleness_signal() in briefing_freshness.py.
"""

from __future__ import annotations

# Bypass-prefix list — bootstrap commands and read-only ops that
# MUST work for the briefing-load loop itself to function. Without
# these, the only channel that clears the stale-briefing gate
# (`divineos briefing`) would itself be gated. Catch-22.
#
# Listed as PREFIXES — any segment of a chained command starting
# with any of these is allowed.
BYPASS_PREFIXES: tuple[str, ...] = (
    "divineos briefing",
    "divineos briefing-id",  # recall-challenge cure — must run while gated
    "divineos init",
    "divineos preflight",
    "divineos recall",
    "divineos ask",
    "divineos hud",
    "divineos context",
    "divineos goal",
)

# Shell separators that compose multiple commands into one bash
# string. `cd <path> && divineos briefing` is the common case —
# the second segment is what we want to bypass-check.
_CHAIN_SEPARATORS: tuple[str, ...] = ("&&", ";", "|", "\n")


def command_segments(command: str) -> list[str]:
    """Split a shell command into its discrete segments.

    Returns trimmed non-empty segments. A startswith() on the whole
    command never matches `cd X && divineos briefing` because the
    first chars are `cd `, not `divineos`. Split-and-check covers it.
    """
    parts: list[str] = [command]
    for sep in _CHAIN_SEPARATORS:
        nxt: list[str] = []
        for p in parts:
            nxt.extend(p.split(sep))
        parts = nxt
    return [s.strip() for s in parts if s.strip()]


def is_bypass_bash_command(command: str) -> bool:
    """True if any segment of `command` starts with a BYPASS_PREFIX.

    Used by the require-briefing hook (and any other substrate's
    equivalent) to decide whether a Bash tool call should be allowed
    through even when briefing is stale.

    Wired 2026-06-29 per Perplexity audit Gap #6: when a bypass fires,
    record it via bypass_telemetry.record_bypass so the rate is
    queryable. Previously bypasses were invisible — env-var bypasses
    were tracked but command-prefix bypasses (like `divineos briefing`
    passing through the briefing-gate) were not. record_bypass dedups
    on (env_var, session, day), so the same command bypassing
    repeatedly within a day collapses to one event. Fail-open: any
    telemetry error swallows silently so it cannot break the gate.
    """
    for seg in command_segments(command):
        for prefix in BYPASS_PREFIXES:
            if seg.startswith(prefix):
                try:
                    from divineos.core.bypass_telemetry import record_bypass

                    record_bypass(
                        gate_name="briefing",
                        env_var=f"cmd:{prefix}",
                        reason="command-prefix bypass via BYPASS_PREFIXES",
                    )
                except Exception:
                    pass  # telemetry failure must not break the gate decision
                return True
    return False
