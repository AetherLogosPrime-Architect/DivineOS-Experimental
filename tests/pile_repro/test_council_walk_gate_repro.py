"""Council-walk-gate theme: read-only commands owe no walk (pile round three).

Born as reproductions of problems, each marked ``xfail(strict=True)``. Sixteen of
the nineteen parameter cases have since been repaired on main (the classifier now
lets read-only look-ups and ``--help`` through), so their marks have been removed
and they stand as ordinary regression tests: if the repair is ever undone they go
red. Three cases are still real problems and keep their marks, each with a reason
that names the defect: ``compass-ops spectrums``, ``journal search``, and the
fingerprint of one file in two working copies. The day one of those is repaired its
mark turns into a failure and has to come off.

The tests that are NOT marked xfail include controls. A probe that cannot tell a
broken probe from an absent problem proves nothing, so each control shows the same
code path answering a case it should answer today.

Source: docs/pile_sorting/output/council_walk_gate.md (rows listed per test).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from divineos.core.council_required import gate as gate_mod
from divineos.core.council_required.types import GateOutcome, fingerprint_for
from divineos.core.gravity_classifier import score_substrate_modification

REPO = Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def scratch_ledger(tmp_path, monkeypatch):
    """Route the ledger to a scratch path so no test touches the real one."""
    db_path = tmp_path / "ledger.sqlite"
    from divineos.core import _ledger_base
    from divineos.core import ledger as ledger_mod

    monkeypatch.setattr(_ledger_base, "_get_db_path", lambda: db_path)
    monkeypatch.setattr(ledger_mod, "_get_db_path", lambda: db_path)
    ledger_mod.init_db()
    return db_path


def _no_keywords():
    return {}


_STILL_OWES_A_WALK = pytest.mark.xfail(
    raises=AssertionError,
    strict=True,
    reason="reproduces: a read-only look-up still owes a council walk",
)


@pytest.mark.parametrize(
    "command",
    [
        pytest.param("divineos audit list", id="audit-list"),
        pytest.param("divineos audit show finding-1", id="audit-show"),
        pytest.param("divineos audit summary", id="audit-summary"),
        pytest.param("divineos prereg list", id="prereg-list"),
        pytest.param("divineos prereg show prereg-1", id="prereg-show"),
        pytest.param("divineos prereg overdue", id="prereg-overdue"),
        pytest.param("divineos prereg summary", id="prereg-summary"),
        pytest.param("divineos compass-ops history", id="compass-history"),
        pytest.param("divineos compass-ops summary", id="compass-summary"),
        pytest.param(
            "divineos compass-ops spectrums",
            id="compass-spectrums",
            marks=_STILL_OWES_A_WALK,
        ),
        pytest.param("divineos journal list", id="journal-list"),
        pytest.param(
            "divineos journal search topic",
            id="journal-search",
            marks=_STILL_OWES_A_WALK,
        ),
    ],
)
def test_a_read_only_look_up_owes_no_council_walk(command):
    """A list, show, summary, history, overdue or search command writes nothing,
    so the classifier must not say it needs a council walk.

    Rows: psf-7ce1ee55, psf-c717c6e4, psf-d36076f1, psf-4e4e3ad2
    Note (psf-7ce1ee55): "read-only subcommands (`audit list|show|summary`, `prereg list|show|overdue|summary`, `compass-ops history|summary|spectrums`, `journal list|search`) and `--help` should not owe the council gate a wal"

    Calls the real ``score_substrate_modification`` that the council gate uses.

    What would make this test wrong: it checks the classifier's verdict, so a
    repair made one layer up (an allowlist inside ``gate.decide`` rather than in
    the classifier) would leave the still-marked cases failing even though the
    problem is repaired; read it together with the gate-level test below. The
    commands use made-up identifiers (``finding-1``, ``prereg-1``), which the
    classifier does not look up, so a repair that starts validating identifiers
    could fail these for a reason other than the problem.
    """
    result = score_substrate_modification("Bash", (), command)
    assert result.is_council_required is False, (
        f"{command!r} reads without writing but still owes a council walk "
        f"(fired: {getattr(result, 'fired_features', None)})"
    )


@pytest.mark.parametrize(
    "command",
    [
        pytest.param("divineos prereg --help", id="prereg-help"),
        pytest.param("divineos audit --help", id="audit-help"),
        pytest.param("divineos audit submit-round --help", id="write-verb-help"),
    ],
)
def test_asking_for_help_owes_no_council_walk(command):
    """Opening a command with --help writes nothing, so it owes no walk.

    Rows: psf-d5aa48d4, psf-d36076f1, psf-7ce1ee55
    Note (psf-d5aa48d4): "exempt `--help` and `--version` calls from the substrate-write classifier, which is already entry 9 on the gameplan."

    Calls the real ``score_substrate_modification``. ``divineos --version`` is
    free too (see the control below).

    What would make this test wrong: ``divineos audit submit-round --help``
    names a write verb; if the exemption is ever narrowed to read-only nouns,
    that one parameter would fail while the others stay green, which is a
    reasonable narrowing and not a failure of the others.
    """
    result = score_substrate_modification("Bash", (), command)
    assert result.is_council_required is False, f"{command!r} only prints help"


@pytest.mark.parametrize(
    "command",
    [
        pytest.param("divineos audit list", id="audit-list"),
        pytest.param("divineos audit show finding-1", id="audit-show"),
        pytest.param("divineos prereg show prereg-1", id="prereg-show"),
    ],
)
def test_the_gate_lets_a_read_only_look_up_through_with_no_walk_on_record(scratch_ledger, command):
    """With an empty ledger, the real gate lets a command that only reads through.

    Rows: psf-a8cea834, psf-021be55d, psf-4bb053f7
    Note (psf-a8cea834): "let reading-only commands like "show" through the council gate, so it stops blocking the remedy another gate asks for."

    Calls the real ``gate.decide`` with the real classifier, against a scratch
    ledger holding no walks. The note is that another gate's remedy (a command
    that only shows a record) must not sit behind this gate.

    What would make this test wrong: the ledger is isolated by a fixture, so if
    that isolation broke and a real walk existed the gate could ALLOW for a
    reason unrelated to the problem; the control below proves the same setup
    blocks a write. The keyword loader is a stub, which is safe because it is
    only read when a walk record exists.
    """
    decision = gate_mod.decide(
        tool_name="Bash",
        file_paths=(),
        bash_command=command,
        gravity_fn=score_substrate_modification,
        keywords_loader=_no_keywords,
    )
    assert decision.outcome == GateOutcome.ALLOW, f"{command!r} only reads"


@pytest.mark.xfail(
    raises=AssertionError,
    strict=True,
    reason="reproduces: a walk filed against a file path in one working copy does not match the same file in another copy",
)
def test_the_same_file_in_another_working_copy_gets_the_same_fingerprint(tmp_path, monkeypatch):
    """The fingerprint keeps an absolute path when the file sits in a working
    copy other than the one this code was loaded from, so a walk filed for the
    file in one copy does not count in another.

    Rows: psf-349ffceb, psf-acc25677
    Note (psf-349ffceb): "key the fingerprint on the file's place in the repository and not its absolute path, so a walk filed for a file counts in any working copy of it. That's new, and it cost me twelve walks."

    Calls the real ``fingerprint_for``. A real git repository is created in a
    temporary folder to stand for "another working copy", and the same file is
    named by absolute path and by repository-relative path.

    What would make this test wrong: today the code strips only the root it
    finds by walking up from its own module file (or from
    ``DIVINEOS_REPO_ROOT``), so this test clears that variable. A repair that
    finds the root differently (for example by asking git for the file's
    top-level folder) would pass, which is intended; a repair that merely
    treated every absolute path as relative would also pass and would be wrong,
    so a reviewer should check the repair against the control below, which must
    keep holding.
    """
    monkeypatch.delenv("DIVINEOS_REPO_ROOT", raising=False)
    other = tmp_path / "other_copy"
    (other / "src").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(other)], check=True)
    target = other / "src" / "example.py"
    target.write_text("x = 1\n", encoding="utf-8")
    by_absolute_path = fingerprint_for("Edit", (str(target),), "")
    by_relative_path = fingerprint_for("Edit", ("src/example.py",), "")
    assert by_absolute_path == by_relative_path


def test_control_a_write_still_owes_a_walk():
    """Control: commands that write are still classified as needing a walk, so
    the classifier is alive and the read-only tests above are not passing or
    failing because it returns a constant.

    Rows: psf-7ce1ee55
    Note (psf-7ce1ee55): "read-only subcommands (`audit list|show|summary`, `prereg list|show|overdue|summary`, `compass-ops history|summary|spectrums`, `journal list|search`) and `--help` should not owe the council gate a wal"

    What would make this test wrong: a repair that exempts too much would turn
    this red, which is the point; a repair that renames these commands would
    also turn it red for a reason unrelated to the problem.
    """
    for command in ("divineos prereg file x --claim y", "divineos audit submit-round x"):
        result = score_substrate_modification("Bash", (), command)
        assert result.is_council_required is True, command


def test_control_the_gate_blocks_a_write_with_no_walk_on_record(scratch_ledger):
    """Control: the same gate and the same empty scratch ledger do BLOCK a write,
    so the gate-level test is not allowing for an unrelated reason.

    Rows: psf-a8cea834
    Note (psf-a8cea834): "let reading-only commands like "show" through the council gate, so it stops blocking the remedy another gate asks for."

    What would make this test wrong: it stays green if the gate blocks writes
    and reads alike, so on its own it says nothing about reads; it only proves
    the probe is alive.
    """
    decision = gate_mod.decide(
        tool_name="Bash",
        file_paths=(),
        bash_command="divineos prereg file x --claim y",
        gravity_fn=score_substrate_modification,
        keywords_loader=_no_keywords,
    )
    assert decision.outcome == GateOutcome.BLOCK


def test_control_version_and_council_show_are_already_free():
    """Control: the exemption the note asks for exists for some commands, which
    shows the classifier can say "no walk needed".

    Rows: psf-d5aa48d4, psf-a8cea834
    Note (psf-d5aa48d4): "exempt `--help` and `--version` calls from the substrate-write classifier, which is already entry 9 on the gameplan."

    What would make this test wrong: if those two commands were ever counted as
    writes this would fail for a reason that has nothing to do with the problem.
    """
    for command in ("divineos --version", "divineos council show abc", "ls tests"):
        result = score_substrate_modification("Bash", (), command)
        assert result.is_council_required is False, command


def test_control_a_path_inside_this_checkout_is_already_relative():
    """Control: for a file inside the working copy this code was loaded from,
    the fingerprint is already repository-relative, so the other-copy test above
    targets the gap and not a missing feature.

    Rows: psf-349ffceb
    Note (psf-349ffceb): "key the fingerprint on the file's place in the repository and not its absolute path, so a walk filed for a file counts in any working copy of it. That's new, and it cost me twelve walks."

    What would make this test wrong: it relies on the root being found from this
    module's own location, so it would fail if tests ran against an installed
    copy outside the checkout.
    """
    absolute = fingerprint_for("Edit", (str(REPO / "src" / "divineos" / "__init__.py"),), "")
    relative = fingerprint_for("Edit", ("src/divineos/__init__.py",), "")
    assert absolute == relative
