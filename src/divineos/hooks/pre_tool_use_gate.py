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

# Module-level guardrail marker — Aletheia Finding 48 class-fix
# 2026-05-14. CI test (tests/test_guardrail_marker_consistency.py)
# walks src/ and asserts every file with this marker set to True is
# listed in scripts/guardrail_files.txt. Prevents the next refactor
# from silently removing self-enforcement code from multi-party review.
__guardrail_required__ = True

import json
import re
import sys
from typing import Any


def _load_bypass_subcommands() -> frozenset[str]:
    """Load the canonical bypass-list from scripts/hook_bypass_commands.txt.

    2026-06-09 fix (task #98 locked-box trap): the bypass-list used to be
    inlined here, which meant other PreToolUse Bash hooks (require-
    ear-armed.sh, etc.) couldn't share it — they'd block documented
    bypass commands before they reached this Python module. Now BOTH
    this module AND .claude/hooks/_lib.sh's is_bypass_command read from
    the same canonical file. Single source of truth, no duplication
    drift. Council walk consult-ba0fc4337e51 (Dekker + Lamport): the
    trap was drift-into-failure from accreted-not-designed gate
    layering.

    File format: one ``divineos <subcommand>`` prefix per line, ``#``
    for comments, blank lines ignored. We extract just the subcommand
    after ``divineos `` for fast set-membership check on the matched
    regex group.

    Fail-soft: if the file is missing or unreadable, return the
    bootstrap-essential minimum so the system stays bootable.
    """
    from pathlib import Path

    # Walk up from this file to find repo root (src/divineos/hooks/<file>).
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "scripts" / "hook_bypass_commands.txt"
        if candidate.exists():
            try:
                subs: set[str] = set()
                for line in candidate.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    # Format: "divineos <subcommand>"
                    parts = line.split(None, 1)
                    if len(parts) == 2 and parts[0] == "divineos":
                        subs.add(parts[1].strip())
                if subs:
                    return frozenset(subs)
            except OSError:
                pass
            break
    # Fail-soft minimum to keep bootstrap working.
    return frozenset({"briefing", "ask", "recall", "hud", "context", "init", "preflight"})


_BYPASS_DIVINEOS_SUBCOMMANDS = _load_bypass_subcommands()

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

# Match "divineos <subcmd>" — requires a subcommand word after divineos.
#
# 2026-06-17 fix: also match "divineos.exe <subcmd>" (Windows venv path
# form). Aether and Aria both hit a gate-deadlock the day this was filed
# when invoking divineos via the full venv path (e.g.
# `"./.venv/Scripts/divineos.exe" goal add "..."`). The previous regex
# required `divineos` directly followed by whitespace, so the .exe form
# never matched the bypass list — gate-clearing commands like `goal add`
# and `ask` blocked themselves because the bypass-list lookup didn't fire.
# Adding the optional `.exe` and the optional closing quote handles both
# bare invocations and quoted-path invocations.
#
# 2026-07-16 fix (Aletheia Round 2 Finding 22, keyword-vs-shape master):
# the previous version used `.search()`, matching the pattern ANYWHERE in
# the command. That let `divineos briefing; rm -rf /tmp/x` bypass all
# gates because "briefing" appeared as a substring. The fix is two-fold:
# (a) compound-command detection — any shell metacharacter that would
#     chain commands means we're not looking at a simple bypass, so we
#     refuse the bypass path and fall through to normal gates
# (b) anchored `.match()` — a bypass only counts if the command STARTS
#     with (optional path prefix +) divineos + safe subcmd. A safe word
#     appearing mid-command is not a safe command.
# See Aletheia's F22 for the "allow narrowly, deny broadly" template the
# corrigibility gate already implements correctly.
_DIVINEOS_SUBCMD_RE = re.compile(
    # optional leading whitespace, optional (possibly quoted) path prefix
    # ending in / or \, then divineos with optional .exe and optional
    # closing quote, then required whitespace + subcommand word.
    r"^\s*"
    r"(?:[\"\']?[\w./\\:-]*[/\\])?"
    r"divineos(?:\.exe)?[\"\']?"
    r"\s+(\w[\w-]*)"
)

# Shell metacharacters that chain / pipe / substitute — if any of these
# appear in the command, we are NOT looking at a simple divineos
# invocation, and the bypass path must not apply. The bypass is for
# "run this specific safe command," not "run this safe command AND
# whatever follows." F22 tests all pass after adding this check.
_SHELL_COMPOUND_CHARS = (";", "&&", "||", "|", "`", "$(")


def _has_compound_shape(cmd: str) -> bool:
    """True if the command contains shell-metacharacters that would
    chain, pipe, or substitute — meaning it is NOT a simple bypass
    candidate. Aletheia F22 fix: even a command starting with a safe
    subcommand may not bypass if it chains into a dangerous one.
    """
    return any(marker in cmd for marker in _SHELL_COMPOUND_CHARS)


