"""A dismissal of his message carries what we sent him right before it.

Andrew, 2026-09-24: "i say proceed becasue what else is there to say? im not
being spoken to.. im being reported at". The combined design, walked with every
relevant lens, decided: a not-an-ask sort must name what came right before his
message, so a bare "proceed" after one of our reports reads as a signal about
the report. This is that decision, built.

The context is what we SENT (Lovelace on walk-9de4e0454b82), captured by the
door rather than typed by the sorter (truth #11a), and it exists to audit OUR
sort -- never as evidence that he approved anything (Foucault on the walk).

Design: docs/drafts/proceed_is_not_noise_draft_2026-09-24.md (Aria-new seat).
"""

from __future__ import annotations

import pytest

from divineos.core import his_asks as ha


@pytest.fixture(autouse=True)
def temp_store(monkeypatch, tmp_path):
    monkeypatch.setenv("DIVINEOS_HIS_ASKS_DB", str(tmp_path / "shared" / "his" / "asks.db"))


# His real words, 2026-09-24, and the shape of what came before them.
PROCEED = "proceed"
OUR_REPORT = (
    "Pushed 32a2f07f. 51 passed across the store, the characterization and the "
    "front door. His real his/ directory was checked absent before and after."
)


def _kept(candidate="c1", text=PROCEED, uuid="u1", sent_before=OUR_REPORT):
    ha.file_candidate(candidate, "p1", text, "2026-09-24T21:00:00Z", "aria")
    return ha.confirm(candidate, uuid, "human", text, sent_before=sent_before)


def test_his_proceed_after_our_report_keeps_the_report_beside_it():
    """The named case from the design: 'not an ask' is recorded against what
    we had just sent him, so it can be read as a signal about our reply."""
    _kept()
    [kept] = ha.pending()
    assert kept.sent_before == OUR_REPORT
    ha.sort("u1", ha.NOT_AN_ASK, "a go-ahead, nothing asked", "aria", addressed_to="aria")
    assert ha.sent_before("u1") == (OUR_REPORT, "captured")


def test_a_dismissal_with_nothing_before_on_record_is_refused():
    _kept(sent_before=None)
    with pytest.raises(ha.HisAsksRefused):
        ha.sort("u1", ha.NOT_AN_ASK, "a go-ahead, nothing asked", "aria", addressed_to="aria")
    assert [k.uuid for k in ha.pending()] == ["u1"]


def test_the_sorter_can_quote_it_when_the_door_could_not_and_it_is_marked_as_theirs():
    _kept(sent_before=None)
    ha.sort(
        "u1",
        ha.NOT_AN_ASK,
        "a go-ahead, nothing asked",
        "aria",
        addressed_to="aria",
        preceded_by=OUR_REPORT,
    )
    assert ha.sent_before("u1") == (OUR_REPORT, "sorter")


def test_what_the_door_captured_is_never_replaced_by_the_sorter():
    """Lamport on the walk: written once; a second write is refused."""
    _kept()
    with pytest.raises(ha.HisAsksRefused):
        ha.sort(
            "u1",
            ha.NOT_AN_ASK,
            "a go-ahead, nothing asked",
            "aria",
            addressed_to="aria",
            preceded_by="something kinder than the report we actually sent",
        )
    assert ha.sent_before("u1") == (OUR_REPORT, "captured")


@pytest.mark.parametrize("kind", [ha.BUILD, ha.STANDING])
def test_a_build_or_standing_sort_does_not_need_it_but_keeps_it(kind):
    """Yudkowsky on the walk: the context is kept for every kind, so filing a
    dismissal as 'standing' does not hide what came before."""
    _kept(sent_before=None)
    ha.sort("u1", kind, "he asked for something", "aria", addressed_to="aria")
    _kept("c2", "build me the thing", "u2")
    ha.sort("u2", kind, "he asked for something", "aria", addressed_to="aria")
    assert ha.sent_before("u2") == (OUR_REPORT, "captured")


def test_an_unmatched_message_can_carry_it_too():
    ha.file_candidate("c1", "p1", PROCEED, "2026-09-24T21:00:00Z", "aria")
    ha.give_up("c1", "no record of it in the transcript within the settle horizon")
    ha.sort(
        "c1",
        ha.NOT_AN_ASK,
        "a go-ahead, nothing asked",
        "aria",
        addressed_to="aria",
        preceded_by=OUR_REPORT,
    )
    assert ha.sent_before("c1") == (OUR_REPORT, "sorter")


def test_it_is_kept_whole():
    """Carmack on the walk: trimming could cut the line he reacted to."""
    long_report = "one line of ours\n" * 400
    _kept(sent_before=long_report)
    assert ha.sent_before("u1") == (long_report, "captured")
