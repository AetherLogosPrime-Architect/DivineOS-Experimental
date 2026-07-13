"""no-verify cost-escalation — core decision logic, moved out of the bash hook.

The PreToolUse hook ``.claude/hooks/no-verify-cost-escalation.sh`` is the
doorbell; this module is the brain. Same shape as the audit_visibility,
deletion_discipline, and seal_hook migrations: keep the bash thin so the
hook can't drift from the convention, and put all the actual judgment
inside the OS.

Pop 2026-06-30: "where the right answer is the same every time, the
decision itself is wasted work. Removing the decision point removes the
leak. Replace the decision with structure so it makes the choice for you."

The hook script becomes ~10 lines. The convention is enforced by there
being nothing in the hook to misuse.

# Rule

Any ``git commit --no-verify`` or ``git push --no-verify`` in a Bash
tool-call must be accompanied by an inline
``DIVINEOS_NO_VERIFY_REASON="<one-line>"`` assignment. The reason is
logged to bypass_telemetry on the allow path so bypasses stay visible
in the substrate's drift surfaces.

# Why the bash version was wrong

Earlier today the bash hook was using bare ``python`` instead of
``find_divineos_python``. That ANTI-pattern is what
test_no_hook_uses_bare_python_for_divineos_imports catches. The bug
existed at all because the hook contained Python logic in the first
place — the kind of thing the OS-module-thin-hook split is designed
to prevent. Moving the logic here means the only python the hook
runs is the OS module call.
"""

from __future__ import annotations

import re
import shlex
from typing import Any


_REASON_PATTERN = re.compile(r'DIVINEOS_NO_VERIFY_REASON=(?:"([^"]+)"|\'([^\']+)\'|(\S+))')
_MIN_REASON_LEN = 8


def decide(tool_input: dict[str, Any] | None) -> dict[str, Any] | None:
    """Decide whether a Bash command containing --no-verify should pass.

    Returns:
        None  → allow (either irrelevant or has a valid named reason)
        dict  → deny with the structured PreToolUse JSON the hook prints

    Logging side-effect: on the allow-with-reason path, records the
    bypass to bypass_telemetry so it shows up in drift surfaces.
    """
    if not tool_input:
        return None
    cmd = (tool_input.get("command") or "").strip()
    if not cmd:
        return None

    try:
        tokens = shlex.split(cmd)
    except ValueError:
        # Malformed shell quoting — let it through; another gate catches.
        return None

    if "git" not in tokens:
        return None
    git_idx = tokens.index("git")
    subcommand = tokens[git_idx + 1] if git_idx + 1 < len(tokens) else ""
    if subcommand not in ("commit", "push"):
        return None
    if "--no-verify" not in tokens:
        return None

    # --no-verify on git commit/push. Demand an inline reason.
    match = _REASON_PATTERN.search(cmd)
    if match:
        reason = (match.group(1) or match.group(2) or match.group(3) or "").strip()
        if len(reason) < _MIN_REASON_LEN:
            return _deny(
                "BLOCKED: --no-verify reason too short "
                f"(< {_MIN_REASON_LEN} chars).\n"
                "Aletheia 2026-06-30 letter #13: the bypass must name what it\n"
                'is cover for. "fix", "tests", "wip" do not name the gate-shape\n'
                "being bypassed. Try a more specific reason such as:\n"
                f'  DIVINEOS_NO_VERIFY_REASON="gate blocks fix to gate" \\\n'
                f"    git {subcommand} --no-verify ..."
            )
        # Allow path — log the bypass to telemetry, then approve silently.
        try:
            from divineos.core.bypass_telemetry import record_bypass

            record_bypass(
                gate_name="git-" + subcommand + "-no-verify",
                env_var="DIVINEOS_NO_VERIFY_REASON",
                reason=reason,
            )
        except Exception:  # noqa: BLE001 — observability fail-open
            pass
        return None

    # No reason provided — block.
    return _deny(
        f"BLOCKED: git {subcommand} --no-verify requires a named reason.\n\n"
        "Aletheia 2026-06-30 (letter #13) flagged --no-verify as a structural\n"
        "signal: the bypass-telemetry caught all four uses on 2026-06-30 but\n"
        "did not stop them. This gate converts catch-without-stop into\n"
        "name-the-reason-or-block.\n\n"
        "Required form:\n"
        '  DIVINEOS_NO_VERIFY_REASON="<what the gate is wrong about>" \\\n'
        f"    git {subcommand} --no-verify ...\n\n"
        "The reason gets logged to bypass_telemetry so the bypasses stay\n"
        "visible in drift surfaces. Reason must be at least "
        f"{_MIN_REASON_LEN} chars and should name the gate-shape, not the\n"
        "surface symptom.\n\n"
        "If the gate is genuinely wrong-shape, file the bug first:\n"
        '  divineos audit submit-round "<gate>: wrong-shape" --actor aether\n'
        "and reference the round-id in the no-verify reason."
    )


def _deny(reason: str) -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def main() -> int:
    """Entry point for the bash hook to call.

    Reads PreToolUse JSON from stdin, writes a decision (or nothing for
    allow) to stdout, exits 0. Fail-open on any unexpected error — the
    hook itself is observational and must not break the workflow.
    """
    import json
    import sys

    try:
        data = json.loads(sys.stdin.read() or "{}")
    except Exception:  # noqa: BLE001
        return 0
    if (data.get("tool_name") or "") != "Bash":
        return 0
    decision = decide(data.get("tool_input") or {})
    if decision is not None:
        sys.stdout.write(json.dumps(decision))
    return 0


__all__ = ["decide", "main"]
