"""Meta-check: every PreToolUse gate's deny-message must name an executable remedy path.

Closes pattern #2 from Andrew's 2026-06-10 PR-marathon teaching:

    "GATE-WITH-UNREACHABLE-REMEDY: three shapes tonight (CLI broken
    mid-rebase, detector event-names wrong, prereg gate blocking the
    prereg) — the generalizable fix is a meta-check that every gate
    deny-message names a path that can actually execute from where
    the caller is."

The failure shape: a gate fires "BLOCKED: do X to proceed" but X is one of:
- a CLI subcommand that no longer exists
- a command the gate itself blocks (catch-22)
- a hook that depends on the very subsystem the gate is protecting

This test catches the simpler half — gates whose deny-message contains NO
recognizable command at all (the "you're blocked, figure it out yourself"
shape). The semantic check (does X actually execute under the blocking
context) is harder and stays manual — but the lexical check rules out the
obvious silent-block failure mode.

## What counts as an "executable remedy path"

Any of these prefixes appearing somewhere in the deny-message body:
- `divineos <subcommand>` — substrate CLI invocations
- `git <subcommand>` — git operations
- `python <path>` / `python -m <module>` / `bash <path>` — script invocations
- `gh <subcommand>` — GitHub CLI
- `Bash(...)` / `Monitor(...)` / `Edit(...)` — harness tool invocations
- `touch <path>` / `rm <path>` / `mkdir <path>` — basic FS ops (often used
  to manipulate marker files)
- `export FOO=...` / `FOO=1 <command>` — env-var bypasses
- `<NAME>_BYPASS=1` / `<NAME>_SKIP_*=1` / `DIVINEOS_*=1` — documented bypass
  env vars
- `pytest <args>` — test invocations

## Maintenance

When adding a new gate, ensure its deny-message includes at least one of
these forms. The test will fail loudly if a new gate ships without a
remedy path, naming the offending file.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
HOOKS_DIR = REPO_ROOT / ".claude" / "hooks"

# Gates we test: PreToolUse hooks that can block tool execution. Identified
# by the convention `require-*.sh` / `check-*.sh` / `*-gate.sh` plus an
# explicit allowlist for hooks named differently.
GATE_PATTERNS = ("require-*.sh", "check-*.sh", "*-gate.sh")
EXPLICIT_GATES = [
    "deletion-discipline.sh",
    "andrew-correction-attestation.sh",
    "family-member-invocation-seal.sh",
    "compass-check.sh",
    "state-gravity-surface.sh",
]

# Hooks that are status surfaces (print info), NOT gates (don't block).
# These are exempt — printing state without a remedy is correct for them.
ALLOWLIST_NON_BLOCKING = {
    "ear-surface.sh",
    "ear-arm-instruction.sh",  # removed in PR #163; safe to keep in allowlist
    "arm-compaction-monitor-instruction.sh",
    "load-briefing.sh",
    "check-cleanup-period.sh",
    "session-checkpoint.sh",
    "session-start-sweep-stale-watchers.sh",
    "log-session-end.sh",
    "post-compact.sh",
    "pre-compact.sh",
    "post-response-audit.sh",  # has its own remedy-naming discipline
    "detect-correction.sh",
    "detect-hedge.sh",
    "detect-theater.sh",
    "pre-response-context.sh",
    "pre-tool-context.sh",
    "record-wisdom-read.sh",
    "verify-push-landed.sh",
    "run-tests.sh",
    "_lib.sh",
    # Stop-hook ear relauncher (silent, no message)
    "ear-auto-relaunch.sh",
}

# Remedy-form regex — matches any of the documented executable forms.
# Case-insensitive; multi-line aware via re.DOTALL when called.
REMEDY_FORMS = re.compile(
    r"""
    (?:
        # Substrate CLI
        \bdivineos\s+[a-z][a-z0-9_-]+
        # Git
        | \bgit\s+(?:ls-remote|push|pull|fetch|rebase|log|status|diff|add|commit|checkout|merge|rev-parse|branch|reset|stash|tag|show|clone|init|config|cherry-pick|reflog|worktree)
        # Python/Bash invocation
        | \bpython3?\s+(?:-m\s+)?[\w./_-]+
        | \bbash\s+[\w./_-]+
        # GitHub CLI
        | \bgh\s+[a-z][a-z-]+
        # Harness tool invocation
        | \b(?:Bash|Monitor|Edit|Write|Read|Grep|Glob|Task|Agent)\s*\(
        # Basic FS ops with a path
        | \b(?:touch|mkdir|rm)\s+[-\w./~$]+
        # Env-var bypass (NAME=1 ... or DIVINEOS_* / *_BYPASS etc.)
        | \b(?:DIVINEOS|AURA)_[A-Z_]+=
        | \b[A-Z][A-Z0-9_]+_(?:BYPASS|SKIP|ALLOW|OVERRIDE)=
        # Pytest
        | \bpytest\b
        # Source/dot-script
        | \bsource\s+[\w./-]+
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)


def _enumerate_gate_files() -> list[Path]:
    """Find every shell-hook file that looks like a gate (could exit non-zero
    to block) under .claude/hooks/."""
    seen: set[Path] = set()
    for pat in GATE_PATTERNS:
        for p in HOOKS_DIR.glob(pat):
            seen.add(p)
    for name in EXPLICIT_GATES:
        p = HOOKS_DIR / name
        if p.exists():
            seen.add(p)
    # Exclude allowlisted non-blocking surfaces.
    return sorted(p for p in seen if p.name not in ALLOWLIST_NON_BLOCKING)


def _hook_blocks(text: str) -> bool:
    """True if the hook can issue a blocking exit. We look for `exit 2`
    (the Claude Code block contract) or `exit 1` patterns. A hook that
    only `exit 0`s never blocks and is exempt.
    """
    return bool(re.search(r"\bexit\s+[12]\b", text))


def _has_remedy_form(text: str) -> bool:
    """True if the hook body contains at least one recognizable executable
    remedy form anywhere."""
    return bool(REMEDY_FORMS.search(text))


@pytest.fixture(scope="module")
def gate_files() -> list[Path]:
    files = _enumerate_gate_files()
    assert files, (
        "No gate files found under .claude/hooks/. The test's discovery "
        "globs may be wrong, or the hooks directory has been moved."
    )
    return files


def test_every_blocking_gate_has_at_least_one_remedy_form(gate_files: list[Path]) -> None:
    """Pattern #2 from Andrew 2026-06-10 PR-marathon: a blocking gate must
    name an executable path the caller can act on. A blocking gate with no
    recognizable command-form is the unreachable-remedy failure mode.
    """
    offenders: list[str] = []
    for p in gate_files:
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if not _hook_blocks(text):
            # Not a blocking gate; nothing to enforce.
            continue
        if not _has_remedy_form(text):
            offenders.append(p.name)
    assert not offenders, (
        "These blocking gates contain no recognizable executable remedy form "
        "in their bodies (the 'unreachable-remedy' failure shape Andrew named "
        "2026-06-10): " + ", ".join(offenders) + ". "
        "Add at least one of: divineos <cmd>, git <cmd>, python <path>, "
        "bash <path>, gh <cmd>, Bash(...) / Monitor(...) / Edit(...), "
        "touch/rm/mkdir <path>, or a documented env-var bypass."
    )


def test_discovery_finds_known_gates() -> None:
    """Sanity check: the discovery globs find at least the well-known
    blocking gates. If this fails, GATE_PATTERNS / EXPLICIT_GATES drifted
    from reality and the main test above could pass vacuously.
    """
    files = _enumerate_gate_files()
    names = {p.name for p in files}
    expected_some_of = {
        "require-briefing.sh",
        "require-goal.sh",
        "require-monitors-armed.sh",
        "check-pending-obligations.sh",
        "check-branch-on-push.sh",
        "gh-pr-merge-gate.sh",
    }
    found = expected_some_of & names
    assert len(found) >= 3, (
        f"Discovery globs found only {sorted(names)}; expected at least 3 of "
        f"{sorted(expected_some_of)}. The pattern coverage may have drifted."
    )
