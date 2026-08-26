"""The growth warning must anchor to the right branch and never fake a pass.

Two failures are pinned here and both actually happened while this was written.

FIRST, the anchor. Rounds cover several PRs in one block of prose. The initial
implementation took every ``tip <sha>`` from any round mentioning the branch,
and on its first real run against PR #437 it anchored to PR #432's tip and
printed a confident commit count against it. A true number about the wrong
subject -- the exact class the checker exists to surface, reproduced inside the
checker. ``test_the_nearest_tip_after_the_branch_name_wins`` is that bug.

SECOND, could-not-look. Every path that fails to measure must say so in words
that cannot be read as a clean bill. A branch with no confirm is the LEAST
reviewed case there is, so reporting silence there would invert the truth
exactly. That is the fourth consolidation invariant (Aria and Aether,
2026-08-24): a check that cannot run must never be able to report success.

Everything here drives the real functions. The git layer is the only thing
stubbed, because the subject is which anchor gets chosen and what gets said --
not whether git works.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_branch_growth.py"

# The AFFIRMATIVE clean-bill, not the bare phrase. The could-not-look messages
# deliberately CONTAIN the words "within limits" inside the sentence denying
# them -- "This is 'could not look', NOT 'within limits'" -- so a plain
# substring check fails on the honest output and passes on a silent one. Caught
# by these tests on their first run, which is the correct direction for a test
# about not mistaking a denial for a claim to trip.
AFFIRMATIVE_PASS = "— within limits."


def _load():
    """Import the script by path — scripts/ is not a package."""
    sys.path.insert(0, str(_SCRIPT.parent))
    try:
        spec = importlib.util.spec_from_file_location("check_branch_growth", _SCRIPT)
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        sys.path.pop(0)


@pytest.fixture
def growth():
    return _load()


def _round(round_id: str, focus: str, notes: str = ""):
    return SimpleNamespace(round_id=round_id, focus=focus, notes=notes)


class TestAnchorSelection:
    def test_the_nearest_tip_after_the_branch_name_wins(self, growth, monkeypatch):
        """The real defect: one round, four branches, five shas.

        Shaped after round-ec31cf1d9d5b, where taking the first tip in the round
        anchored #437 to #432's commit. Branch B's tip sits AFTER branch A's, so
        a first-match implementation returns A's for both.
        """
        text = (
            "PR #432 branch-alpha tip aaaaaaaaaaaaaaaa tree-hash: 1111111111111111 | "
            "PR #437 branch-beta CONFIRMED AT tip bbbbbbbbbbbbbbbb"
        )
        monkeypatch.setattr(growth, "list_rounds_or_empty", None, raising=False)
        monkeypatch.setattr(growth, "_git", lambda *a: "origin")
        monkeypatch.setitem(
            sys.modules,
            "divineos.core.watchmen.store",
            SimpleNamespace(list_rounds=lambda limit=60: [_round("round-x", text)]),
        )
        assert growth.anchors_for_branch("branch-beta") == [("round-x", "bbbbbbbbbbbbbbbb")]
        assert growth.anchors_for_branch("branch-alpha") == [("round-x", "aaaaaaaaaaaaaaaa")]

    def test_a_branch_with_no_tip_after_it_borrows_nothing(self, growth, monkeypatch):
        """Better to have no anchor than someone else's."""
        text = "PR #432 branch-alpha tip aaaaaaaaaaaaaaaa | PR #99 branch-omega (no tip given)"
        monkeypatch.setattr(growth, "_git", lambda *a: "origin")
        monkeypatch.setitem(
            sys.modules,
            "divineos.core.watchmen.store",
            SimpleNamespace(list_rounds=lambda limit=60: [_round("round-x", text)]),
        )
        assert growth.anchors_for_branch("branch-omega") == []

    def test_a_tree_hash_is_not_mistaken_for_a_tip(self, growth, monkeypatch):
        """Rounds carry tree-hashes and patch-ids beside tips; only tips are commits."""
        text = "branch-beta tree-hash: cccccccccccccccc patch-id dddddddddddddddd"
        monkeypatch.setattr(growth, "_git", lambda *a: "origin")
        monkeypatch.setitem(
            sys.modules,
            "divineos.core.watchmen.store",
            SimpleNamespace(list_rounds=lambda limit=60: [_round("round-x", text)]),
        )
        assert growth.anchors_for_branch("branch-beta") == []


