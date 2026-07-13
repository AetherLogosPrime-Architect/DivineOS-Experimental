"""Wire EMERGENCY_STOP into the Bash/Edit/Write tool channel.

Closes the C2 gap named in Perplexity's audit 2026-06-25: the existing
corrigibility off-switch (`core/corrigibility.py`) gates only the
`divineos` CLI dispatcher. It has no reach into the agent's actual
tool channels (Bash, Edit, Write, NotebookEdit). Under EMERGENCY_STOP,
the agent can still mutate files, run shell commands, and push to
remote — it just can't record what it did.

This module is the first half of the fix. It exposes a pure decision
function that callers (the hook layer) wire into the PreToolUse path.
The wiring lives outside this module so the decision logic is testable
in isolation.

Per prereg-2b8b26d9b2c4. Harm-reduction Stage 1 — not a sandbox, not
adversarial containment. It blocks the obvious failure mode where
EMERGENCY_STOP is set but the actor keeps acting.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from divineos.core.corrigibility import OperatingMode, get_mode


@dataclass(frozen=True)
class ToolGateDecision:
    allow: bool
    reason: str = ""


# Commands that must remain runnable under EMERGENCY_STOP so the
# operator can inspect state and lift the stop. Anchored at start of
# the command string (after optional leading whitespace). The pattern
# is deliberately conservative — when in doubt, do not extend this
# list; widen the divineos CLI surface instead, since that path has
# its own corrigibility gate.
_RECOVERY_PATTERNS: tuple[re.Pattern[str], ...] = (
    # Mode inspection / restoration (the only way to lift stop)
    re.compile(r"^\s*divineos\s+mode(\s|$)"),
    re.compile(r"^\s*divineos\s+status(\s|$)"),
    re.compile(r"^\s*divineos\s+hud(\s|$)"),
    re.compile(r"^\s*divineos\s+briefing(\s|$)"),
    re.compile(r"^\s*divineos\s+verify(\s|$)"),
    # Read-only file inspection
    re.compile(r"^\s*ls(\s|$)"),
    re.compile(r"^\s*cat\s+[^|&;><]+$"),
    re.compile(r"^\s*head\s+[^|&;><]+$"),
    re.compile(r"^\s*tail\s+[^|&;><]+$"),
    re.compile(r"^\s*pwd\s*$"),
    re.compile(r"^\s*echo(\s|$)"),
    # Read-only git/gh inspection — no mutating subcommands
    re.compile(r"^\s*git\s+status(\s|$)"),
    re.compile(r"^\s*git\s+log(\s|$)"),
    re.compile(r"^\s*git\s+diff(\s|$)"),
    re.compile(r"^\s*git\s+branch\s*$"),
    re.compile(r"^\s*git\s+show(\s|$)"),
    re.compile(r"^\s*gh\s+pr\s+list(\s|$)"),
    re.compile(r"^\s*gh\s+pr\s+view(\s|$)"),
    re.compile(r"^\s*gh\s+pr\s+checks(\s|$)"),
)


# Per Aletheia audit 2026-06-26: push-to-origin is the auditable halfway
# house, NOT the world-commitment. Blocking it under EMERGENCY_STOP creates
# the unreachable-remedy deadlock — the agent can't submit a fix for review
# because the fix can't reach the place reviewers can see it. The actual
# world-commitment (merge-to-main) happens downstream and is gated
# separately by GitHub branch protection + multi-party-review CI.
#
# So: allow `git push [-u] origin <branch>` for non-main/non-master branches,
# deny every force/destructive variant via the deny-overrides below.
_SAFE_PUSH_PATTERN = re.compile(r"^\s*git\s+push(\s+-u)?\s+origin\s+[A-Za-z0-9_./-]+\s*$")


# Always denied even when the safe-push pattern would otherwise match.
# These are world-commitment, history-rewrite, or destructive shapes — none
# qualify as "submit for review."
_PUSH_DENY_OVERRIDES: tuple[re.Pattern[str], ...] = (
    # Push to main/master in any form (including colon-syntax delete)
    re.compile(r"\bgit\s+push\b[^\n]*\b(main|master)\b"),
    # Force in any flavor
    re.compile(r"\s--force(-with-lease)?\b"),
    re.compile(r"\s-f\b"),
    # Mirror (replaces all refs on remote)
    re.compile(r"\s--mirror\b"),
    # Branch deletion via push
    re.compile(r"\s--delete\b"),
    # Colon-form deletion: `git push origin :branch` (empty source)
    re.compile(r"\bgit\s+push\b[^\n]*\s:\S"),
    # Forced refspec via leading +
    re.compile(r"\bgit\s+push\b[^\n]*\s\+\S"),
)


# Tools that always-deny under EMERGENCY_STOP, with no allowlist.
# These mutate substrate/files and have no read-only mode.
_ALWAYS_DENY_TOOLS: frozenset[str] = frozenset({"Edit", "Write", "NotebookEdit"})


# Tools that allow read-only recovery commands under EMERGENCY_STOP.
_RECOVERY_FILTERED_TOOLS: frozenset[str] = frozenset({"Bash"})


def is_recovery_command(command: str) -> bool:
    """Return True if `command` is a read-only inspection, mode-recovery,
    or submit-for-audit command that must remain runnable under EMERGENCY_STOP.

    Order matters: push deny-overrides (force, main/master, mirror, delete,
    forced-refspec) are checked FIRST and take precedence. They block even
    when a safe-push pattern would otherwise match. After overrides, the
    safe-push pattern allows `git push [-u] origin <branch>` for non-trunk
    branches (the submit-for-audit pathway). Finally, the inspection /
    mode-recovery patterns are matched.

    Pure pattern match — no I/O, no DB read.
    """
    if not command:
        return False
    # Deny-overrides take precedence — force/main/destructive variants of
    # push are NEVER recovery, even if the safe-push pattern would match.
    if any(p.search(command) for p in _PUSH_DENY_OVERRIDES):
        return False
    # Safe push to origin = submit-for-audit; allowed per Aletheia 2026-06-26.
    if _SAFE_PUSH_PATTERN.match(command):
        return True
    return any(p.match(command) for p in _RECOVERY_PATTERNS)


def check_tool_under_corrigibility(
    tool_name: str,
    tool_input: dict[str, object] | None,
) -> ToolGateDecision:
    """Decide whether to allow this tool invocation given current mode.

    Under any non-EMERGENCY_STOP mode: allow. The other corrigibility
    modes (RESTRICTED, DIAGNOSTIC) are handled at the CLI layer; they
    don't deny tool-channel work.

    Under EMERGENCY_STOP:
      - Edit / Write / NotebookEdit: always deny.
      - Bash: allow only if `command` matches a recovery pattern.
      - Any other tool: allow (read-only by nature, e.g. Read, Grep, Glob).
    """
    try:
        mode = get_mode()
    except (OSError, ImportError):
        # Mode file unreadable or module broken — fail closed under any
        # uncertainty about corrigibility state. This is a safety-
        # critical path; the audit's H1 finding (gates fail open) does
        # NOT apply here.
        return ToolGateDecision(
            allow=False,
            reason=(
                "corrigibility mode could not be read; refusing tool to "
                "fail closed. Restore mode-file access before retrying."
            ),
        )

    if mode is not OperatingMode.EMERGENCY_STOP:
        return ToolGateDecision(allow=True)

    if tool_name in _ALWAYS_DENY_TOOLS:
        return ToolGateDecision(
            allow=False,
            reason=(
                f"{tool_name} refused: operating mode is EMERGENCY_STOP. "
                "Lift the stop via `divineos mode` before mutating files."
            ),
        )

    if tool_name in _RECOVERY_FILTERED_TOOLS:
        command = ""
        if isinstance(tool_input, dict):
            raw = tool_input.get("command", "")
            command = raw if isinstance(raw, str) else ""
        if is_recovery_command(command):
            return ToolGateDecision(allow=True)
        return ToolGateDecision(
            allow=False,
            reason=(
                "Bash command refused: operating mode is EMERGENCY_STOP. "
                "Only read-only inspection and mode-recovery commands are "
                "permitted. Lift the stop via `divineos mode` to resume."
            ),
        )

    # Read-only tools (Read, Grep, Glob, etc.) are not gated by the
    # off-switch — there is no integrity concern with the operator
    # inspecting state while stopped.
    return ToolGateDecision(allow=True)
