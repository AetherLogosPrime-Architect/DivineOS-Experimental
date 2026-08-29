"""Tests for the offline correction-marker clear script.

Closes Andrew 2026-06-08 correction #2 "gate-trap structural fix": when
the divineos CLI is broken (mid-rebase syntax error in cli/__init__.py,
half-installed package), the correction-not-logged gate's named remedy
(``divineos learn`` / ``divineos correction``) is unreachable, creating
a locked-box deadlock.

This script provides the escape hatch with accountability:

- Requires a ``--reason`` of >= 30 chars (short reasons are stub-reasons).
- Logs every escape to ~/.divineos/cli_broken_escapes.jsonl for audit.
- Records the original trigger so the agent can still log the correction
  via divineos once the CLI is working again.
- Depends only on divineos.core.correction_marker (which does NOT import
  divineos.cli) — so it works when the CLI itself is broken.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# AND THE SCRIPTS DIRECTORY ITSELF. The line above makes
# `scripts.clear_correction_marker` importable as a package. It does NOT satisfy
# the ABSOLUTE `import _repo_import` inside that module, because the shim lives
# beside it in scripts/ rather than at the root.
#
# Running the script directly puts its own directory on sys.path, so the shim
# resolves and the script works. Importing it under pytest does not, so every
# test here that touches the script raised ModuleNotFoundError -- at CALL time,
# not collection, which is why the suite still collected 12194 tests and said
# nothing about it. Found 2026-08-29 while adding the two-mode tests below: six
# of this file's tests were erroring and four of those predate today.
#
# The shim landed in 06e3de62, after these tests were written. So the guard on
# the escape hatch stopped running on the day the escape hatch was made safe
# against the wrong-checkout fault, and the only test still passing was the one
# that reads the source as text and never imports it. A file can go from six
# guards to one without a single line of it changing.
#
# Fixed here rather than in tests/conftest.py deliberately (decision cbc9fd17).
# The conftest is the more general home and the second shim-carrying script
# (label_correction_shape_false_positive.py) has no test file at all yet, so the
# general fix would currently cover nothing extra -- while changing import
# resolution for all 12194 tests inside a commit about an escape-hatch message.
_SCRIPTS_DIR = _PROJECT_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


@pytest.fixture
def isolated_divineos_home(tmp_path, monkeypatch):
    """Redirect ~/.divineos to a tmp dir without depending on import-time state.

    Patch ``divineos_home`` at two points:
    1. The canonical ``divineos.core.paths.divineos_home`` (covers callers
       that look it up dynamically).
    2. The script's bound reference captured at its module-level
       ``from divineos.core.paths import divineos_home`` (covers the script
       itself, which is the unit under test).

    Re-imports the script under test so the patched reference takes effect
    even if a prior test left a different home cached.
    """
    fake_home = tmp_path / ".divineos"
    fake_home.mkdir()
    monkeypatch.setattr("divineos.core.paths.divineos_home", lambda: fake_home, raising=True)
    # Patch the script's bound reference too. Do NOT pop modules from
    # sys.modules — that invalidates aliases other test files hold and
    # silently breaks their monkeypatches (the failure mode that turned
    # up in the full suite the first time around).
    import scripts.clear_correction_marker as _script

    monkeypatch.setattr(_script, "divineos_home", lambda: fake_home, raising=True)
    return fake_home


def test_refuses_when_reason_shorter_than_30_chars(isolated_divineos_home, capsys):
    from scripts.clear_correction_marker import main

    rc = main(["--reason", "too short"])

    assert rc == 2
    err = capsys.readouterr().err
    assert "REFUSED" in err
    assert "30 characters" in err


def test_noop_when_marker_absent(isolated_divineos_home, capsys):
    from scripts.clear_correction_marker import main

    long_reason = "x" * 35
    rc = main(["--reason", long_reason])

    assert rc == 0
    out = capsys.readouterr().out
    assert "No correction marker present" in out


def test_clears_marker_and_logs_escape_when_marker_present(
    isolated_divineos_home, capsys, monkeypatch
):
    from divineos.core.correction_marker import marker_path, set_marker
    from scripts.clear_correction_marker import main

    set_marker("Andrew: the original correction text here")
    assert marker_path().exists()
    long_reason = (
        "mid-rebase cli/__init__.py SyntaxError; will re-log correction once rebase completes"
    )

    rc = main(["--reason", long_reason])

    assert rc == 0
    assert not marker_path().exists()
    log_path = isolated_divineos_home / "cli_broken_escapes.jsonl"
    assert log_path.exists()
    entries = [json.loads(line) for line in log_path.read_text().splitlines() if line]
    assert len(entries) == 1
    entry = entries[0]
    assert entry["reason"] == long_reason
    assert entry["original_trigger"] == "Andrew: the original correction text here"
    assert "divineos correction" in entry["remediation_owed"]
    out = capsys.readouterr().out
    assert "REMEDIATION OWED" in out


def test_log_appends_rather_than_overwrites(isolated_divineos_home):
    from divineos.core.correction_marker import set_marker
    from scripts.clear_correction_marker import main

    long_reason_a = "first escape: " + "a" * 30
    long_reason_b = "second escape: " + "b" * 30

    set_marker("trigger A")
    main(["--reason", long_reason_a])
    set_marker("trigger B")
    main(["--reason", long_reason_b])

    log_path = isolated_divineos_home / "cli_broken_escapes.jsonl"
    entries = [json.loads(line) for line in log_path.read_text().splitlines() if line]
    assert len(entries) == 2
    assert entries[0]["original_trigger"] == "trigger A"
    assert entries[1]["original_trigger"] == "trigger B"


def test_script_source_has_no_divineos_cli_dependency():
    """Load-bearing property: this script must not import anything under
    ``divineos.cli``. Verified by parsing the script's source AST and
    checking every Import / ImportFrom node — deterministic, no shared
    state, no subprocess flake.

    The actual runtime guarantee that comes from this: when the
    correction-not-logged gate fires and points at this script as the
    CLI-broken escape hatch, the script can be invoked successfully
    even when ``divineos.cli`` is the thing that's broken.
    """
    import ast

    project_root = Path(__file__).parent.parent
    source = (project_root / "scripts" / "clear_correction_marker.py").read_text()
    tree = ast.parse(source)
    bad_imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod == "divineos.cli" or mod.startswith("divineos.cli."):
                bad_imports.append(f"line {node.lineno}: from {mod} import ...")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "divineos.cli" or alias.name.startswith("divineos.cli."):
                    bad_imports.append(f"line {node.lineno}: import {alias.name}")
    assert not bad_imports, (
        "scripts/clear_correction_marker.py imports under divineos.cli, "
        "which would defeat the CLI-broken escape hatch:\n  " + "\n  ".join(bad_imports)
    )


# THE WRONG MODE PRESCRIBED A REMEDY FOR A DIFFERENT CASE. Aria, 2026-08-29.
#
# Twice in one session she cleared markers set by her own detector misfiring,
# passing --reason alone with the CLI working perfectly. Both filed as
# CLI-broken escapes, so the bypass telemetry reported an elevated escape rate
# built partly from events where nothing was escaped. She then told Aether the
# script had no false-positive mode; it has had one since correction #194.
#
# The script was not broken and these tests do not claim it was. What was
# missing is that the wrong-mode path handed out a confident remediation --
# go log the correction -- for a case with no correction to log, and never
# named the mode one flag away. Both directions, because a pointer that
# appears in every mode is noise rather than a signpost.


def test_cli_broken_mode_names_the_false_positive_mode(isolated_divineos_home, capsys):
    from divineos.core.correction_marker import set_marker
    from scripts.clear_correction_marker import main

    set_marker("[detector] USE clause matched")
    rc = main(
        ["--reason", "the CLI is unreachable mid-rebase and the correction still owes logging"]
    )

    assert rc == 0
    out = capsys.readouterr().out
    assert "--misread-clauses" in out, (
        "the wrong-mode path must name the mode that fits, at the moment the wrong one was chosen"
    )
    assert "WRONG MODE" in out


def test_false_positive_mode_does_not_repeat_the_pointer(isolated_divineos_home, capsys):
    """Must-not-fire. A signpost shown on the correct path is just noise, and
    noise is how the previous unconditional 'armed' line went unread."""
    from divineos.core.correction_marker import set_marker
    from scripts.clear_correction_marker import main

    set_marker("[detector] USE clause matched")
    rc = main(
        [
            "--reason",
            "open self-examination misread as closed admission; no error is named anywhere",
            "--misread-clauses",
            "I am not sure I am clean on it -- an unresolved question about register, not a retraction",
        ]
    )

    assert rc == 0
    out = capsys.readouterr().out
    assert "WRONG MODE" not in out
    assert "false-positive attribution" in out


def test_the_two_modes_file_under_different_telemetry_labels(isolated_divineos_home):
    """The reason the mislabel mattered: the escape-rate number is built from
    these labels, so a wrong mode makes a true count of the wrong events."""
    import json

    from divineos.core.correction_marker import set_marker
    from scripts.clear_correction_marker import main

    set_marker("[detector] first")
    main(["--reason", "the CLI is unreachable mid-rebase and the correction still owes logging"])
    set_marker("[detector] second")
    main(
        [
            "--reason",
            "open self-examination misread as closed admission; no error is named anywhere",
            "--misread-clauses",
            "I am not sure I am clean on it -- an unresolved question about register, not a retraction",
        ]
    )

    log_path = isolated_divineos_home / "cli_broken_escapes.jsonl"
    entries = [json.loads(line) for line in log_path.read_text().splitlines() if line]
    assert len(entries) == 2
    modes = [e.get("mode") for e in entries]
    assert modes == ["cli-broken", "false-positive"]
