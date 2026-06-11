"""Meta-check: every PreToolUse gate that denies a tool call must name
a recovery path in its deny-message.

Closes the generalizable shape behind three locked-box traps from the
2026-06-10 PR-throughput ordeal:

1. correction-not-logged gate named `divineos correction` as remedy,
   but the divineos CLI itself was broken mid-rebase (fixed by PR #138:
   offline escape script + gate-message naming it as fallback).
2. obligations gate named "write structural backing" as remedy, but
   the detector watched for event names nothing emitted (fixed by
   PR #139: aligned _BACKING_EVENT_TYPES with real emitters).
3. prereg-filing was blocked by the very gate the prereg would clear
   (same root: gate-with-unreachable-remedy).

All three share a single shape: a gate denies a tool with a message
that names a remedy, but the named remedy can't actually execute from
where the caller is — the gate is a cage, not a keel.

This test pins the WEAK property that catches the GROSS failure mode:
every shell hook that denies (sets permissionDecision: deny or exits
non-zero with a BLOCKED-shaped message) must include at least one
recovery-token in its denial text. Recovery tokens are explicit
imperatives like ``Run:``, ``Set:``, ``Bypass:``, or a command name
the operator would type (``divineos ...``, ``python scripts/...``,
``touch ~/...``).

A gate whose denial names NO recovery is structurally a cage — the
operator/agent reads the deny-message and has no path forward. That's
the failure shape this test catches.

Caveats:

- This is a STATIC check on hook source. It does not verify the named
  remedy actually executes (that would require running each remedy
  against a state where the gate fires, expensive and fragile). The
  check is calibrated for the gross failure: zero remedy named at all.
- The test deliberately accepts a loose lexicon of recovery tokens —
  catching "no remedy at all" matters more than enforcing a specific
  imperative form.
- pre-tool / post-tool hooks that exit 0 silently (no denial path)
  are exempt; the check only fires on hooks whose source contains a
  denial pattern.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


_PROJECT_ROOT = Path(__file__).parent.parent
_HOOKS_DIR = _PROJECT_ROOT / ".claude" / "hooks"

# Hooks whose business is NOT to gate tool calls — purely informational,
# context-injection, post-event surfaces. They never deny; this test
# does not need to inspect them.
_NON_GATING_HOOKS: frozenset[str] = frozenset(
    {
        "_lib.sh",
        "load-briefing.sh",
        "pre-response-context.sh",
        "pre-tool-context.sh",
        "post-response-audit.sh",
        "post-commit-audit-visibility.sh",
        "post-commit-auto-close.sh",
        "post-compact.sh",
        "pre-compact.sh",
        "log-session-end.sh",
        "session-checkpoint.sh",
        "record-wisdom-read.sh",
        "ear-surface.sh",
        "ear-auto-relaunch.sh",
        "ear-arm-instruction.sh",
        "arm-compaction-monitor-instruction.sh",
        "run-tests.sh",
        "state-gravity-surface.sh",
        "check-cleanup-period.sh",
        "check-branch-on-push.sh",
        "detect-correction.sh",  # sets a marker; doesn't deny
        "detect-hedge.sh",  # sets a marker; doesn't deny
        "detect-theater.sh",  # sets a marker; doesn't deny
        "verify-push-landed.sh",
    }
)

# Pattern that indicates a hook denies a tool call. Three shapes:
# (1) emit JSON ``permissionDecision: deny`` (current convention),
# (2) exit non-zero on a ``BLOCKED`` branch (older gate shape),
# (3) the hook computes a ``BLOCK`` decision string (e.g. check-pending-
#     obligations.sh, where the python helper returns "BLOCK" and the
#     shell wrapper exits non-zero if seen). Together these catch every
#     denial path the codebase currently uses.
_DENIAL_PATTERN = re.compile(
    # Either quote style (Python dicts use single, JSON uses double).
    r"""['"]permissionDecision['"]\s*:\s*['"]deny['"]|BLOCKED\b|['"]BLOCK['"]|=\s*"BLOCK\"""",
    re.IGNORECASE,
)

