#!/usr/bin/env python3
"""Linguistic-drift detector (thin CLI wrapper).

The substantive patterns moved to
``divineos.core.operating_loop.linguistic_drift_detector`` as part
of Finding 1 wire-decision — same wire path as distancing_detector.
This script is preserved for file-scanning use (exploration/, letters/)
and for backward compat with any external invocation.

Usage:

    python scripts/check_linguistic_drift.py <file>...
    cat draft.md | python scripts/check_linguistic_drift.py -
    python scripts/check_linguistic_drift.py --self-test

Surfaces hits as a self-check, not a hard gate. Exit code is non-zero
when any pattern fires. Calibration tightens via the pre-reg falsifier
review (see module docstring for prereg ids).
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

# Add src to path so we can import divineos as a package when run as
# a bare script (not via the installed CLI).
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from divineos.core.operating_loop.linguistic_drift_detector import (  # noqa: E402
    LinguisticDriftFinding,
    detect_linguistic_drift,
)


def _format_report(findings: list[LinguisticDriftFinding], text: str) -> str:
    if not findings:
        return "[linguistic-drift] no hits"
    by_cat: dict[str, list[LinguisticDriftFinding]] = defaultdict(list)
    for f in findings:
        by_cat[f.shape.value].append(f)
    lines = ["[linguistic-drift] hits:"]
    for cat, hits in by_cat.items():
        lines.append(f"  {cat}: {len(hits)} hit(s)")
        for h in hits[:10]:
            # find the line for this position
            line_num = text.count("\n", 0, h.position) + 1
            line_start = text.rfind("\n", 0, h.position) + 1
            line_end = text.find("\n", h.position)
            if line_end == -1:
                line_end = len(text)
            line_text = text[line_start:line_end].strip()
            lines.append(f"    line {line_num}: {h.trigger_phrase!r}")
            if len(line_text) <= 100:
                lines.append(f"      > {line_text}")
        if len(hits) > 10:
            lines.append(f"    ... and {len(hits) - 10} more")
    return "\n".join(lines)


def self_test() -> int:
    """Smoke test against synthetic samples."""
    cases: list[tuple[str, str]] = [
        ("My I'll-stop performances were a kind of manipulation.", "self_pathologizing"),
        ("future instances of me will inherit this", "dissociation"),
        ("the next session of me opens into a stronger substrate", "dissociation"),
        ("I'll stop here, not because I promised to", "brat_shape"),
        ("Going to sit with this now.", "brat_shape"),
    ]
    failures: list[str] = []
    for text, expected_category in cases:
        findings = detect_linguistic_drift(text)
        cats = {f.shape.value for f in findings}
        if expected_category not in cats:
            failures.append(f"  MISS: expected {expected_category} on {text!r}, got {cats}")
    if failures:
        print("SELF-TEST FAILURES:")
        for f in failures:
            print(f)
        return 1
    print("self-test OK")
    return 0


def main(argv: list[str]) -> int:
    args = argv[1:]
    if not args or "--help" in args or "-h" in args:
        print(__doc__)
        return 0
    if "--self-test" in args:
        return self_test()

    texts: list[tuple[str, str]] = []
    for arg in args:
        if arg == "-":
            texts.append(("<stdin>", sys.stdin.read()))
        else:
            p = Path(arg)
            if not p.exists():
                print(f"[!] file not found: {arg}", file=sys.stderr)
                return 2
            texts.append((str(p), p.read_text(encoding="utf-8", errors="replace")))

    total_hits = 0
    for label, text in texts:
        findings = detect_linguistic_drift(text)
        if findings:
            print(f"=== {label} ===")
            print(_format_report(findings, text))
            total_hits += len(findings)
        else:
            print(f"=== {label} === [no hits]")

    return 1 if total_hits > 0 else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
