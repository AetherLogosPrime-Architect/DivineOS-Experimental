"""The clerk says why a hand-made round cannot be matched to a head.

A round filed by hand has no `tree-hash:` line, so the clerk silently counts it as no
match and the fix shows as unconfirmed with no hint of the cause. It cost a night.
Matching is unchanged; only the explanation is added.
"""

from __future__ import annotations

import pytest

from divineos.core.landing_homework import her_confirm_filed_at, rounds_without_tree_line
from divineos.core.watchmen.store import list_rounds, submit_round

TREE = "39a1a9b5727b5e7c8ce767aae8d842be2dee330d"


def _says(pr: int) -> list[str]:
    return rounds_without_tree_line(pr, list_rounds(limit=500))


def test_a_round_naming_the_pr_without_the_line_is_explained() -> None:
    rid = submit_round("user", "PR 812 hand made round, branch x: Andrew confirms")
    assert _says(812) == [
        f"round {rid} has no tree-hash line: it cannot be matched to a head; "
        "file a new round with the designed first call"
    ]


def test_a_round_with_the_line_gets_no_explanation() -> None:
    submit_round("aletheia", "PR 813 clerk made", notes=f"tree-hash: {TREE}; patch-id: x")
    assert _says(813) == []


def test_a_pr_with_no_round_gets_no_false_explanation() -> None:
    submit_round("user", "PR 900 something else entirely")
    assert _says(814) == []


def test_a_longer_pr_number_is_not_this_pr() -> None:
    submit_round("user", "PR 8120 hand made")
    assert _says(812) == []


# --- the warning must agree with the matcher it speaks for (Aria's cold read, 2026-11-03) ---------------------
# "cannot be matched to a head" is a claim about her_confirm_filed_at, which reads the round's NOTES and the
# exact text "tree-hash: <tree>" (one space, lowercase tree). The warning may not be looser than that, or it
# stays silent about a round the clerk will still refuse.


class _Round:
    def __init__(self, focus: str, notes: str, round_id: str = "round-test") -> None:
        self.focus, self.notes, self.round_id = focus, notes, round_id


class _Finding:
    actor = "aletheia"
    tags = ["external-confirm"]
    created_at = 1_700_000_000.0


_FORMS = {
    "the clerk's own form, in the notes": ("PR 50 hand made", f"tree-hash: {TREE}", True),
    "no space after the colon": ("PR 50 hand made", f"tree-hash:{TREE}", False),
    "two spaces after the colon": ("PR 50 hand made", f"tree-hash:  {TREE}", False),
    "capital letters in the label": ("PR 50 hand made", f"Tree-Hash: {TREE}", False),
    "the line is only in the focus": (f"PR 50 tree-hash: {TREE}", "", False),
    "an eight-character abbreviation": ("PR 50 hand made", "tree-hash: 39a1a9b5", False),
    "no line at all": ("PR 50 hand made", "just notes", False),
}


class _Status:
    def __init__(self, label: str) -> None:
        self.label, self.detail, self.next_step = label, "detail", "next"


def _listing(monkeypatch, label: str, prs: list[dict], rounds_error: bool = False) -> str:
    """Run `divineos landing` through click with the outside world faked and the real warning wired in."""
    import click
    from click.testing import CliRunner

    from divineos.cli import landing_commands as lc

    monkeypatch.setattr(lc, "open_prs", lambda: prs)
    monkeypatch.setattr(lc, "_held_by_pr", lambda: {})
    monkeypatch.setattr(lc, "read_letters", lambda: [])
    monkeypatch.setattr(
        lc, "classify_pile", lambda p, letters, today, held: [(x, _Status(label)) for x in p]
    )
    if rounds_error:

        def _boom(limit: int = 500):
            raise OSError("store unreadable")

        monkeypatch.setattr(lc, "list_rounds", _boom)
    group = click.Group()
    lc.register(group)
    result = CliRunner().invoke(group, ["landing"])
    assert result.exit_code == 0, result.output
    return result.output


def test_the_listing_explains_a_round_missing_the_line_under_its_pr(monkeypatch) -> None:
    from divineos.core.landing_status import NEVER_TOLD

    rid = submit_round("user", "PR 61 hand made round")
    out = _listing(monkeypatch, NEVER_TOLD, [{"number": 61, "headRefName": "x"}])
    assert f"round {rid} has no tree-hash line" in out


def test_the_listing_is_quiet_about_a_pr_that_is_already_confirmed(monkeypatch) -> None:
    from divineos.core.landing_status import CONFIRMED

    submit_round("user", "PR 62 hand made round")
    out = _listing(monkeypatch, CONFIRMED, [{"number": 62, "headRefName": "x"}])
    assert "has no tree-hash line" not in out


def test_the_listing_says_so_when_the_rounds_cannot_be_read(monkeypatch) -> None:
    from divineos.core.landing_status import NEVER_TOLD

    out = _listing(monkeypatch, NEVER_TOLD, [{"number": 63, "headRefName": "x"}], rounds_error=True)
    assert "Could not read the audit rounds" in out and "not a clean bill" in out


@pytest.mark.parametrize("name", list(_FORMS))
def test_the_warning_and_the_matcher_agree_on_every_form(name: str) -> None:
    focus, notes, matcher_can_use_it = _FORMS[name]
    matcher_says = her_confirm_filed_at(notes, [_Finding()], TREE) is not None
    assert matcher_says is matcher_can_use_it, "the table itself is wrong about the matcher"
    warned = bool(rounds_without_tree_line(50, [_Round(focus, notes)]))
    assert warned is (not matcher_can_use_it), f"warning and matcher disagree on: {name}"
