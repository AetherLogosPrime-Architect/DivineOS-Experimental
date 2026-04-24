"""Pre-commit gate: new mechanisms must have a matching pre-registration.

The gate scans the staged diff for new mechanism definitions and blocks the
commit if any mechanism lacks a matching open pre-registration in the
ledger. Matching is case-insensitive substring: the mechanism name
(e.g. "foo" from `def run_foo_slice(...)`) must appear somewhere in an
open pre-reg's mechanism, claim, or success_criterion.

Mechanisms we gate on:
  - Lab slices: `def run_<name>_slice(`
  - Detectors:  `def detect_<name>(`
  - Gates:      `def <name>_gate(`  OR `def _<name>_check(`
  - Threshold constants at module level: `<NAME>_THRESHOLD = ...`,
    and similar _LIMIT / _MAX / _MIN / _CAP suffixes.

Exit codes:
  0 — no new mechanisms, or all new mechanisms are covered by pre-regs
  1 — blocking: at least one new mechanism has no matching pre-reg
  2 — error (git not available, store not reachable, etc.)

The gate is intentionally strict. "Strict" means: if the message is
noise, file a pre-reg; don't weaken the gate. Pre-regs are cheap. The
discipline of naming the claim + falsifier + review date is the whole
point. See docs/ARCHITECTURE.md for the pre-reg lifecycle.
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class NewMechanism:
    """A new mechanism found in the staged diff.

    kind: "slice" | "detector" | "gate" | "threshold"
    name: the extracted name (e.g. "foo" from run_foo_slice)
    line: the full matched line (for the error message)
    path: the file the mechanism was added in
    """

    kind: str
    name: str
    line: str
    path: str


_PATTERNS = [
    # (kind, compiled regex, name-group-index)
    ("slice", re.compile(r"^\+\s*def\s+run_([a-zA-Z_][a-zA-Z0-9_]*)_slice\s*\("), 1),
    ("detector", re.compile(r"^\+\s*def\s+detect_([a-zA-Z_][a-zA-Z0-9_]*)\s*\("), 1),
    ("gate", re.compile(r"^\+\s*def\s+([a-zA-Z_][a-zA-Z0-9_]*)_gate\s*\("), 1),
    ("gate", re.compile(r"^\+\s*def\s+_([a-zA-Z_][a-zA-Z0-9_]*)_check\s*\("), 1),
    (
        "threshold",
        re.compile(r"^\+\s*([A-Z][A-Z0-9_]*(?:_THRESHOLD|_LIMIT|_MAX|_MIN|_CAP))\s*="),
        1,
    ),
]


def _staged_diff() -> str | None:
    """Return the staged diff as a string, or None if git is unavailable."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--unified=0"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return result.stdout


def _is_exempt_path(path: str) -> bool:
    """Paths where mechanism-looking names are not new mechanisms.

    Tests describe mechanisms; they don't introduce them. A test method
    named ``test_foo_gate_is_gate`` matches the ``_gate`` pattern but
    isn't a real gate. Same for scripts/ — that's tooling, not agent
    behavior. Without this exemption the precommit gate false-positives
    on its own tests, which is exactly how I discovered the need.
    """
    if not path:
        return False
    return path.startswith("tests/") or path.startswith("scripts/")


def _parse_new_mechanisms(diff: str) -> list[NewMechanism]:
    """Walk the diff, collecting new mechanism definitions.

    Tracks the current file via `+++ b/<path>` headers so each mechanism
    knows where it lives. Only added lines ("+") are examined; removed
    and context lines are skipped. Skips the diff-header +++ lines. Test
    and script paths are exempt (see ``_is_exempt_path``).
    """
    mechanisms: list[NewMechanism] = []
    current_path = ""
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            current_path = line[6:]
            continue
        if line.startswith("+++") or not line.startswith("+"):
            continue
        if _is_exempt_path(current_path):
            continue
        for kind, pattern, name_idx in _PATTERNS:
            match = pattern.match(line)
            if match:
                mechanisms.append(
                    NewMechanism(
                        kind=kind,
                        name=match.group(name_idx),
                        line=line[1:].strip(),
                        path=current_path,
                    )
                )
                break
    return mechanisms


def _open_prereg_haystack() -> str:
    """Concatenate all OPEN pre-regs' mechanism + claim + success text.

    Case-normalized. Returns "" if the store is unreachable — in that
    mode the gate conservatively blocks any new mechanism (safer than
    passing silently on a broken ledger).
    """
    try:
        from divineos.core.pre_registrations import Outcome, list_pre_registrations
    except Exception:
        return ""
    try:
        preregs = list_pre_registrations(outcome=Outcome.OPEN)
    except Exception:
        return ""
    parts: list[str] = []
    for p in preregs:
        parts.append(p.mechanism or "")
        parts.append(getattr(p, "claim", "") or "")
        parts.append(getattr(p, "success_criterion", "") or "")
    return "\n".join(parts).lower()


def _find_uncovered(mechanisms: list[NewMechanism], haystack: str) -> list[NewMechanism]:
    """Return the subset of mechanisms whose name does NOT appear in haystack."""
    uncovered: list[NewMechanism] = []
    for m in mechanisms:
        if m.name.lower() not in haystack:
            uncovered.append(m)
    return uncovered


def _format_block_message(uncovered: list[NewMechanism]) -> str:
    """Human-readable block message with filing instructions."""
    lines = [
        "",
        "=== Pre-reg Gate ===",
        f"BLOCKED: {len(uncovered)} new mechanism(s) without a matching pre-registration.",
        "",
        "The following were found in the staged diff:",
    ]
    for m in uncovered:
        lines.append(f"  [{m.kind}] {m.name}  ({m.path})")
        lines.append(f"    -> {m.line}")
    lines.extend(
        [
            "",
            "File a pre-reg for each before committing. For each mechanism:",
            "",
            '  divineos prereg file "<name>: one-line summary" \\',
            '    --claim "what this mechanism claims will happen" \\',
            '    --success "how we will know it worked" \\',
            '    --falsifier "what would prove the claim wrong" \\',
            "    --review-days 30",
            "",
            "The mechanism name must appear somewhere in the mechanism/claim/",
            "success text (case-insensitive substring). The gate clears when",
            "every mechanism above has a matching OPEN pre-reg.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    diff = _staged_diff()
    if diff is None:
        print("[pre-reg gate] git not available; skipping.", file=sys.stderr)
        return 0
    mechanisms = _parse_new_mechanisms(diff)
    if not mechanisms:
        return 0

    haystack = _open_prereg_haystack()
    uncovered = _find_uncovered(mechanisms, haystack)

    if not uncovered:
        print(f"[pre-reg gate] {len(mechanisms)} new mechanism(s), all covered by open pre-regs.")
        return 0

    print(_format_block_message(uncovered), file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