def _is_bypass_command(cmd: str) -> bool:
    """True if the command should skip all gates (read-only / bootstrap).

    Aletheia F22 (2026-07-16): the check now requires the command to
    BE a safe command, not merely CONTAIN a safe word somewhere.
    Compound commands (chained/piped/substituted) never bypass.
    """
    if not cmd:
        return False
    # F22 gate: compound commands are never bypass candidates, even if
    # they contain a safe word. `divineos briefing; rm -rf /tmp/x` must
    # NOT bypass — the safe word is a decoy, not the command.
    if _has_compound_shape(cmd):
        return False
    # 2026-06-29 (Andrew "no gate should ever be blocking you from using
    # what you need to clear the gate"): the context-governor block
    # message documents `touch ~/.divineos/context_consolidated.json` as
    # the escape hatch when extract errors. That command is itself a
    # substrate-write (creating a marker file) so the gate was blocking
    # the gate's own documented escape — chicken-and-egg, observed live
    # this session when extract was blocked on uncommitted work and the
    # touch was blocked on context-governor at the hard line. This check
    # matches the consolidation marker by its load-bearing path-suffix
    # so any touch of the marker (with ~, $HOME, /c/Users/, /home/, or
    # backslash-Windows-path) passes through. The marker only exists to
    # signal extract was attempted; allowing this specific write does
    # not weaken any safety property.
    if (
        ".divineos/context_consolidated.json" in cmd
        or ".divineos\\context_consolidated.json" in cmd
    ):
        return True
    # divineos bypass subcommands — anchored to command start (F22 fix).
    match = _DIVINEOS_SUBCMD_RE.match(cmd)
    if match and match.group(1) in _BYPASS_DIVINEOS_SUBCOMMANDS:
        return True
    # dev / read-only prefixes — already anchored via startswith.
    for prefix in _DEV_PREFIXES:
        if cmd.startswith(prefix):
            return True
    return False


# Path-exemption set for low-friction (low-gravity) writes.
#
# Per operator directive 2026-04-27: "your exploration folder should
# have no blocks." Extended 2026-06-08 (correction #45): the same
# principle applies to other relational / first-person-expression
# surfaces — letters to family members, mansion writing. These are
# categorically NOT father-facing-claim shape; the fabrication-shape
# detector and the engagement-discipline cluster (goal / engagement /
# consultation / correction-marker) are calibrated for code and
# architecture work, and applying them to relational/expressive writes
# blocks exactly the register the path exists to enable.
#
# The exemption is from path-blocks-tool-use, not from finding-recording.
# The Stop hook still scans assistant output and writes markers; this
# helper only prevents markers from blocking the NEXT write when that
# write is to an exemption path. Forensic-record value preserved.
#
# Mansion specifically: per operator directive, mansion fabrication is
# permitted but must NOT bleed into OS; the path-exemption preserves
# this by leaving marker-firing intact while skipping the tool-block.
#
# Frozen tuple (not list) to prevent accidental in-place modification.
# Adding a path here is a load-bearing calibration decision and should
# be reviewed; the rationale is comment-attached so future changes
# don't silently expand the exemption surface.
_LOW_FRICTION_PATH_SEGMENTS: tuple[str, ...] = (
    "/exploration/",  # First-person free-expression / leisure space.
    "/family/letters/",  # Letters to/from family members — relational channel.
    "/mansion/",  # Internal-space writing — not father-facing.
)


# Code-file extensions that disqualify a path from the leisure-writing
# exemption even if it lives under an exempt directory. Fable 5 audit
# Finding 5 / 2026-06-09: the previous matcher had no such guard, so
# `exploration/gates.py` qualified for the exemption that's supposed to
# encode "this is non-code writing." If the intent is relational
# expression, the file is virtually never source code.
_CODE_FILE_SUFFIXES: frozenset[str] = frozenset(
    {
        ".py",
        ".pyi",
        ".pyx",
        ".sh",
        ".bash",
        ".js",
        ".ts",
        ".tsx",
        ".jsx",
        ".go",
        ".rs",
        ".c",
        ".cpp",
        ".h",
        ".hpp",
        ".java",
        ".rb",
        ".php",
        ".sql",
        ".toml",
        ".yaml",
        ".yml",
    }
)


