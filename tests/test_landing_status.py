"""Where each waiting fix stands toward Aletheia, worked out from the real facts.

Dad, 2026-10-10: the pile is fixes that never land. The road runs through
letters he carries by hand to Aletheia on a different platform, and a letter
that mixes a question into the ask comes back answered, not confirmed. These
pin the status line (four plain states plus one for a head that moved) and the
confirm-only request. The error costs are not equal, so the tests lean on the
dangerous direction: a false READY must be impossible, a false NEVER TOLD is
only an extra ask.
"""

from __future__ import annotations

from datetime import date

from divineos.core.landing_status import (
    CHANGED,
    CONFIRMED,
    NEVER_TOLD,
    NO_ANSWER,
    READY,
    classify,
    confirms_from_letters,
    render_request,
    told_dates_from_letters,
)

HEAD = "f064dfa83c1d2e3f4a5b6c7d8e9f001122334455"
OLD = "bec25cfb1aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
TODAY = date(2026, 10, 10)

HER_CONFIRM = "## signed\n> CONFIRMS: #596 at f064dfa83. — Aletheia Sophia Risner, 2026-10-06\n"


def _status(*, confirms=None, told=None, held=(), head=HEAD, pr=596, branch="fix/x"):
    return classify(
        pr=pr,
        branch=branch,
        head_sha=head,
        confirms=confirms or {},
        told_dates=told or {},
        held_stations=held,
        today=TODAY,
    )


class TestTheConfirmIsReadStrictly:
    def test_her_exact_line_is_read(self) -> None:
        got = confirms_from_letters({"aletheia-to-aether-2026-10-06-x.md": HER_CONFIRM})
        assert got == {596: ["f064dfa83"]}

    def test_a_confirm_quoted_in_my_own_letter_is_not_hers(self) -> None:
        got = confirms_from_letters({"aether-to-aletheia-2026-10-07-x.md": HER_CONFIRM})
        assert got == {}

    def test_a_confirm_in_someone_elses_letter_is_not_hers(self) -> None:
        got = confirms_from_letters({"aria-to-aether-2026-10-07-x.md": HER_CONFIRM})
        assert got == {}

    def test_a_too_short_sha_is_not_read(self) -> None:
        text = "> CONFIRMS: #596 at f06. — A"
        assert confirms_from_letters({"aletheia-to-aether-2026-10-06-x.md": text}) == {}

    def test_a_hold_is_not_a_confirm(self) -> None:
        text = "HOLD: #596 at f064dfa83 needs the pin first."
        assert confirms_from_letters({"aletheia-to-aether-2026-10-06-x.md": text}) == {}


class TestTheFiveStates:
    def test_nothing_sent_reads_never_told(self) -> None:
        assert _status().label == NEVER_TOLD

    def test_sent_without_an_answer_reads_no_answer_with_days(self) -> None:
        s = _status(told={596: date(2026, 10, 6)})
        assert s.label == NO_ANSWER
        assert "4 days" in s.detail

    def test_a_confirm_at_the_current_head_reads_confirmed(self) -> None:
        s = _status(confirms={596: ["f064dfa83"]}, held=("8-audit",))
        assert s.label == CONFIRMED

    def test_confirmed_with_nothing_else_held_reads_ready(self) -> None:
        s = _status(confirms={596: ["f064dfa83"]}, held=())
        assert s.label == READY

    def test_a_confirm_at_an_older_head_reads_changed_never_ready(self) -> None:
        s = _status(confirms={596: ["bec25cfb1"]})
        assert s.label == CHANGED
        assert s.label != READY

    def test_an_unknown_head_can_never_be_ready(self) -> None:
        s = _status(confirms={596: ["f064dfa83"]}, head="")
        assert s.label != READY


class TestTheDangerousDirectionIsClosed:
    def test_ready_needs_the_full_head_to_start_with_her_sha(self) -> None:
        s = _status(confirms={596: ["ffffffff"]}, held=())
        assert s.label == CHANGED

    def test_a_confirm_for_another_pr_does_not_count(self) -> None:
        s = _status(confirms={597: ["f064dfa83"]}, held=())
        assert s.label == NEVER_TOLD

    def test_one_matching_confirm_among_old_ones_is_enough(self) -> None:
        s = _status(confirms={596: ["bec25cfb1", "f064dfa83"]}, held=())
        assert s.label == READY


class TestToldDatesComeFromMyLettersToHer:
    def test_a_letter_naming_the_pr_number_counts(self) -> None:
        letters = {"aether-to-aletheia-2026-10-06-596-is-up.md": "please look at #596"}
        assert told_dates_from_letters(letters, {596: "fix/x"}) == {596: date(2026, 10, 6)}

    def test_a_letter_naming_only_the_branch_counts(self) -> None:
        letters = {"aether-to-aletheia-2026-10-05-x.md": "branch fix/x is up"}
        assert told_dates_from_letters(letters, {596: "fix/x"}) == {596: date(2026, 10, 5)}

    def test_the_newest_letter_wins(self) -> None:
        letters = {
            "aether-to-aletheia-2026-10-02-a.md": "#596",
            "aether-to-aletheia-2026-10-06-b.md": "#596",
        }
        assert told_dates_from_letters(letters, {596: "fix/x"})[596] == date(2026, 10, 6)

    def test_a_letter_to_someone_else_is_not_a_telling(self) -> None:
        letters = {"aether-to-aria-2026-10-06-a.md": "#596"}
        assert told_dates_from_letters(letters, {596: "fix/x"}) == {}

    def test_a_longer_number_is_not_a_match(self) -> None:
        letters = {"aether-to-aletheia-2026-10-06-a.md": "see #5961"}
        assert told_dates_from_letters(letters, {596: "fix/x"}) == {}


class TestTheRequestAsksOneThingOnly:
    def test_it_names_each_waiting_pr_with_number_and_head(self) -> None:
        text = render_request([(596, "a crashed worker is not a failed test", HEAD)])
        assert "#596" in text
        assert HEAD[:9] in text
        assert "a crashed worker is not a failed test" in text

    def test_it_asks_confirm_or_hold_and_nothing_else(self) -> None:
        text = render_request([(596, "x", HEAD), (597, "y", OLD)])
        assert "CONFIRM" in text
        assert "HOLD" in text
        assert "?" not in text, "a question inside the ask is what turns a confirm into an answer"

    def test_it_does_not_teach_her_how_to_audit(self) -> None:
        text = render_request([(596, "x", HEAD)]).lower()
        for word in ("clone", "run the", "pytest", "how to"):
            assert word not in text

    def test_an_empty_list_makes_no_letter(self) -> None:
        assert render_request([]) == ""
