"""The readiness board must see every open request, or say it could not.

2026-11-27: 71 requests were open and ``divineos build-flow status`` listed 50,
because ``_open_prs`` asked GitHub for ``--limit 50``. The 21 oldest were simply
absent, and ``divineos landing`` then marked each of them "held by board" --
could not look -- so three requests Aletheia had already confirmed could never
show READY. A silent cap is the same absence-becomes-value collapse the file
already guards for per-request file lists (``_GH_PR_FILES_CAP``): a result of
exactly the cap cannot be told from a truncated one.

The fake ``gh`` below honours ``--limit`` the way the real one does, so these
tests fail on the old code for the reason the real board failed.
"""

from __future__ import annotations

import json

import pytest

from divineos.cli import build_flow_commands as bfc


def _fake_gh_with(total: int):
    """A gh that holds ``total`` open requests and truncates at ``--limit``."""
    seen: dict[str, int] = {}

    def fake(args: list[str]) -> str | None:
        limit = int(args[args.index("--limit") + 1])
        seen["limit"] = limit
        rows = [
            {"number": 1000 - i, "headRefName": f"b{i}", "isDraft": True, "body": ""}
            for i in range(total)
        ]
        return json.dumps(rows[:limit])

    return fake, seen


def test_the_board_sees_seventy_one_when_seventy_one_are_open(monkeypatch) -> None:
    fake, _seen = _fake_gh_with(71)
    monkeypatch.setattr(bfc, "_gh", fake)

    prs = bfc._open_prs()

    assert prs is not None
    assert len(prs) == 71


def test_a_list_that_fills_the_cap_is_could_not_say_not_a_short_list(monkeypatch) -> None:
    """If GitHub ever holds more than we asked for, the answer is unknown, never 'these are all of them'."""
    fake, seen = _fake_gh_with(100000)
    monkeypatch.setattr(bfc, "_gh", fake)

    assert bfc._open_prs() is None
    assert seen["limit"] == bfc._GH_OPEN_PRS_CAP


def test_a_list_just_under_the_cap_is_returned_whole(monkeypatch) -> None:
    fake, _seen = _fake_gh_with(bfc._GH_OPEN_PRS_CAP - 1)
    monkeypatch.setattr(bfc, "_gh", fake)

    prs = bfc._open_prs()

    assert prs is not None
    assert len(prs) == bfc._GH_OPEN_PRS_CAP - 1


@pytest.mark.parametrize("raw", ["not json", json.dumps({"a": 1}), None])
def test_unreadable_answers_stay_could_not_say(monkeypatch, raw) -> None:
    monkeypatch.setattr(bfc, "_gh", lambda args: raw)

    assert bfc._open_prs() is None
