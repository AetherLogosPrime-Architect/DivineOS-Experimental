"""The ancestry rung: what it lets through, and the four ways it must not.

Aletheia amended the anchor rule on 2026-09-03 after her first version broke
within twelve hours -- broken by the act of USING it, because catching a
branch up to main rewrites a generated file, and a tree hash moves when any
byte under it moves. Her replacement puts ancestry under the tree: if the
commit she read is still in this history, her reading was built upon rather
than superseded.

These assert the discrimination in BOTH directions, because a rung that only
ever says yes is not a rung. The refusals are the load-bearing half: a round
that never claimed an ancestry gets no rung at all, an orphaned tip is refused
with no exception available, and a lookup that could not be performed must
never render as a pass.

``_is_ancestor`` runs against real git in a real repository. ``list_findings``
is substituted -- it is the collaborator supplying input, not the thing under
test. Companion to ``test_stamp_ready_tree_binding.py``, which covers the
strict tree rung above this one.
"""

from __future__ import annotations

import subprocess
from types import SimpleNamespace

import pytest

from divineos.cli import stamp_ready_command as src


def _git(*args: str, cwd) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    ).stdout.strip()


@pytest.fixture()
def repo(tmp_path, monkeypatch):
    """A repository with a main line and one commit that is NOT on it.

    Yields ``(first, head, orphan)`` where ``first`` is an ancestor of ``head``
    and ``orphan`` is a real commit on a side branch that is not.
    """
    root = tmp_path / "repo"
    root.mkdir()
    _git("init", "-q", "-b", "main", cwd=root)
    _git("config", "user.email", "t@example.com", cwd=root)
    _git("config", "user.name", "t", cwd=root)

    (root / "a.txt").write_text("one\n", encoding="utf-8")
    _git("add", "a.txt", cwd=root)
    _git("commit", "-q", "-m", "one", cwd=root)
    first = _git("rev-parse", "HEAD", cwd=root)

    _git("checkout", "-q", "-b", "side", cwd=root)
    (root / "b.txt").write_text("side\n", encoding="utf-8")
    _git("add", "b.txt", cwd=root)
    _git("commit", "-q", "-m", "side", cwd=root)
    orphan = _git("rev-parse", "HEAD", cwd=root)

    _git("checkout", "-q", "main", cwd=root)
    (root / "a.txt").write_text("one\ntwo\n", encoding="utf-8")
    _git("commit", "-q", "-am", "two", cwd=root)
    head = _git("rev-parse", "HEAD", cwd=root)

    monkeypatch.chdir(root)
    return first, head, orphan


def _findings(monkeypatch, *texts: str) -> None:
    rows = [SimpleNamespace(title="", description=t) for t in texts]
    monkeypatch.setattr("divineos.core.watchmen.store.list_findings", lambda **kw: rows)


def _titled(monkeypatch, *pairs: tuple[str, str]) -> None:
    rows = [SimpleNamespace(title=t, description=d) for t, d in pairs]
    monkeypatch.setattr("divineos.core.watchmen.store.list_findings", lambda **kw: rows)


# ------------------------------------------------- a refusal is not a signature
#
# Aletheia offered this on 2026-09-03, after a reporting script of mine read her
# sentence "I am not confirming the thirteen in bucket one as READ" and printed
# her name against thirteen branches she had refused:
#
#   "Negation-as-affirmation has now happened once; a test is how it stops
#    being a thing either of us has to stay alert to."
#
# She was writing about my script. The same substring filter selects findings in
# the gate itself, so the fault was in shipped code too and neither of us had
# looked there. These pin both directions, because a filter that removes real
# confirms is a worse failure than the one it repairs: an emptied confirms set
# makes the gate stop refusing and start merely warning.


def test_a_withheld_clearance_never_supplies_a_tree(repo, monkeypatch):
    _first, _head, _orphan = repo
    _titled(
        monkeypatch,
        (
            "SHAPE-CLEARED (not read) PR #461 -- aletheia, relayed",
            "I am not confirming these as READ. Cleared on shape only, at tree "
            "b231ff548261, and the shape verdict is not an audit.",
        ),
    )
    assert src._confirmed_trees("round-x") == set(), (
        "a finding whose title says it is not a signature supplied a tree as though it were one"
    )


