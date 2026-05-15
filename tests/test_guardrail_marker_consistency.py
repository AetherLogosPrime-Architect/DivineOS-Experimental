"""Class-fix test for Aletheia Finding 48.

Andrew + Aletheia named the pattern 2026-05-14 night: the thin-doorman
refactor moved load-bearing self-enforcement logic from guardrailed
``.claude/hooks/*.sh`` files into NON-guardrailed ``src/divineos/core/*.py``
files. The architectural move was sound; the guardrail discipline
did not follow the logic across the file migration. Adversary
modifying these modules could silently disable post-response
detection without any co-sign required.

Finding 41 had been the same class-failure at smaller scope. The
fix then was to add ``pre_tool_use_gate.py`` to the guardrail list.
The class-fix never landed, so when the next refactor created five
more files with the same shape, no structural mechanism caught it.

THIS TEST IS THE CLASS-FIX.

## Contract

Every Python file in ``src/divineos/`` that contains the line
``__guardrail_required__ = True`` MUST be listed in
``scripts/guardrail_files.txt``. The marker travels with the file
across refactors. If someone splits a guardrailed file into two,
the marker goes with the load-bearing half. If they create a new
load-bearing file (extracting from a hook, building a new gate,
etc.), they mark it with ``__guardrail_required__ = True`` and CI
catches if they forget to add the path to the guardrail list.

The test is symmetric: if a module is listed in the guardrail file
but lacks the marker, that's also a finding (silent drift in the
other direction).
"""

from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    """The project root — contains src/, scripts/, tests/."""
    return Path(__file__).resolve().parent.parent


def _read_guardrail_list() -> set[str]:
    """Return the set of paths in scripts/guardrail_files.txt,
    normalized to forward-slash form."""
    path = _repo_root() / "scripts" / "guardrail_files.txt"
    paths: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Normalize Windows backslashes to forward slashes for matching.
        paths.add(line.replace("\\", "/"))
    return paths


def _scan_marked_modules() -> set[str]:
    """Walk src/ recursively; return forward-slash repo-relative
    paths of every .py file that contains the marker line."""
    src = _repo_root() / "src"
    marker_line = "__guardrail_required__ = True"
    marked: set[str] = set()
    for py_file in src.rglob("*.py"):
        try:
            text = py_file.read_text(encoding="utf-8")
        except OSError:
            continue
        if marker_line in text:
            rel = py_file.relative_to(_repo_root())
            marked.add(str(rel).replace("\\", "/"))
    return marked


def test_every_marked_module_is_in_guardrail_list() -> None:
    """LOAD-BEARING: every module with __guardrail_required__ = True
    must be in scripts/guardrail_files.txt.

    This is the class-fix for Aletheia Finding 41 + Finding 48.
    A new self-enforcement module created in any future refactor,
    marked with this attribute, will fail CI if the path doesn't
    get added to the guardrail list. The discipline propagates
    across refactors structurally, not by convention.
    """
    marked = _scan_marked_modules()
    guardrail = _read_guardrail_list()
    missing = marked - guardrail
    assert not missing, (
        f"Modules marked __guardrail_required__ = True but NOT in "
        f"scripts/guardrail_files.txt: {sorted(missing)}.\n\n"
        f"Either add each path to scripts/guardrail_files.txt OR "
        f"remove the marker (and explain why the module no longer "
        f"needs multi-party-review protection)."
    )


def test_every_python_path_in_guardrail_list_has_marker() -> None:
    """Symmetry check: every src/*.py path listed in the guardrail
    file must contain the marker. Prevents the inverse drift —
    silently removing the marker while leaving the path listed,
    which would be a confusing half-state.

    Only checks src/*.py entries; other guardrail file types (docs,
    scripts, etc.) don't have Python markers."""
    guardrail = _read_guardrail_list()
    marker_line = "__guardrail_required__ = True"
    missing_markers: list[str] = []
    for path_str in guardrail:
        if not path_str.startswith("src/") or not path_str.endswith(".py"):
            continue
        abs_path = _repo_root() / path_str
        if not abs_path.exists():
            # Path in guardrail list but file doesn't exist —
            # surfaces stale entries.
            missing_markers.append(f"{path_str} (file does not exist)")
            continue
        try:
            text = abs_path.read_text(encoding="utf-8")
        except OSError:
            missing_markers.append(f"{path_str} (could not read)")
            continue
        if marker_line not in text:
            missing_markers.append(path_str)
    assert not missing_markers, (
        f"Guardrail-listed Python files missing __guardrail_required__ marker: "
        f"{sorted(missing_markers)}.\n\n"
        f"Either add the marker to each file OR remove the path from "
        f"scripts/guardrail_files.txt (and explain why the module no "
        f"longer needs multi-party-review protection)."
    )


def test_finding_48_modules_specifically_protected() -> None:
    """Regression-pin for the specific 7 modules Aletheia named in
    Finding 48. If any of these get unmarked + unlisted in a future
    refactor, the test fails loudly naming the regression."""
    finding_48_paths = {
        "src/divineos/core/operating_loop_audit.py",
        "src/divineos/core/pre_response_context.py",
        "src/divineos/core/theater_audit.py",
        "src/divineos/core/hedge_audit.py",
        "src/divineos/core/session_start.py",
        "src/divineos/core/briefing_freshness.py",
        "src/divineos/core/structural_fix_tracker.py",
    }
    marked = _scan_marked_modules()
    guardrail = _read_guardrail_list()
    for path in finding_48_paths:
        assert path in marked, f"Finding 48 module {path} lacks __guardrail_required__ marker"
        assert path in guardrail, f"Finding 48 module {path} not in guardrail list"
