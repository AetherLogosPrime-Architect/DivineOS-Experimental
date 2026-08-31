"""Tests for the painted-door scanner.

The load-bearing case is the real one. `_HISTORICAL` is the comment that
actually misled me twice on 2026-08-27 -- it sat two lines above a raw
substring test and claimed an exclusion the code had never performed. A
detector for this class that cannot find the instance that motivated it is
decoration, so that fixture is the first test in the file.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_comment_claims.py"
_spec = importlib.util.spec_from_file_location("check_comment_claims", _SCRIPT)
assert _spec and _spec.loader
cc = importlib.util.module_from_spec(_spec)
# Register before exec: dataclasses resolve annotations via
# sys.modules[cls.__module__], and a module loaded by path alone is not
# there yet, so @dataclass raises on a None lookup.
sys.modules[_spec.name] = cc
_spec.loader.exec_module(cc)


_HISTORICAL = """
def find_stages(cmd):
    # A real pipeline, not a logical-or and not a pipe inside quotes-only.
    # Strip || first so `a || b` never counts as a pipeline.
    stripped = cmd.replace("||", "")
    if "|" not in stripped:
        return []
    return stripped.split("|")
"""


def _scan(tmp_path: Path, source: str, corpus: str = "") -> list[cc.Claim]:
    path = tmp_path / "sample.py"
    path.write_text(source, encoding="utf-8")
    monkey = cc.REPO_ROOT
    cc.REPO_ROOT = tmp_path
    try:
        return cc.scan_file(path, corpus, cc.Tally())
    finally:
        cc.REPO_ROOT = monkey


def test_the_comment_that_actually_misled_me_is_found(tmp_path: Path) -> None:
    """The instance the whole file exists for."""
    claims = _scan(tmp_path, _HISTORICAL)
    assert claims, "the detector cannot find the case that motivated it"
    assert any("not a logical-or" in c.text for c in claims)
    assert claims[0].symbol == "find_stages"


def test_explanatory_prose_far_from_a_branch_is_not_a_claim(tmp_path: Path) -> None:
    """The noise the first two versions of this drowned in.

    An earlier cut matched any present-tense capability verb and returned
    1,353 findings; narrowing to exclusions still returned 1,219, because
    "not a" is how people write ordinary explanation. Position is what
    separates a claim about a branch from a sentence about a design.
    """
    source = """
# This module names a design class, not a corrective evaluation, and it
# never tries to decide whether the data is good -- it only surfaces where
# a reader should look next.

def unrelated():
    return 1
"""
    assert _scan(tmp_path, source) == []


def test_a_claim_whose_symbol_is_tested_is_marked_covered(tmp_path: Path) -> None:
    claims = _scan(tmp_path, _HISTORICAL, corpus="def test_find_stages(): find_stages('a')")
    assert claims and claims[0].covered is True


def test_an_untested_symbol_is_marked_uncovered(tmp_path: Path) -> None:
    claims = _scan(tmp_path, _HISTORICAL, corpus="def test_something_else(): pass")
    assert claims and claims[0].covered is False


def test_an_unresolvable_symbol_reports_uncovered_rather_than_passing(tmp_path: Path) -> None:
    """Unknown is its own answer.

    A claim with no enclosing symbol cannot be checked against the tests at
    all. Dropping it would let the hardest cases read as clean -- the exact
    failure direction every instrument in this house has been repaired for.
    """
    source = """
# Only reaches here when the input is not a directory.
if True:
    pass
"""
    claims = _scan(tmp_path, source)
    assert claims
    assert claims[0].symbol == "<module-level>"
    assert claims[0].covered is False


def test_history_and_intent_are_not_capability_claims(tmp_path: Path) -> None:
    """A note about why something WAS done claims nothing about what it does."""
    source = """
def guarded():
    # This used to skip empty input because 2026-08-01 showed it never mattered.
    if not guarded:
        return None
    return 1
"""
    assert _scan(tmp_path, source) == []


def test_a_scan_that_opened_nothing_says_so_and_fails(capsys: pytest.CaptureFixture[str]) -> None:
    """Subject-report, not self-report.

    Zero findings from a scanner that opened no files must not read the same
    as zero findings from a clean repository.
    """
    code = cc.main(["--roots", "no/such/directory"])
    out = capsys.readouterr().out
    assert "NOTHING OPENED" in out
    assert code == 1


def test_printable_survives_a_console_that_cannot_encode_the_repo() -> None:
    """The crash that looked like completion, caught twice in one day."""
    assert cc._printable("plain") == "plain"
    assert cc._printable("arrow → here")
