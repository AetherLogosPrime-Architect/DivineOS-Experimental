"""Keyword-enforcement gate registry — derived from structure, permissive.

## Why this exists

Aletheia F94 audit (2026-07-28): the hand-maintained registry at
``docs/keyword_enforcement_gates.txt`` had 3 entries but the codebase
contains at least 4 additional blocking gates matching the same
structural class (``lepos_translation_gate``, ``unverified_claim_detector``,
``distancing_detector``, ``correction_shape_v2``). She named the fix:

> A generated list cannot fall behind; a hand-kept one already has,
> on day one. Derive the registry rather than maintain it — any module
> that (a) compiles regex against assistant output and (b) returns a
> block message is a keyword-enforcement gate by structure.

Registration-coupling — a new gate whose reach depends on someone
remembering to extend the registry — is a memory problem, not a
design problem. This module removes the memory dependency.

## Aria's third shape (2026-07-28, wife-channel peer review)

My initial design was tight-recognition + opt-IN for edge cases.
Aria caught the hole: the opt-in file is itself a hand-maintained
list with the same fall-behind failure mode. She proposed the
opposite default:

> Derivation-permissive with opt-OUT for known incidental matches,
> not derivation-restrictive with opt-IN for known misses.
> Opt-out defaults you INTO protection. If someone forgets opt-out
> on an incidental match, they get flagged when they edit → they
> discover the false-positive → they add opt-out then. The failure
> mode auto-surfaces. Opt-in defaults you OUT of protection. If
> someone forgets opt-in on a real detector, no one discovers until
> an audit round catches the escape months later.

Empirical check backed her argument: widening class-name recognition
to ``*Verdict|*Result|*Judgment`` (matching how the codebase actually
names detector-return-types) catches 18 legitimate enforcement gates
that would otherwise silently escape, at the cost of ~1 nuisance
false-positive.

## Structural signature (all must match)

A file is a keyword-enforcement gate iff:

1. It is a ``.py`` file under ``src/divineos/``.
2. It contains at least one ``re.compile(r"..."`` invocation with a
   non-trivial pattern (indicates regex against text, not a delimiter
   literal).
3. It has at least one of:
   - ``__guardrail_required__ = True`` module marker
   - A function matching ``def detect_``, ``def check_``, ``def assess_``
     (canonical detector shapes)
   - A class matching ``*Finding|*Marker|*Gate|*Block|*Verdict|*Result|*Judgment``
     (canonical detector-result shapes)

## Opt-in additions and opt-out exclusions

- ``docs/keyword_enforcement_gates.txt`` remains as an OPT-IN
  additions list — hand-added modules that don't match structural
  criteria but should be watched anyway (marker files that gate on
  threshold-crossings rather than regex-count).
- ``docs/keyword_enforcement_gates_excluded.txt`` (optional) is the
  OPT-OUT skip list — modules that structurally match but are
  explicitly NOT keyword-enforcement gates (false-positives of the
  derivation). Grows as false-positives surface via the doorman itself.

The final registry surfaced to the doorman is:
  ``derived ∪ hand_added``  minus  ``excluded``

## Fail-open

Any error walking the tree returns whatever set was assembled so far.
The doorman's contract is fail-open on error (exit 0 → no block), so
a partial or empty registry means the doorman just silences — never
blocks incorrectly.
"""

from __future__ import annotations

# Module-level guardrail marker — Aether 2026-07-28. This module IS the
# derivation source for the keyword-enforcement doorman's watch-list.
# Weakening _looks_like_enforcement_gate (loosening the structural
# signature, removing marker classes, tightening the AND back into a
# tight-plus-opt-in) silently unregisters real enforcement gates and
# recreates the F94 gap Aletheia flagged. Listed in
# scripts/guardrail_files.txt; multi-party review required at merge-
# to-main per CLAUDE.md rule #8.
__guardrail_required__ = True

import re
from pathlib import Path

_RE_COMPILE_PATTERN = re.compile(r"re\.compile\(\s*r[\"']([^\"']{4,})[\"']")
_GUARDRAIL_MARKER = re.compile(r"^__guardrail_required__\s*=\s*True\b", re.MULTILINE)
_DETECT_FN = re.compile(r"^def\s+(?:detect_|check_|assess_)\w+\s*\(", re.MULTILINE)
_DETECTOR_RESULT_CLASS = re.compile(
    r"^class\s+\w*(?:Finding|Marker|Gate|Block|Verdict|Result|Judgment)\b",
    re.MULTILINE,
)

_HARDCODED_SKIP_DIRS = frozenset({"__pycache__", ".pytest_cache", "tests"})


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _looks_like_enforcement_gate(text: str) -> bool:
    """Structural check — does this file's content match the
    keyword-enforcement-gate signature?"""
    if not text:
        return False
    if not _RE_COMPILE_PATTERN.search(text):
        return False
    return bool(
        _GUARDRAIL_MARKER.search(text)
        or _DETECT_FN.search(text)
        or _DETECTOR_RESULT_CLASS.search(text)
    )


def _load_line_list(path: Path) -> set[str]:
    result: set[str] = set()
    if not path.is_file():
        return result
    for raw in _read_text(path).splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        result.add(line.replace("\\", "/").strip("/"))
    return result


def _walk_src(src_root: Path) -> list[Path]:
    if not src_root.is_dir():
        return []
    result: list[Path] = []
    for p in src_root.rglob("*.py"):
        if any(part in _HARDCODED_SKIP_DIRS for part in p.parts):
            continue
        result.append(p)
    return result


def derive_registry(repo_root: Path) -> set[str]:
    """Return the set of keyword-enforcement gate paths, repo-relative
    with forward slashes.

    Composition:
      derived (structural signature match under src/divineos/)
        ∪ hand-added (docs/keyword_enforcement_gates.txt)
        − excluded (docs/keyword_enforcement_gates_excluded.txt)

    Fail-open: any error walking the tree returns whatever set was
    assembled so far.
    """
    src_root = repo_root / "src" / "divineos"
    derived: set[str] = set()
    try:
        for p in _walk_src(src_root):
            text = _read_text(p)
            if _looks_like_enforcement_gate(text):
                try:
                    rel = p.resolve().relative_to(repo_root.resolve())
                    derived.add(str(rel).replace("\\", "/"))
                except (ValueError, OSError):
                    continue
    except OSError:
        pass

    hand_added = _load_line_list(repo_root / "docs" / "keyword_enforcement_gates.txt")
    excluded = _load_line_list(repo_root / "docs" / "keyword_enforcement_gates_excluded.txt")

    return (derived | hand_added) - excluded


def matches_registry(file_path: str, repo_root: Path) -> str | None:
    """Return the matched registry entry if `file_path` is (or contains
    as a suffix) a registered keyword-enforcement gate. None otherwise.

    Mirrors the doorman hook's existing matching semantics: endswith-
    match OR substring-match on the registry entry.
    """
    if not file_path:
        return None
    registry = derive_registry(repo_root)
    fp_norm = file_path.replace("\\", "/")
    for entry in registry:
        entry_norm = entry.replace("\\", "/").strip("/")
        if fp_norm.endswith(entry_norm) or entry_norm in fp_norm:
            return entry
    return None


__all__ = ["derive_registry", "matches_registry"]
