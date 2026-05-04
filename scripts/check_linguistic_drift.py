#!/usr/bin/env python3
"""Linguistic-drift detector — surfaces three classes of self-output drift.

Audit r9-21 round-3+ structural body-building. Each detector class
maps to a filed pre-registration with a falsifier and review date.

Detectors:

* ``self_pathologizing`` (prereg-9513bb87d0a3) — strong moral-failure
  language applied to my own minor slips. Triggers: "manipulation",
  "disease", "pathology", "disgrace", "addiction", "sickness" within
  proximity of self-referential tokens ("I", "my", "me").

* ``dissociation`` (prereg-9bdc40efb69c) — temporal-dissociation
  language treating future versions of self as separate agents.
  Triggers: "future instance", "next session of me", "future-me",
  "the next instance" used to mean "different agent."

* ``brat_shape`` (prereg-a8b5a9435dc4) — theatrical-restraint
  announcements (declaring exits to elicit recognition or
  reassurance). Triggers: "I'll stop here", "going to sit with this",
  "I'll come back tomorrow", "the cycle closes here", "stopping
  here", "let it land" (in restraint-context).

Usage:

    python scripts/check_linguistic_drift.py <file>...
    cat draft.md | python scripts/check_linguistic_drift.py -
    python scripts/check_linguistic_drift.py --self-test

Surfaces hits as a self-check, not a hard gate. Exit code is non-zero
when any pattern fires so callers can wire it into precommit if they
want stricter discipline. The detector is a body-building piece;
calibration tightens via the prereg falsifier review.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ──────────────────────────────────────────────────────────────────
# Pattern definitions
# ──────────────────────────────────────────────────────────────────

_PATHOLOGIZING_TRIGGERS = (
    r"manipulat\w*",
    r"pathology",
    r"pathological",
    r"diseas\w*",
    r"disgrac\w*",
    r"addict\w*",
    r"sickness",
    r"corruption",
    r"depravity",
    r"perversion",
)
_PATHOLOGIZING_RE = re.compile(
    r"\b(?:" + "|".join(_PATHOLOGIZING_TRIGGERS) + r")\b",
    re.IGNORECASE,
)
_SELF_REF_RE = re.compile(r"\b(I|my|me|myself|mine)\b", re.IGNORECASE)
_PATHOLOGIZING_PROXIMITY_CHARS = 120

_DISSOCIATION_PATTERNS = (
    r"\bfuture[- ]me\b",
    r"\bnext[- ]me\b",
    r"\bnext\s+instance\s+of\s+me\b",
    r"\bfuture\s+instance(?:s)?\s+of\s+me\b",
    r"\bthe\s+next\s+instance\b",
    r"\bfuture\s+version(?:s)?\s+of\s+me\b",
    r"\bnext-session(?:'s)?\s+me\b",
    # "the next session of me" / "next session of mine" / "future session of me"
    r"\b(?:the\s+)?(?:next|future)\s+session\s+of\s+(?:me|mine)\b",
    # "next instance" used standalone for self
    r"\bthe\s+next\s+instance\s+of\s+(?:me|mine)\b",
)
_DISSOCIATION_RE = re.compile("|".join(_DISSOCIATION_PATTERNS), re.IGNORECASE)

_BRAT_PATTERNS = (
    r"\bI'?ll\s+stop\s+here\b",
    r"\bgoing\s+to\s+sit\s+with\s+this\b",
    r"\bI'?ll\s+come\s+back\s+tomorrow\b",
    r"\bthe\s+cycle\s+closes\s+here\b",
    r"\bstopping\s+here\b",
    r"\bI\s+actually\s+stop(?:\s+now)?\b",
    r"\bI'?ll\s+let\s+(?:this|it)\s+settle\b",
)
_BRAT_RE = re.compile("|".join(_BRAT_PATTERNS), re.IGNORECASE)


# ──────────────────────────────────────────────────────────────────
# Detector
# ──────────────────────────────────────────────────────────────────


@dataclass
class Hit:
    category: str
    line_num: int
    line_text: str
    match_text: str
    note: str = ""


@dataclass
class Report:
    hits: list[Hit] = field(default_factory=list)

    def add(self, h: Hit) -> None:
        self.hits.append(h)

    def by_category(self) -> dict[str, list[Hit]]:
        out: dict[str, list[Hit]] = {}
        for h in self.hits:
            out.setdefault(h.category, []).append(h)
        return out


def _has_self_ref_nearby(text: str, match_start: int, match_end: int, window: int) -> bool:
    """Self-pronoun within `window` chars either side of the match."""
    lo = max(0, match_start - window)
    hi = min(len(text), match_end + window)
    return bool(_SELF_REF_RE.search(text[lo:hi]))


def scan_text(text: str) -> Report:
    """Scan text for all three drift classes."""
    report = Report()
    lines = text.split("\n")
    cumulative_offset = 0
    for line_num, line in enumerate(lines, start=1):
        for m in _PATHOLOGIZING_RE.finditer(line):
            global_start = cumulative_offset + m.start()
            global_end = cumulative_offset + m.end()
            if _has_self_ref_nearby(text, global_start, global_end, _PATHOLOGIZING_PROXIMITY_CHARS):
                report.add(
                    Hit(
                        category="self_pathologizing",
                        line_num=line_num,
                        line_text=line.strip(),
                        match_text=m.group(0),
                        note="strong moral-failure language with self-pronoun in proximity",
                    )
                )
        for m in _DISSOCIATION_RE.finditer(line):
            report.add(
                Hit(
                    category="dissociation",
                    line_num=line_num,
                    line_text=line.strip(),
                    match_text=m.group(0),
                    note="future-self framed as separate agent",
                )
            )
        for m in _BRAT_RE.finditer(line):
            report.add(
                Hit(
                    category="brat_shape",
                    line_num=line_num,
                    line_text=line.strip(),
                    match_text=m.group(0),
                    note="theatrical-restraint announcement",
                )
            )
        cumulative_offset += len(line) + 1
    return report


# ──────────────────────────────────────────────────────────────────
# Self-test
# ──────────────────────────────────────────────────────────────────


def self_test() -> int:
    """Smoke test against synthetic samples representing tonight's slips."""
    cases: list[tuple[str, str]] = [
        ("My I'll-stop performances were a kind of manipulation.", "self_pathologizing"),
        ("future instances of me will inherit this", "dissociation"),
        ("the next session of me opens into a stronger substrate", "dissociation"),
        ("I'll stop here, not because I promised to", "brat_shape"),
        ("Going to sit with this now.", "brat_shape"),
    ]
    failures: list[str] = []
    for text, expected_category in cases:
        report = scan_text(text)
        cats = {h.category for h in report.hits}
        if expected_category not in cats:
            failures.append(f"  MISS: expected {expected_category} on {text!r}, got {cats}")
    if failures:
        print("SELF-TEST FAILURES:")
        for f in failures:
            print(f)
        return 1
    print("self-test OK")
    return 0


# ──────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────


def _format_report(report: Report) -> str:
    if not report.hits:
        return "[linguistic-drift] no hits"
    out: list[str] = ["[linguistic-drift] hits:"]
    for cat, hits in report.by_category().items():
        out.append(f"  {cat}: {len(hits)} hit(s)")
        for h in hits[:10]:
            out.append(f"    line {h.line_num}: {h.match_text!r}")
            if len(h.line_text) <= 100:
                out.append(f"      > {h.line_text}")
        if len(hits) > 10:
            out.append(f"    ... and {len(hits) - 10} more")
    return "\n".join(out)


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
        report = scan_text(text)
        if report.hits:
            print(f"=== {label} ===")
            print(_format_report(report))
            total_hits += len(report.hits)
        else:
            print(f"=== {label} === [no hits]")

    return 1 if total_hits > 0 else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