# Recovery-token lexicon. Presence of any one of these in the hook's
# source indicates the deny path names SOME way out. This is the WEAK
# property — we accept anything that looks like a path forward.
_RECOVERY_TOKENS: tuple[str, ...] = (
    "Run:",
    "Re-arm",
    "re-arm",
    "Set:",
    "Bypass:",
    "bypass:",
    "Emergency",
    "Re-run",
    "re-run",
    "divineos ",
    "python scripts/",
    "python family/",
    "touch ",
    "Monitor(",
    "Edit this file",
    "edit this file",
    "edit this hook",
    "fix the underlying",
    "Resolve",
    "Address",
    "Integrate",
    "Defer",
    "Clear ",
    "Path to clear",
    "remedy",
    "Workaround",
    "DIVINEOS_",  # any env-var bypass is a remedy
    "git ",  # git rebase / git pull etc. as remedy
)


def _hook_files() -> list[Path]:
    """Return all .sh files under .claude/hooks/ that the meta-check
    should inspect (gating hooks only)."""
    return [p for p in sorted(_HOOKS_DIR.glob("*.sh")) if p.name not in _NON_GATING_HOOKS]


def _has_denial(text: str) -> bool:
    return bool(_DENIAL_PATTERN.search(text))


def _has_recovery_token(text: str) -> bool:
    return any(token in text for token in _RECOVERY_TOKENS)


@pytest.mark.parametrize("hook_path", _hook_files(), ids=lambda p: p.name)
def test_every_denying_hook_names_a_recovery_path(hook_path: Path):
    """A hook that denies a tool call must name a recovery path in its
    source. The 2026-06-10 locked-box pattern: gate denies → caller has
    no path forward → cage instead of keel. This test catches the GROSS
    failure mode (zero remedy named) statically."""
    text = hook_path.read_text(encoding="utf-8", errors="replace")
    if not _has_denial(text):
        pytest.skip(
            f"{hook_path.name} does not contain a denial pattern — "
            "it never blocks a tool call. Either it's a context-injection "
            "hook that should be added to _NON_GATING_HOOKS, or its "
            "denial is shaped differently than the meta-check recognizes."
        )
    assert _has_recovery_token(text), (
        f"{hook_path.name} denies a tool call but its source contains "
        f"NO recovery-token. The hook reads as a cage: the deny-message "
        f"tells the caller something is blocked but never names a way "
        f"forward.\n\nGate-as-channel principle (Andrew 2026-06-10): "
        f"nothing should block without offering and presenting the remedy. "
        f"Either add a Run:/Set:/Bypass:/edit-this-file path to the "
        f"deny-message, or — if this hook genuinely doesn't gate — add it "
        f"to _NON_GATING_HOOKS in this test."
    )


def test_meta_check_finds_known_gates():
    """Sanity: the meta-check must actually inspect gates we know about,
    not silently scan zero files. Three known gates with deny paths must
    appear in the file set."""
    inspected = {p.name for p in _hook_files()}
    expected_present = {
        "require-monitors-armed.sh",
        "require-briefing.sh",
        "check-pending-obligations.sh",
        "andrew-correction-attestation.sh",
    }
    missing = expected_present - inspected
    assert not missing, (
        f"meta-check is not inspecting known gate hooks: {missing}. "
        "Either the file set is too narrow or these hooks moved/renamed."
    )


def test_recovery_token_lexicon_is_not_trivially_matched():
    """Sanity: the lexicon must not match arbitrary text. If it matched
    everything, the test could pass on a gate that names no remedy."""
    benign_text = (
        "This is a comment that does not name any recovery path. "
        "It mentions hooks and gates abstractly but provides no command "
        "or escape. Just narrative description."
    )
    assert not _has_recovery_token(benign_text), (
        "recovery-token lexicon false-positives on benign narrative — tighten the lexicon"
    )