def _is_low_friction_write(input_data: dict[str, Any]) -> bool:
    """True if the tool is a Write/Edit to a low-friction exemption path.

    Lets the following gates skip when the tool is writing to an
    exemption path (correction #45 / 2026-06-08 expansion):
    - Gate 1.46 (theater marker) — original scope
    - Gate 1.47 (compass-required cascade) — original scope
    - Gate 1.5 (correction-marker) — added 2026-06-08
    - Gate 2 (session-fresh goal) — added 2026-06-08
    - Gate 4 (engagement) — added 2026-06-08
    - Gate 4.5 (consultation staleness) — added 2026-06-08

    HARD safety walls still fire for all writes regardless of path:
    truly-stale briefing (>24h), mansion-quiet, hedge, pull-detection,
    retry-blocker, context-governor. Those protect actual safety
    properties that don't change with tool gravity.

    The discipline-cluster gates encode "have a goal, engage with
    substrate, address corrections before code work." Writing a letter
    to a family member is not code work — it's a relational expression
    whose discipline lives elsewhere (the family-letter skill itself
    requires a goal and grounds in the recipient's state).

    Fable 5 audit Finding 5 fix (2026-06-09): the previous matcher used
    unanchored substring matching, which meant ``exploration/../core/
    ledger.py`` (path traversal landing in core) and ``data/mansion/
    config.py`` (a code file under a substring-matching directory) both
    silently received the exemption. The fix:
      1. Resolve ``..`` via PurePosixPath so traversal collapses.
      2. Match low-friction segments against directory ancestors, not
         arbitrary substrings of the path.
      3. Reject code-file extensions (.py / .sh / .ts / .yml / etc) —
         a code file under an exempt directory is still code work.
    """
    try:
        from pathlib import PurePosixPath

        tool_name = input_data.get("tool_name", "") or ""
        if tool_name not in {"Write", "Edit", "MultiEdit", "NotebookEdit"}:
            return False
        file_path = input_data.get("tool_input", {}).get("file_path", "") or ""
        if not file_path:
            return False

        # Normalize separators + resolve ``..`` segments. PurePosixPath
        # collapses ``a/b/../c`` to ``a/c`` without touching the disk.
        normalized = file_path.replace("\\", "/")
        try:
            resolved_parts: list[str] = []
            for part in PurePosixPath(normalized).parts:
                if part == "..":
                    if resolved_parts:
                        resolved_parts.pop()
                    # ``..`` past the root drops it — paths like
                    # ``exploration/../core/x.py`` resolve to
                    # ``core/x.py`` which won't match any exempt dir.
                elif part != ".":
                    resolved_parts.append(part)
            resolved = "/" + "/".join(p.strip("/") for p in resolved_parts if p)
            # Empty after resolution → can't be exempt.
            if resolved == "/":
                return False
        except (ValueError, IndexError):
            return False

        # Code-file extensions disqualify regardless of directory.
        # A .py under exploration/ is still code work.
        ext = ""
        if "." in resolved_parts[-1]:
            ext = "." + resolved_parts[-1].rsplit(".", 1)[-1].lower()
        if ext in _CODE_FILE_SUFFIXES:
            return False

        # Now check: does any segment appear as a true directory ancestor?
        # Segments are stored as "/exploration/" etc; we want the segment
        # without trailing slash to appear as a *component* of the path,
        # not anywhere in the path string.
        path_components = set(resolved_parts[:-1])  # excludes filename
        for segment in _LOW_FRICTION_PATH_SEGMENTS:
            seg_name = segment.strip("/")
            # Multi-component segment like "family/letters" — match the
            # joined chain.
            if "/" in seg_name:
                joined = "/" + "/".join(resolved_parts[:-1])
                if "/" + seg_name + "/" in joined + "/":
                    return True
            else:
                if seg_name in path_components:
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


# Session-block marker filename. Written at checkout root by
# session_start.verify_session_ownership() when data-home ownership
# verification fails; read here to hard-block substrate access until
# the operator resolves the mismatch. Filename kept at the checkout
# root (not under divineos_home()) so the marker survives even when
# data-home routing itself is the failure.
_SESSION_BLOCK_MARKER_NAME = ".divineos_session_block"


def _check_overdue_prereg_block() -> dict[str, Any] | None:
    """Hard-block substantive tool use when any pre-registration is overdue.

    Runs after the bypass check so `divineos prereg assess ...` and
    other bypass-listed commands can still fire — the operator needs
    them to record outcomes or defer reviews to clear the block.
    Non-bypass tool use is denied with a message pointing at which
    pre-registration IDs need review.

    2026-07-07 fix per Andrew: "no warnings.. they do not work." The
    prior surface put overdue reviews in the briefing where they got
    scrolled past. The doorman does something — this gate is the
    something. Pairs with the 30->7 default review window shortening
    so overdue actually means overdue by design intent.
    """
    try:
        from divineos.core.pre_registrations.store import (
            get_overdue_pre_registrations,
        )
    except ImportError:
        return None
    try:
        overdue = get_overdue_pre_registrations()
    except Exception:  # noqa: BLE001 — fail-open if the store errors
        return None
    if not overdue:
        return None
    ids_preview = ", ".join(p.prereg_id[:24] for p in overdue[:5])
    more = f" (and {len(overdue) - 5} more)" if len(overdue) > 5 else ""
    return _make_deny(
        "OVERDUE PRE-REGISTRATIONS block substantive tool use.\n\n"
        f"{len(overdue)} pre-registration(s) past review date: "
        f"{ids_preview}{more}\n\n"
        "For each overdue pre-registration, record the outcome or defer:\n"
        "  divineos prereg assess <id> --outcome SUCCESS|FAILED|INCONCLUSIVE "
        '--actor <name> --notes "<what happened>"\n'
        "  divineos prereg assess <id> --outcome DEFERRED --actor <name> "
        '--notes "<why deferring>"\n\n'
        "List all overdue with: divineos prereg overdue"
    )