def test_a_withheld_clearance_never_opens_the_ancestry_rung(repo, monkeypatch):
    """The sharper case: declining to read is when the ancestry gets EXPLAINED."""
    first, head, _orphan = repo
    _titled(
        monkeypatch,
        (
            "NOT CONFIRMING PR #465 -- aletheia",
            f"CONFIRMS nothing here. The tip {first[:12]} is an ancestor of the "
            "current head, but I have not read what sits on top of it.",
        ),
    )
    holds, _why = src._ancestry_rung("round-x", head)
    assert holds is False


def test_a_real_confirm_is_not_swept_up_by_the_withheld_filter(repo, monkeypatch):
    """The direction that matters more, and the reason this is a NEGATIVE filter.

    Selecting only titles that BEGIN with CONFIRMS would read stricter and be
    looser: rounds predating that convention lose their confirms, an emptied
    confirms set stops the gate refusing, and the tree binding degrades to a
    warning. So an ordinary confirm with an unremarkable title must survive.
    """
    _first, _head, _orphan = repo
    _titled(
        monkeypatch,
        ("Round 9 review notes, aletheia", "CONFIRMS at tree b231ff548261."),
    )
    assert "b231ff548261" in src._confirmed_trees("round-x")


# --------------------------------------------------------------- _is_ancestor


def test_is_ancestor_separates_yes_no_and_could_not_tell(repo):
    first, head, orphan = repo
    assert src._is_ancestor(first, head) is True
    assert src._is_ancestor(orphan, head) is False
    # A sha this repository has never held. The answer is NOT "no" -- an
    # unfetched commit and an orphaned one are different facts, and collapsing
    # them is how a branch nobody fetched gets reported as rebuilt.
    assert src._is_ancestor("0" * 40, head) is None


# -------------------------------------------------------------------- the rung


def test_rung_holds_when_a_confirms_finding_claims_a_real_ancestry(repo, monkeypatch):
    first, head, _orphan = repo
    _findings(monkeypatch, f"CONFIRMS this PR. Signed tip {first[:12]} is an ancestor of head.")
    holds, why = src._ancestry_rung("round-x", head)
    assert holds is True
    assert first[:12] in why


def test_rung_refuses_when_the_record_names_a_tip_but_claims_no_ancestry(repo, monkeypatch):
    """The git fact is TRUE here and the rung must still refuse.

    This is the entire reason the written claim is required. Ancestry alone is
    not sufficient: a branch piling real new commits on top of the reviewed one
    passes an ancestor test exactly as cleanly as one that only caught up. What
    separates them is whether the differences are artifact-only, and that
    reading is a judgement Aletheia refused to let this repository keep in a
    list -- so it has to be written down by someone willing to sign it.
    """
    first, head, _orphan = repo
    _findings(monkeypatch, f"CONFIRMS this PR at tip {first[:12]}.")
    holds, why = src._ancestry_rung("round-x", head)
    assert holds is False
    assert "claims" in why


def test_rung_refuses_an_orphaned_tip_and_says_so_in_those_words(repo, monkeypatch):
    _first, head, orphan = repo
    _findings(monkeypatch, f"CONFIRMS. tip {orphan[:12]} is an ancestor of the current head.")
    holds, why = src._ancestry_rung("round-x", head)
    assert holds is False
    assert "orphaned" in why


def test_rung_does_not_read_a_failed_lookup_as_a_pass(repo, monkeypatch):
    _first, head, _orphan = repo
    _findings(monkeypatch, f"CONFIRMS. tip {'0' * 12} is an ancestor of head.")
    holds, why = src._ancestry_rung("round-x", head)
    assert holds is False
    # And it must not be called orphaned either -- that would assert a fact
    # from a measurement that never happened.
    assert "orphaned" not in why
    assert "resolved" in why


def test_rung_refuses_when_the_head_itself_could_not_be_read(repo, monkeypatch):
    first, _head, _orphan = repo
    _findings(monkeypatch, f"CONFIRMS. tip {first[:12]} is an ancestor of head.")
    holds, why = src._ancestry_rung("round-x", "")
    assert holds is False
    assert "could not be resolved" in why


def test_rung_ignores_findings_that_are_not_confirms(repo, monkeypatch):
    """A finding merely discussing an ancestry is not a signature."""
    first, head, _orphan = repo
    _findings(monkeypatch, f"Note for later: tip {first[:12]} is an ancestor of head.")
    holds, _why = src._ancestry_rung("round-x", head)
    assert holds is False
