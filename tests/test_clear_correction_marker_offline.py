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

    rc = main(["--cli-broken", "--reason", "too short"])

    assert rc == 2
    err = capsys.readouterr().err
    assert "REFUSED" in err
    assert "30 characters" in err


def test_noop_when_marker_absent(isolated_divineos_home, capsys):
    from scripts.clear_correction_marker import main

    long_reason = "x" * 35
    rc = main(["--cli-broken", "--reason", long_reason])

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

    rc = main(["--cli-broken", "--reason", long_reason])

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
    main(["--cli-broken", "--reason", long_reason_a])
    set_marker("trigger B")
    main(["--cli-broken", "--reason", long_reason_b])

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


# ─── The mode must be declared, never inferred from an omission ───────


class TestModeIsDeclaredNotGuessed:
    """A default is a guess, and this one guessed wrong 45 times out of 45.

    The mode used to be inferred: ``"false-positive" if misread_clauses else
    "cli-broken"``. Forgetting one flag therefore MEANT "the CLI is broken" --
    a factual assertion about the machine, filed silently, carrying a
    remediation debt and a bypass-telemetry row that feeds the
    gates-are-being-routed-around verdict.

    Measured 2026-08-22 across all 45 rows of cli_broken_escapes.jsonl: NOT ONE
    is a CLI-broken escape. About 35 are false-positive attributions; about 10
    are defect-escapes where gates blocked each other. A file named for a
    category that has never once occurred.

    It stayed wrong for months because it was wrong SILENTLY. Nothing ever
    contradicted the guess, so nothing ever surfaced it.
    """

    def test_omitting_both_flags_is_refused(self, isolated_divineos_home, capsys):
        from scripts.clear_correction_marker import main

        rc = main(["--reason", "a reason well past the thirty character floor for this gate"])

        assert rc == 2
        assert "name the mode" in capsys.readouterr().err

    def test_the_refusal_names_both_paths(self, isolated_divineos_home, capsys):
        from scripts.clear_correction_marker import main

        """A refusal that does not say what WOULD work is the painted door."""
        main(["--reason", "a reason well past the thirty character floor for this gate"])

        err = capsys.readouterr().err
        assert "--misread-clauses" in err
        assert "--cli-broken" in err

    def test_both_flags_together_are_refused_as_contradictory(self, isolated_divineos_home, capsys):
        from scripts.clear_correction_marker import main

        rc = main(
            [
                "--cli-broken",
                "--misread-clauses",
                "quoted reply text long enough to clear the forty character minimum",
                "--reason",
                "a reason well past the thirty character floor for this gate",
            ]
        )

        assert rc == 2
        assert "cannot both be true" in capsys.readouterr().err

    def test_a_declared_false_positive_still_works(self, isolated_divineos_home):
        from scripts.clear_correction_marker import main

        """The guard must not break the path it exists to protect."""
        rc = main(
            [
                "--misread-clauses",
                "quoted reply text long enough to clear the forty character minimum",
                "--reason",
                "a reason well past the thirty character floor for this gate",
            ]
        )

        assert rc == 0

    def test_a_declared_cli_broken_still_works(self, isolated_divineos_home):
        from scripts.clear_correction_marker import main

        rc = main(["--cli-broken", "--reason", "the CLI is genuinely unreachable right now"])

        assert rc == 0