class TestRemoteStripping:
    def test_a_remote_tracking_ref_matches_the_name_an_auditor_wrote(self, growth, monkeypatch):
        """The miss on the first live run: rounds say `fix/x`, callers pass `origin/fix/x`."""
        monkeypatch.setattr(growth, "_git", lambda *a: "origin")
        assert growth.strip_remote("origin/fix/x") == "fix/x"

    def test_a_local_branch_resembling_a_remote_keeps_its_name(self, growth, monkeypatch):
        """Only a CONFIGURED remote is stripped, so `upstream/x` survives when
        no such remote exists — shortening it would name a different branch."""
        monkeypatch.setattr(growth, "_git", lambda *a: "origin")
        assert growth.strip_remote("upstream/fix/x") == "upstream/fix/x"


class TestCouldNotLookIsNeverAPass:
    def _run(self, growth, monkeypatch, capsys, anchors, growth_result):
        monkeypatch.setattr(growth, "anchors_for_branch", lambda b, limit=60: anchors)
        monkeypatch.setattr(growth, "growth_since", lambda a, b: growth_result)
        code = growth.main(["--branch", "some-branch"])
        return code, capsys.readouterr().out

    def test_no_anchor_says_could_not_look(self, growth, monkeypatch, capsys):
        code, out = self._run(growth, monkeypatch, capsys, [], None)
        assert code == 0
        assert "no CONFIRMED anchor" in out
        assert "could not look" in out.lower()
        assert AFFIRMATIVE_PASS not in out

    def test_an_unresolvable_anchor_says_could_not_look(self, growth, monkeypatch, capsys):
        code, out = self._run(growth, monkeypatch, capsys, [("round-x", "deadbeef")], None)
        assert code == 0
        assert "could not look" in out.lower()
        assert AFFIRMATIVE_PASS not in out

    def test_within_limits_is_only_said_when_actually_measured(self, growth, monkeypatch, capsys):
        code, out = self._run(growth, monkeypatch, capsys, [("round-x", "deadbeef")], (3, 4))
        assert code == 0
        assert AFFIRMATIVE_PASS in out


class TestTheWarning:
    def _run(self, growth, monkeypatch, capsys, counts):
        monkeypatch.setattr(growth, "anchors_for_branch", lambda b, limit=60: [("r", "deadbeef")])
        monkeypatch.setattr(growth, "growth_since", lambda a, b: counts)
        code = growth.main(["--branch", "some-branch"])
        return code, capsys.readouterr().out

    def test_commits_over_the_limit_warn(self, growth, monkeypatch, capsys):
        code, out = self._run(growth, monkeypatch, capsys, (31, 1))
        assert "WARNING" in out and "31 commit" in out
        assert code == 0, "helper, not a gate — the push continues"

    def test_files_over_the_limit_warn_on_their_own(self, growth, monkeypatch, capsys):
        """Either dimension is enough: a two-commit branch touching 400 files is
        just as unreadable as a 200-commit one."""
        code, out = self._run(growth, monkeypatch, capsys, (2, 61))
        assert "WARNING" in out and "61 file" in out
        assert code == 0

    def test_exactly_at_the_limit_does_not_warn(self, growth, monkeypatch, capsys):
        _, out = self._run(growth, monkeypatch, capsys, (30, 60))
        assert "WARNING" not in out
        assert AFFIRMATIVE_PASS in out
