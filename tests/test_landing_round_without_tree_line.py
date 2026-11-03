"""The clerk says why a hand-made round cannot be matched to a head.

A round filed by hand has no `tree-hash:` line, so the clerk silently counts it as no
match and the fix shows as unconfirmed with no hint of the cause. It cost a night.
Matching is unchanged; only the explanation is added.
"""

from __future__ import annotations

from divineos.core.landing_homework import rounds_without_tree_line
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