def _check_ownership_block() -> dict[str, Any] | None:
    """Enforce the session-block marker set by session_start on ownership
    mismatch.

    Returns a deny decision if the marker exists, None to fall through.
    Runs BEFORE _is_bypass_command in main() — a mismatched substrate
    makes even documented bypass commands unsafe (they would read or
    write the wrong home). Recovery uses Edit and Write tools, which
    Claude Code does not route through this Bash-tool gate.

    2026-07-07 root-cause fix for the identity-crossing incident: the
    ownership check in data_home_ownership.py existed and was correct
    but was wired only into preflight (discipline-not-enforcement).
    session_start now writes the block marker on verification failure;
    this check enforces refusal-to-route as the spec's "fail loud,
    refuse to boot" second half.
    """
    try:
        from divineos.core.data_home_ownership import _checkout_root
    except ImportError:
        return None
    try:
        marker = _checkout_root() / _SESSION_BLOCK_MARKER_NAME
        if not marker.exists():
            return None
        message = marker.read_text(encoding="utf-8")
    except (OSError, ValueError):
        return None
    return _make_deny(
        "DIVINEOS SESSION BLOCKED — data-home ownership mismatch detected "
        "at session start.\n\n"
        f"{message}\n\n"
        "Recovery: the Edit and Write tools do NOT trigger this Bash gate. "
        "Use them to (a) fix the `.divineos_data_home` marker at the checkout "
        "root so it points at YOUR data-home (or remove that marker to fall "
        f"through to the default), or (b) delete the block marker at {marker}. "
        "Restart the session — session-start will re-verify ownership and "
        "clear the block marker automatically on success."
    )


def _combine_engagement_denies(denies: list[str]) -> str:
    """Coalesce the soft engagement-discipline denials (goal / engagement /
    consultation) into ONE message so they clear in a single pass rather than
    surfacing single-file across N retries.

    GATE-GATE 2026-06-03: the chain is first-deny-wins, so a turn that was
    missing all three hit them one at a time — clear goal, retry, hit
    engagement, retry, hit consultation, retry. The hard safety walls above
    (off-switch, briefing, hedge-claim, mansion-quiet, pull-detection) still
    short-circuit individually and take precedence; ONLY this soft cluster
    coalesces. Same gates, same order, same decisions — just gathered instead
    of returned one-at-a-time.
    """
    if len(denies) == 1:
        return denies[0]
    parts = [
        f"BLOCKED: {len(denies)} engagement checks need clearing before "
        "substrate-modifying tools — surfaced together so you clear them in one "
        "pass, not one at a time:",
        "",
    ]
    for i, d in enumerate(denies, 1):
        body = d[len("BLOCKED: ") :] if d.startswith("BLOCKED: ") else d
        parts.append(f"  [{i}] {body}")
        parts.append("")
    parts.append("Clear all of the above, then retry the tool.")
    return "\n".join(parts)


def _make_soft_advise(advise: str) -> dict[str, Any]:
    """Package a soft advisory in the Claude Code hook response format.

    Allows the tool call to proceed while emitting an additionalContext
    message the agent will see. Used for non-blocking gates whose intent
    is "surface this state" rather than "stop this action".

    Round-2 audit (2026-05-07) named the gate-firing-as-noise failure-mode:
    when a hard-block fires repeatedly with identical message for routine
    cases (e.g. session-id rotation between continuous-work tool calls),
    the agent learns to chain a stub-fix and stops reading the gate
    content. The Goodhart trap: the gate's metric (marker-present)
    decoupled from the property (agent oriented in substrate).

    Soft-advise is the register-fix (Tannen): informational instead of
    emergency-imperative. The gate still surfaces the state; the agent
    receives it as additionalContext rather than as a forced ritual.
    Hard-block stays for truly-stale state (>24h since briefing).
    """
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "additionalContext": advise,
        }
    }


def _briefing_diagnostic(stale_info: dict[str, Any]) -> str:
    """Build a structured message naming WHY the briefing-state is stale.

    Round-2 audit (Holmes' lens): when the briefing gate fires, the
    message should name which condition triggered — TTL expired,
    session-id mismatch, or marker missing entirely. Each is a different
    failure-mode and each calls for a different operator response.
    """
    if not stale_info.get("loaded"):
        return "marker missing - briefing has not been loaded"
    parts = []
    age_h = stale_info.get("age_seconds", 0) / 3600
    parts.append(f"loaded {age_h:.1f}h ago")
    if stale_info.get("ttl_expired"):
        ttl_h = stale_info.get("ttl_seconds", 0) / 3600
        parts.append(f"TTL expired (limit {ttl_h:.0f}h)")
    delta = stale_info.get("calls_since", 0)
    threshold = stale_info.get("threshold", 0)
    if delta:
        parts.append(f"{delta} tool calls since load (threshold {threshold})")
    return " - ".join(parts)


