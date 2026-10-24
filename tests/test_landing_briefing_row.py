"""The pile arrives unasked: a briefing row for the fixes waiting on the auditor.

Dad, 2026-10-10: the pile is fixes that never land. A command I have to
remember to run fails by construction, so the counts ride the briefing. The
briefing does not read the readiness board, so it must never be able to say a
fix is READY, and a pile it could not read must show as a row, not as silence.
The words are plain ones (walk-0032613dac1c, Wayne): he reads this too.
"""

from __future__ import annotations

from datetime import date

import pytest

from divineos.core import briefing_dashboard as bd
from divineos.core import landing_status as ls

HEAD = "f064dfa83c1d2e3f4a5b6c7d8e9f001122334455"


def _pr(n: int, head: str = HEAD, branch: str | None = None) -> dict:
    return {
        "number": n,
        "headRefName": branch or f"fix/thing-{n}",
        "headRefOid": head,
        "title": f"title {n}",
    }


def _letters(*, told: list[int] = (), confirmed: dict[int, str] | None = None) -> dict[str, str]:
    letters = {f"aether-to-aletheia-2026-10-08-x{n}.md": f"please look at #{n}" for n in told}
    for n, sha in (confirmed or {}).items():
        letters[f"aletheia-to-aether-2026-10-09-c{n}.md"] = f"> CONFIRMS: #{n} at {sha}. — A"
    return letters


@pytest.fixture
def pile(monkeypatch):
    def set_pile(prs, letters):
        monkeypatch.setattr(ls, "open_prs", lambda: prs)
        monkeypatch.setattr(ls, "read_letters", lambda: letters)
        monkeypatch.setattr(ls, "today", lambda: date(2026, 10, 10))

    return set_pile


def test_no_open_prs_shows_no_row(pile) -> None:
    pile([], {})
    assert bd._row_landing() is None


def test_the_counts_are_shown_in_plain_words(pile) -> None:
    prs = [_pr(1), _pr(2), _pr(3, branch="fix/unmentioned")]
    pile(prs, _letters(told=[1, 2], confirmed={2: "bec25cfb1"}))
    row = bd._row_landing()
    assert row is not None
    assert row.count == 3
    assert "1 changed since she looked" in row.detail
    assert "1 waiting on her answer" in row.detail
    assert "1 never asked" in row.detail


def test_the_ones_needing_a_fresh_ask_are_what_is_stale(pile) -> None:
    prs = [_pr(1), _pr(2), _pr(3, branch="fix/unmentioned")]
    pile(prs, _letters(told=[1, 2], confirmed={2: "bec25cfb1"}))
    assert bd._row_landing().stale_count == 2


def test_the_oldest_wait_is_shown_beside_the_count(pile) -> None:
    pile([_pr(1)], _letters(told=[1]))
    assert "oldest ask 2 days ago" in bd._row_landing().detail


def test_the_briefing_can_never_say_ready(pile) -> None:
    """Her confirm names the live head, but the board was not read here."""
    pile([_pr(1)], _letters(told=[1], confirmed={1: "f064dfa83"}))
    detail = bd._row_landing().detail
    assert "1 confirmed" in detail
    assert "board not read here" in detail
    assert "ready" not in detail.replace("none can show ready", "")


def test_the_cloud_helpers_share_of_the_pile_is_counted(pile) -> None:
    """2026-10-09: sixteen drafts from the helper read as the pile growing, and
    nobody had been told how many to expect. The row says how many came from
    it, so a flood is visible the first morning."""
    prs = [
        _pr(1, branch="cloud/repro-a"),
        _pr(2, branch="cloud/repro-b"),
        _pr(3, branch="fix/own-work"),
    ]
    pile(prs, _letters(told=[1, 2, 3]))
    assert "2 of these came from the cloud helper" in bd._row_landing().detail


def test_no_cloud_helper_work_adds_no_words(pile) -> None:
    pile([_pr(1, branch="fix/own-work")], _letters(told=[1]))
    assert "cloud helper" not in bd._row_landing().detail


class TestTheDefaultBriefingActuallyCarriesIt:
    """The first version of this row was tested through its own helper and
    never reached the default briefing (multiplex panels since 2026-05-22; the
    dashboard rows render only behind --legacy). Found by running the real
    briefing and reading it. These assert the chain at its far end."""

    def _panels(self):
        from divineos.core import multiplex_panels as mp

        return {p.name: p for p in mp.build_panels("chatting")}

    def test_the_pile_is_a_panel_in_the_default_build(self, pile) -> None:
        pile([_pr(1), _pr(2)], _letters(told=[1]))
        assert "waiting_on_aletheia" in self._panels()

    def test_it_speaks_in_the_voice_the_briefing_requires(self, pile) -> None:
        from divineos.core.multiplex_voice import check_voice

        pile([_pr(1), _pr(2)], _letters(told=[1]))
        content = self._panels()["waiting_on_aletheia"].content
        assert content.startswith("I have 2 fixes waiting on Aletheia")
        assert check_voice(content).passed, check_voice(content).summary()
        assert 80 <= len(content) <= 600

    def test_it_reaches_the_rendered_text_not_only_the_list(self, pile) -> None:
        from divineos.core import multiplex_panels as mp
        from divineos.core.multiplex_renderer import render_multiplex

        pile([_pr(1), _pr(2)], _letters(told=[1, 2]))
        assert "fixes waiting on Aletheia" in render_multiplex(mp.build_panels("chatting"))

    def test_one_fix_reads_as_one_fix(self, pile) -> None:
        pile([_pr(1)], _letters(told=[1]))
        assert self._panels()["waiting_on_aletheia"].content.startswith(
            "I have 1 fix waiting on Aletheia"
        )

    def test_with_no_pile_there_is_no_panel(self, pile) -> None:
        """The control: the test can fail, so a pass means something."""
        pile([], {})
        assert "waiting_on_aletheia" not in self._panels()

    def test_an_unreadable_pile_still_speaks(self, pile) -> None:
        pile(None, {})
        content = self._panels()["waiting_on_aletheia"].content
        assert "could not read" in content.lower()

    def test_the_panel_names_the_cloud_helpers_share(self, pile) -> None:
        pile([_pr(1, branch="cloud/a"), _pr(2, branch="cloud/b")], _letters(told=[1, 2]))
        assert (
            "2 of these came from the cloud helper" in self._panels()["waiting_on_aletheia"].content
        )


def test_a_pile_it_could_not_read_is_a_row_not_silence(pile) -> None:
    pile(None, {})
    row = bd._row_landing()
    assert row is not None
    assert "could not read" in row.detail.lower()


def test_the_preview_lists_only_what_a_person_can_act_on(pile) -> None:
    prs = [_pr(1), _pr(2), _pr(3, branch="fix/unmentioned")]
    pile(prs, _letters(told=[1, 2], confirmed={2: "bec25cfb1"}))
    preview = "\n".join(bd._row_landing().preview)
    assert "#2" in preview and "#3" in preview
    assert "#1" not in preview


def test_the_row_points_at_the_command_that_drafts_the_request(pile) -> None:
    pile([_pr(1)], {})
    assert "landing --request" in bd._row_landing().drill_down


def test_the_row_is_registered_in_the_briefing() -> None:
    assert bd._row_landing in bd._ROW_FNS
