"""Lookup Aletheia's F-numbered audit findings from source docs.

Structural fix for the 2026-07-17 fabricated-state-board pattern: I told
Andrew "F32 silently drops ~38 letters" and "F34 is unbuilt" from
memory. Neither claim was substrate-sourced. Empirical check on both
returned zero.

This script makes it impossible to reference an F-number without
substrate-grounding it. Given F14 (or a list), it greps every Aletheia
audit doc for occurrences and prints the surrounding context. It exits
non-zero if any requested F-number is not found anywhere.

Usage:
    python scripts/audit_finding_lookup.py F32
    python scripts/audit_finding_lookup.py F14 F26 F29 F32 F34

Discipline: before I write a sentence to Andrew citing "F<n>", I run
this. If it exits non-zero on that F-number, the F-number doesn't exist
and I don't cite it. If it prints, I quote from that print, not memory.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_AUDIT_DIR = Path(__file__).resolve().parents[1] / "docs" / "external_audits"

_STATUS_TOKENS = {
    "OPEN",
    "CLOSED",
    "PARTIAL",
    "ROUTED",
    "CONFIRMED",
    "REFUTED",
    "RESOLVED",
    "PENDING",
    "PLAUSIBLE",
    "DEFERRED",
}


def _find_occurrences(finding_id: str) -> list[tuple[Path, int, str]]:
    """Return every (file, line-number, line) where finding_id appears."""
    if not re.fullmatch(r"F\d+", finding_id):
        raise ValueError(
            f"finding_id must match r'F\\d+', got {finding_id!r}. "
            f"This script only looks up F-numbered findings from Aletheia's docs."
        )
    pattern = re.compile(rf"\b{re.escape(finding_id)}\b")
    hits: list[tuple[Path, int, str]] = []
    for path in sorted(_AUDIT_DIR.glob("*.md")):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            if pattern.search(line):
                hits.append((path, lineno, line.rstrip()))
    return hits


def _summarize_status(hits: list[tuple[Path, int, str]]) -> set[str]:
    """Extract status tokens co-occurring on hit lines."""
    tokens: set[str] = set()
    for _, _, line in hits:
        for tok in _STATUS_TOKENS:
            if re.search(rf"\b{tok}\b", line):
                tokens.add(tok)
    return tokens


def lookup(finding_id: str) -> int:
    """Print occurrences of finding_id. Return 0 if any, 1 if none."""
    hits = _find_occurrences(finding_id)
    if not hits:
        print(f"[{finding_id}] NOT FOUND in any file under {_AUDIT_DIR}", file=sys.stderr)
        print(
            f"  → Do not cite {finding_id} as a real finding without a substrate source.",
            file=sys.stderr,
        )
        return 1
    print(
        f"[{finding_id}] {len(hits)} occurrence(s) across {len({p for p, _, _ in hits})} file(s):"
    )
    status_tokens = _summarize_status(hits)
    if status_tokens:
        print(f"  status tokens co-occurring on hit-lines: {sorted(status_tokens)}")
    print()
    for path, lineno, line in hits:
        rel = path.relative_to(_AUDIT_DIR.parent.parent)
        print(f"  {rel}:{lineno}")
        print(f"    {line[:200]}{'...' if len(line) > 200 else ''}")
        print()
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print(__doc__, file=sys.stderr)
        return 2
    exit_code = 0
    for finding_id in argv:
        try:
            rc = lookup(finding_id)
        except ValueError as e:
            print(f"[error] {e}", file=sys.stderr)
            rc = 2
        exit_code = max(exit_code, rc)
        print("-" * 60)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