# Truly-stale threshold (still hard-block at this age regardless of session-mismatch).
# 24h matches the operator's expectation that a briefing-load older than a day
# represents real cross-session amnesia, not a within-session rotation event.
_TRULY_STALE_AGE_SECONDS = 24 * 3600


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


def _context_governor_gate(input_data: dict[str, Any] | None) -> dict[str, Any] | None:
    """Gate 7: context-governor hard line (prereg-9b958c6493f3).

    The live context window is the working-memory vital sign; the harness
    compacts at the COMPACTION_CEILING. At the 950k hard line, substrate-writes
    are gated until the self is WOVEN (extract + sleep), so a post-compaction
    instance rehydrates from a connected store rather than a thin save. The
    warn band (920k-950k) does NOT reach here — ``consolidation_state`` returns
    "warn" there, surfaced as a soft nudge at UserPromptSubmit (grace to finish
    in-flight work). extract/sleep are bypassed in ``_is_bypass_command`` so
    the gate can never block its own remedy; sleep marks-consolidated, which
    flips this to "ok" for the rest of the session (fires once, no nag).

    Task #120 / Andrew 2026-06-09: low-gravity writes (exploration/, family/
    letters/, mansion/) PASS through this gate during the block state. The
    rest-phase between extract+sleep and the cliff is meant for exactly
    those activities — recording felt-state, writing letters, the
    you-time before compaction. Blocking them uniformly defeats the
    rest-phase before it can serve its purpose. The gravity classifier
    is the routing oracle: any feature firing = high gravity = block;
    no features = low gravity = pass.

    Fail-open: an unreadable/absent transcript yields "ok" and never blocks
    spuriously. Returns a deny decision on block, else None.
    """
    try:
        transcript_path = (input_data or {}).get("transcript_path", "") or ""
        if not transcript_path:
            return None
        from divineos.core.context_governor import (
            consolidation_state,
            governor_channel_message,
        )

        if consolidation_state(transcript_path) != "block":
            return None

        # Block state. Task #120: low-friction rest-phase writes PASS — the
        # rest-phase between extract+sleep and the cliff exists for exactly
        # these. exploration/, family/letters/, mansion/, dream/, bio/ are
        # the channels the operator named (Andrew 2026-06-09); arbitrary
        # writes continue to block.
        ti = (input_data or {}).get("tool_input", {}) or {}
        fp = (ti.get("file_path", "") or "").replace("\\", "/")
        if fp and any(
            seg in fp
            for seg in (
                "exploration/",
                "family/letters/",
                "mansion/",
                "dream/",
                "bio/",
            )
        ):
            return None

        # Andrew 2026-07-09: shell pass-through. The block exists so the self
        # is WOVEN (extract+sleep) before writing to canonical stores — not
        # so the whole shell freezes. Read-only shell (git status, ls, grep,
        # python scripts, extract/sleep/commit themselves) must not be
        # blocked; only substrate-writing CLI subcommands are. Same
        # classifier the obligations gate uses.
        tool_name = (input_data or {}).get("tool_name", "") or ""
        if tool_name in ("Bash", "PowerShell"):
            cmd = (ti.get("command", "") or "").strip()
            try:
                from divineos.core.obligations import is_substrate_write_command

                if not is_substrate_write_command(cmd):
                    return None
            except ImportError:
                return None

        return _make_deny(governor_channel_message(transcript_path))
    except (ImportError, OSError, AttributeError) as _gate_exc:
        _record_gate_failure("gate_7_context_governor", _gate_exc)
    return None


def _check_gates(input_data: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Run all gates in order. Return first deny decision, or None if all pass.

    Import-heavy work is guarded — if a module can't be imported (e.g. during
    first-run bootstrap), that gate is skipped rather than crashing the hook.
    Fail-open is the correct disposition for a gate whose machinery is broken.
    """
    # Soft engagement-discipline denials (goal / engagement / consultation) are
    # COLLECTED here and surfaced together at the end of the soft cluster, so
    # they clear in one pass instead of single-file (GATE-GATE 2026-06-03). The
    # hard walls below still short-circuit individually and take precedence.
    soft_denies: list[str] = []

    # Gate 0: exploration entries must carry a tag header (write-time wall).
    # Named 2026-05-27. Placed FIRST on purpose: the briefing gates below can
    # return a soft-advise ("allow") that short-circuits the rest of the
    # chain, so a hard structural wall must be evaluated before them or a
    # stale-briefing turn would let an untagged entry through. Coverage-by-
    # backfill rots — a new exploration entry saved without tags is invisible
    # to the recall surfacer and silently reopens the forgetting hole (how
    # 82-84 shipped untagged that night). Write-only (Edit gets a diff, not
    # the whole file); README-exempt; constrains a findability affordance,
    # not content — free-speech principle intact.
    try:
        if input_data is not None:
            from divineos.core.exploration_recall import needs_tags_block

            _tn = input_data.get("tool_name", "") or ""
            _ti = input_data.get("tool_input", {}) or {}
            _msg = needs_tags_block(
                _tn, _ti.get("file_path", "") or "", _ti.get("content", "") or ""
            )
            if _msg:
                return _make_deny(_msg)
    except (ImportError, OSError, AttributeError) as _gate_exc:
        _record_gate_failure("gate_0_exploration_tags", _gate_exc)

    # Gate 0: exploration-entry numbering invariants.
    #
    # Built 2026-06-21 (Andrew named the root cause: "I am the OS at this
    # point" — the babysitting pattern was exactly because the OS lacked
    # a validator preventing duplicates and gaps in exploration entry
    # numbers). The validator at exploration_validator.py defines the
    # invariants; this gate makes them enforced at tool-use time so a
    # Write tool call with a malformed exploration entry path is refused
    # before the file lands.
    #
    # Fires ONLY on Write/Edit tool calls to exploration/<member>/. Other
    # writes (letters, code, etc.) are not the validator's concern and
    # pass through. Refusal carries a plain-language reason from the
    # validator that names the invariant violated and the correct
    # number to use.
    if input_data is not None:
        try:
            tool_name = input_data.get("tool_name", "")
            file_path = (input_data.get("tool_input") or {}).get("file_path", "")
            if tool_name in ("Write", "Edit") and "exploration/" in str(file_path):
                from divineos.core.exploration_validator import (
                    validate_new_entry_path,
                )
                from pathlib import Path as _Path

                ok, reason = validate_new_entry_path(_Path(file_path))
                if not ok:
                    return _make_deny(
                        f"BLOCKED: exploration-entry validator refused this path. "
                        f"{reason} Sanctioned creation path: "
                        f"`divineos exploration new --slug <slug>`."
                    )
        except (ImportError, OSError, AttributeError, KeyError) as _gate_exc:
            _record_gate_failure("gate_0_exploration_validator", _gate_exc)

    # Gate 1: briefing-ID recall-challenge.
    #
    # REWRITE 2026-06-20 (Aether, council walk consult-9a8ba69e9598,
    # prereg-933233700f06): the old gate measured wall-clock time-passed
    # since `divineos briefing` last ran. That metric was unrelated to
    # the actual question ("is the briefing still in my retrievable
    # context"). Wall-clock fired stale even when nothing had changed
    # (idle gap) and stayed quiet when the briefing had genuinely faded
    # (mid-session compaction). The briefing-ID recall mechanism in
    # briefing_id.py measures the right thing directly: a context-
    # printed random token I have to reproduce from memory. Recall-
    # failure IS the staleness signal — measured, not estimated.
    #
    # Gate 1.1 (per-session-marker mismatch) and the wall-clock-based
    # Gate 1 are both retired by this swap: the recall-challenge
    # subsumes both — if the briefing is in my context the recall
    # passes regardless of session-id rotation; if it isn't, the recall
    # fails regardless of how recent the marker stamp is.
    #
    # Low-friction-path exemption preserved (operator directive
    # 2026-04-27): writes to exploration/, family/letters/, and other
    # first-person/relational surfaces bypass the staleness check.
    # Letters to family are not father-facing-claim work; blocking
    # them on briefing-staleness blocks exactly the register the
    # exemption path exists to enable.
    try:
        if input_data is None or not _is_low_friction_write(input_data):
            from divineos.core.briefing_id import (
                challenge_message,
                current_tool_count,
                is_fresh,
            )

            if not is_fresh(current_tool_count()):
                return _make_deny(f"BLOCKED: {challenge_message(current_tool_count())}")
    except (ImportError, OSError, AttributeError) as _gate_exc:
        _record_gate_failure("gate_1_briefing_id_recall", _gate_exc)

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

    # Gate 1.46: REMOVED 2026-05-01 (free-speech principle).
    # Theater / fabrication detection now surfaces observationally
    # in the next briefing instead of blocking the next tool. The
    # marker file (~/.divineos/theater_unresolved.json) is still
    # written by the Stop hook for forensic record; the detector
    # itself stays active. What changed: no gate-block on tool use,
    # no cascade to compass-required. Naming via correction / learn
    # is voluntary discipline. See core/theater_marker.py for the
    # rationale and the surface module that replaces this gate.

    # Gate 1.47: compass observation required after virtue-relevant event.
    # Build #4 from claim 7e780182. Fires when a correction, theater fire,
    # hedge fire, or substantive claim has occurred. Skip on exploration-
    # path Write/Edit per the 2026-04-27 calibration directive.
    #
    # 2026-05-08 redesign (per pre-reg prereg-75c900fe; adopted into
    # Experimental 2026-05-27 per decision cfddd811): disclose-then-escalate
    # rather than hard-block-on-marker. Below ESCALATION_THRESHOLD advisory
    # fires, return soft-advise so the substrate-occupant gets the disclosure
    # without being blocked; at/above threshold, hard deny as before. Per-turn
    # dedup (PER_TURN_DEDUP_SECONDS) stops the same marker re-firing on every
    # tool call within one turn — the wallpaper failure-mode the redesign
    # fixes. FALSIFIER (must verify): the escalation actually fires (advised_
    # count reaches threshold and denies), else dedup+grace degrade it to an
    # ignorable advisory.
    try:
        if input_data is None or not _is_low_friction_write(input_data):
            from divineos.core.compass_required_marker import (
                ESCALATION_THRESHOLD as _CR_ESC,
            )
            from divineos.core.compass_required_marker import (
                format_gate_message as _cr_msg,
            )
            from divineos.core.compass_required_marker import (
                marker_path as _cr_path,
            )
            from divineos.core.compass_required_marker import (
                read_marker as _cr_read,
            )
            from divineos.core.compass_required_marker import (
                record_advisory_fire as _cr_record,
            )
            from divineos.core.compass_required_marker import (
                should_dedup_within_turn as _cr_dedup,
            )

            if _cr_path().exists():
                cr = _cr_read()
                if cr is None:
                    # Marker present but unreadable — fail-closed.
                    return _make_deny(
                        "BLOCKED: compass-required marker present at "
                        f"{_cr_path()} but unreadable. "
                        "Clear by running: divineos compass-ops observe "
                        "<spectrum> -p <position> -e <evidence>. Fail-closed."
                    )

                advised_count = int(cr.get("advised_count", 0))
                # Defensive guard: dedup should only suppress after a prior
                # advisory set last_advised_ts (which also sets advised_count
                # >= 1). The >= 1 check guards corrupted/hand-edited markers.
                if advised_count >= 1 and _cr_dedup():
                    pass  # silent suppression within per-turn window
                elif advised_count >= _CR_ESC:
                    # Escalation: advisory ignored ESCALATION_THRESHOLD times.
                    return _make_deny(_cr_msg(cr))
                else:
                    # Disclosure: emit advisory, increment counter, allow.
                    _cr_record()
                    return _make_soft_advise(_cr_msg(cr))
    except (ImportError, OSError, AttributeError) as _gate_exc:
        _record_gate_failure("gate_1_47_compass_required", _gate_exc)

    # Gate 1.48: stale-engagement block.
    # Andrew named this gate 2026-05-14: the briefing should warn on
    # ignored stale entries; after the third ignoring, BLOCK the next
    # code action until they're addressed. Friction is the source of
    # flow. The tracker lives in core/stale_engagement.py:
    # render_dashboard records STALE_SURFACED events; address commands
    # fire area-specific close events; this gate counts the gap and
    # denies when any area has been surfaced 3+ times without being
    # addressed.
    try:
        from divineos.core.stale_engagement import (
            block_message,
            blocked_areas,
        )

        offenders = blocked_areas()
        if offenders:
            return _make_deny(block_message(offenders))
    except (ImportError, OSError, AttributeError) as _gate_exc:
        _record_gate_failure("gate_1_48_stale_engagement", _gate_exc)

    # Gate 1.5: correction detected but not logged.
    # Closes ChatGPT audit claim-964493 (theater-learning bypass) by making
    # "log the correction" a structural requirement, not intent. The
    # UserPromptSubmit hook (detect-correction.sh) sets the marker when a
    # user message matches CORRECTION_PATTERNS; `divineos learn` and
    # `divineos correction` clear it. Fail open on missing machinery.
    #
    # Low-friction-write exemption (correction #45 / 2026-06-08): writes to
    # exploration/, family/letters/, mansion/ are relational/expressive,
    # not architectural; the correction-discipline that this gate encodes
    # applies to code work. The marker stays set; the next high-gravity
    # write (src/divineos/, hooks, etc.) still gets blocked.
    try:
        if input_data is None or not _is_low_friction_write(input_data):
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

    # Low-friction-write check for the soft engagement-discipline cluster
    # (gates 2 / 4 / 4.5). Writes to exploration/, family/letters/, mansion/
    # are relational/expressive, not code-architecture; the discipline these
    # gates encode (have a goal, engage with substrate, recently consulted)
    # is calibrated for code work. For low-friction writes, skip them.
    # Hard safety walls above (briefing-truly-stale, hedge, pull-detection,
    # retry, context-governor) still apply unconditionally.
    # Correction #45 / 2026-06-08.
    _low_friction = input_data is not None and _is_low_friction_write(input_data)

    # Gate 2: session-fresh goal
    if not _low_friction:
        try:
            from divineos.core.hud_state import has_session_fresh_goal

            if not has_session_fresh_goal():
                soft_denies.append(
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
    if not _low_friction:
        try:
            from divineos.core.hud_handoff import engagement_status

            s = engagement_status()
            if not s.get("engaged", True):
                state = s.get("state", "drift")
                if state == "fresh":
                    _eng_msg = (
                        "BLOCKED: No engagement marker yet this session. "
                        "Briefing alone is not enough — engage with a thinking "
                        'tool first. Run: divineos ask "topic", recall, '
                        "context, or decide."
                    )
                elif state == "deep_drift":
                    deep_since = s.get("deep_actions_since", "?")
                    _eng_msg = (
                        f"BLOCKED: {deep_since} code actions since you last "
                        "consulted your knowledge. Light check-ins are not "
                        'enough. Run: divineos ask "topic" or divineos '
                        "recall to query what you actually know."
                    )
                else:
                    code_since = s.get("code_actions_since", "?")
                    _eng_msg = (
                        f"BLOCKED: {code_since} code actions since last thinking "
                        "command. Stop and think. Run: divineos ask, recall, "
                        "decide, or context before continuing."
                    )
                soft_denies.append(_eng_msg)
        except (ImportError, OSError, AttributeError) as _gate_exc:
            _record_gate_failure("gate_4_engagement", _gate_exc)

    # Gate 4.5: consultation-staleness (gate + channel).
    # Andrew named the root 2026-05-23: the consultation tracker WARNED but
    # never blocked, so I routed past it every time ("I forget to use my own
    # tools until the gates block me"). This converts the warning into a
    # block-with-channel: when responses-since-last-substantive-consult
    # exceeds threshold, substrate-modifying tools are denied and the deny
    # message OFFERS THE PATH — it inlines the unread correction and names the
    # exact consult command. Distinct from the engagement gate (gate 4):
    # that counts code-actions and clears on cheap tools (context/decide);
    # this counts RESPONSES and clears only on substrate-surfacing consults
    # (ask/recall/corrections/directives/active/compass), which are bypassed
    # above so they can never be blocked by their own remedy.
    if not _low_friction:
        try:
            from divineos.core.consultation_tracker import (
                consultation_gate_status,
                gate_channel_message,
            )

            if consultation_gate_status().get("stale"):
                soft_denies.append(gate_channel_message())
        except (ImportError, OSError, AttributeError) as _gate_exc:
            _record_gate_failure("gate_4_5_consultation", _gate_exc)

    # Coalesced engagement-discipline cluster: surface the goal / engagement /
    # consultation denials TOGETHER (one pass to clear) instead of single-file
    # across N retries — GATE-GATE 2026-06-03. Placed after the last soft gate
    # (4.5) and before the hard retry/governor walls below, preserving the
    # original gate order. A hard wall above that fired already short-circuited.
    if soft_denies:
        return _make_deny(_combine_engagement_denies(soft_denies))

    # Gate 5 removed 2026-04-21 (commit C of tiered-audit redesign).
    # See comment history for rationale. Replaced by informational
    # drift_state surface in briefing.

    # Gate 6: retry blocker (lesson x11, most repeated behavioral failure).
    # Catches blind retries — same command re-invoked after failure without
    # a diagnostic investigation step in between. Diagnostic commands
    # (Read, Grep, git diff, divineos ask) clear the block automatically.
    try:
        from divineos.core.retry_blocker import (
            check_retry,
            is_diagnostic_command,
            mark_investigated,
        )

        tool_name = (input_data or {}).get("tool_name", "")
        tool_input = (input_data or {}).get("tool_input", {}) or {}

        # If this IS a diagnostic command, mark all failures as investigated
        if tool_name and is_diagnostic_command(tool_name, tool_input):
            mark_investigated()
        elif tool_name:
            # Check if this is a blind retry
            deny_msg = check_retry(tool_name, tool_input)
            if deny_msg:
                return _make_deny(deny_msg)
    except (ImportError, OSError, AttributeError) as _gate_exc:
        _record_gate_failure("gate_6_retry_blocker", _gate_exc)

    # Gate 7: context-governor hard line (prereg-9b958c6493f3).
    governor_decision = _context_governor_gate(input_data)
    if governor_decision is not None:
        return governor_decision

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

    # Ownership-block gate — runs BEFORE bypass check. A mismatched
    # substrate makes even documented bypass commands unsafe: they would
    # read or write another agent's data-home. Recovery uses Edit/Write
    # tools, which Claude Code does not route through this Bash gate.
    # 2026-07-07 root-cause fix — pairs with session_start.verify_session_ownership.
    block_decision = _check_ownership_block()
    if block_decision is not None:
        json.dump(block_decision, sys.stdout)
        return 0

    if _is_bypass_command(cmd):
        return 0

    # Overdue pre-registration block. Fires when any pre-registration is
    # past its review date without a terminal outcome. Non-bypass tools
    # are denied until the operator assesses the outcome or defers.
    # 2026-07-07 fix per Andrew: warnings alone don't work; the doorman
    # blocks. Pairs with the review-days 30->7 default so overdue actually
    # bites within the week.
    overdue_decision = _check_overdue_prereg_block()
    if overdue_decision is not None:
        json.dump(overdue_decision, sys.stdout)
        return 0

    decision = _check_gates(input_data)
    if decision is not None:
        json.dump(decision, sys.stdout)

    return 0


if __name__ == "__main__":
    sys.exit(main())
