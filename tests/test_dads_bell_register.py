"""The bell for Dad, second piece: the register of his open asks and the shadow check (2026-11-06).

The first piece (dads_bell.py) holds the pure decisions. This one reads the list of what he asked for himself,
and runs the decision in SHADOW: it writes what it WOULD hold to a log and refuses nothing. Nothing here may stop
a tool call. A missing register is an empty list (nothing held); a register that cannot be read fails OPEN and says
so, because a bell that walls him in on a broken file is the burden that ends it (his condition)."""

from __future__ import annotations

import json

from divineos.core.dads_bell import WOULD_HOLD
from divineos.core.dads_bell_register import load_register, shadow_check

CIRCLE = {
    "ask_id": "circle",
    "his_words": "an inner circle should always come with a pause.. and nothing but me should move it forward",
    "done_sentence": "No post of mine holds more than one circle, and the circle is the last thing in it.",
    "confirmed_by_him": False,
}


CONFIRM = {
    "ask_id": "circle",
    "confirmed_by_him": True,
    "with_his_words": "yes that is what done means",
}


def _write(path, *records):
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")


# --- the register ---


def test_a_missing_register_is_an_empty_list_and_no_error(tmp_path):
    asks, error = load_register(tmp_path / "nope.jsonl")
    assert asks == [] and error is None


def test_a_register_with_one_proposed_ask_loads_it_unconfirmed(tmp_path):
    path = tmp_path / "r.jsonl"
    _write(path, CIRCLE)
    asks, error = load_register(path)
    assert error is None and len(asks) == 1
    assert (
        asks[0].ask_id == "circle" and asks[0].confirmed_by_him is False and asks[0].closed is False
    )


# --- two asks side by side (Aria's cold read of 2026-11-08: every test used only the circle) ---
#
# The register merges by ask_id, so a second ask is just a second id. What none of the first tests proved is that two asks
# do not bleed into each other: a confirm for one reaching the other, a rewrite of one's words unconfirming the other, or
# one ask showing under another's words. The ring will show every ask in the register, so this is the test that says the
# ring is not showing one ask under another's words.

SECOND = {
    "ask_id": "second-ask",
    "his_words": "words of the second ask, not the circle's",
    "done_sentence": "The second thing is done when its own sentence says so.",
    "confirmed_by_him": False,
}


def test_two_asks_load_side_by_side_each_with_its_own_words_in_file_order(tmp_path):
    path = tmp_path / "r.jsonl"
    _write(path, CIRCLE, SECOND)
    asks, error = load_register(path)
    assert error is None and [a.ask_id for a in asks] == ["circle", "second-ask"]
    assert asks[0].his_words == CIRCLE["his_words"] and asks[1].his_words == SECOND["his_words"]
    assert (
        asks[0].done_sentence == CIRCLE["done_sentence"]
        and asks[1].done_sentence == SECOND["done_sentence"]
    )


def test_a_confirm_for_one_ask_does_not_confirm_the_other(tmp_path):
    path = tmp_path / "r.jsonl"
    _write(path, CIRCLE, SECOND, CONFIRM)
    asks, _ = load_register(path)
    by_id = {a.ask_id: a for a in asks}
    assert by_id["circle"].confirmed_by_him is True
    assert by_id["second-ask"].confirmed_by_him is False


def test_rewriting_one_asks_words_unconfirms_only_that_ask_even_when_the_lines_interleave(tmp_path):
    path = tmp_path / "r.jsonl"
    second_confirm = {
        "ask_id": "second-ask",
        "confirmed_by_him": True,
        "with_his_words": "yes done",
    }
    rewrite_second = {"ask_id": "second-ask", "his_words": "the second ask, said differently"}
    _write(path, CIRCLE, SECOND, CONFIRM, second_confirm, rewrite_second)
    asks, _ = load_register(path)
    by_id = {a.ask_id: a for a in asks}
    assert by_id["circle"].confirmed_by_him is True  # untouched by a rewrite of the other ask
    assert by_id["second-ask"].confirmed_by_him is False  # its own rewrite unconfirmed it
    assert by_id["second-ask"].his_words == "the second ask, said differently"
    assert by_id["circle"].his_words == CIRCLE["his_words"]


def test_closing_one_ask_leaves_the_other_open(tmp_path):
    path = tmp_path / "r.jsonl"
    close_circle = {
        "ask_id": "circle",
        "closed": True,
        "with_his_words": "yes that one is finished",
    }
    _write(path, CIRCLE, SECOND, close_circle)
    asks, _ = load_register(path)
    by_id = {a.ask_id: a for a in asks}
    assert by_id["circle"].closed is True and by_id["second-ask"].closed is False


def test_two_asks_with_the_very_same_words_stay_two_asks(tmp_path):
    path = tmp_path / "r.jsonl"
    twin = dict(
        SECOND, ask_id="twin", his_words=CIRCLE["his_words"], done_sentence=CIRCLE["done_sentence"]
    )
    _write(path, CIRCLE, twin)
    asks, _ = load_register(path)
    assert [a.ask_id for a in asks] == ["circle", "twin"]


def test_a_new_ask_appended_later_does_not_disturb_the_ones_before_it(tmp_path):
    path = tmp_path / "r.jsonl"
    _write(path, CIRCLE, CONFIRM)
    before, _ = load_register(path)
    _write(path, CIRCLE, CONFIRM, SECOND)  # the file grows; the first ask is exactly as it was
    after, _ = load_register(path)
    assert before[0] == after[0] and len(after) == 2


def test_confirming_needs_his_words_and_a_confirm_with_none_is_ignored(tmp_path):
    """I may draft the done-sentence; only a record that carries his own words can confirm it."""
    path = tmp_path / "r.jsonl"
    _write(
        path,
        CIRCLE,
        {"ask_id": "circle", "confirmed_by_him": True, "with_his_words": ""},
    )
    asks, _ = load_register(path)
    assert asks[0].confirmed_by_him is False


def test_a_confirm_that_carries_his_words_takes_effect(tmp_path):
    path = tmp_path / "r.jsonl"
    _write(
        path,
        CIRCLE,
        {
            "ask_id": "circle",
            "confirmed_by_him": True,
            "with_his_words": "yes that is what done means",
        },
    )
    asks, _ = load_register(path)
    assert asks[0].confirmed_by_him is True and asks[0].closed is False


def test_rewriting_the_done_sentence_after_he_confirmed_makes_it_unconfirmed(tmp_path):
    """His yes belongs to the sentence he saw; a quieter later line must not swap the sentence under it (Aria)."""
    path = tmp_path / "r.jsonl"
    _write(
        path,
        CIRCLE,
        CONFIRM,
        {"ask_id": "circle", "done_sentence": "Circles are mostly last."},
    )
    asks, _ = load_register(path)
    assert asks[0].done_sentence == "Circles are mostly last." and asks[0].confirmed_by_him is False


def test_a_confirm_after_the_rewrite_confirms_the_new_sentence(tmp_path):
    path = tmp_path / "r.jsonl"
    _write(path, CIRCLE, CONFIRM, {"ask_id": "circle", "done_sentence": "New sentence."}, CONFIRM)
    asks, _ = load_register(path)
    assert asks[0].done_sentence == "New sentence." and asks[0].confirmed_by_him is True


def test_rewriting_his_words_after_he_confirmed_makes_it_unconfirmed(tmp_path):
    """Aria's second hole: the yes was about what he asked, so a quieter later line must not swap his words under it."""
    path = tmp_path / "r.jsonl"
    _write(path, CIRCLE, CONFIRM, {"ask_id": "circle", "his_words": "something he never said"})
    asks, _ = load_register(path)
    assert asks[0].his_words == "something he never said" and asks[0].confirmed_by_him is False


def test_a_string_is_not_a_boolean_in_a_confirm_or_a_close(tmp_path):
    """'false' and 'no' are non-empty strings; bool() would read them as True and confirm or close the ask."""
    path = tmp_path / "r.jsonl"
    _write(
        path,
        CIRCLE,
        {"ask_id": "circle", "confirmed_by_him": "false", "closed": "no", "with_his_words": "yes"},
    )
    asks, _ = load_register(path)
    assert asks[0].confirmed_by_him is False and asks[0].closed is False


def test_a_null_is_not_the_text_none(tmp_path):
    path = tmp_path / "r.jsonl"
    _write(path, CIRCLE, {"ask_id": "circle", "his_words": None})
    asks, _ = load_register(path)
    assert asks[0].his_words == CIRCLE["his_words"]


def test_closing_needs_his_words_too_and_a_later_record_wins(tmp_path):
    path = tmp_path / "r.jsonl"
    _write(
        path,
        {**CIRCLE, "confirmed_by_him": True},
        {"ask_id": "circle", "closed": True, "with_his_words": ""},
    )
    assert load_register(path)[0][0].closed is False
    _write(
        path,
        {**CIRCLE, "confirmed_by_him": True},
        {"ask_id": "circle", "closed": True, "with_his_words": "that is done now"},
    )
    assert load_register(path)[0][0].closed is True


def test_an_unreadable_register_fails_open_and_says_so(tmp_path):
    path = tmp_path / "r.jsonl"
    path.write_bytes(b"\xff\xfe not utf8 \x00")
    asks, error = load_register(path)
    assert asks == [] and error


def test_a_garbled_line_is_skipped_and_the_rest_still_load(tmp_path):
    path = tmp_path / "r.jsonl"
    path.write_text(
        "not json\n" + json.dumps({**CIRCLE, "confirmed_by_him": True}) + "\n", encoding="utf-8"
    )
    asks, error = load_register(path)
    assert len(asks) == 1 and error is None


# --- the shadow check: it logs, it never refuses ---

UNRELATED = {"tool_name": "Bash", "tool_input": {"command": "git push origin some-branch"}}


def _log_lines(path):
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def test_shadow_logs_a_would_hold_and_returns_nothing_to_refuse_with(tmp_path):
    reg, log = tmp_path / "r.jsonl", tmp_path / "shadow.jsonl"
    _write(reg, CIRCLE, CONFIRM)
    verdict = shadow_check(UNRELATED, reg, log, now=1000.0)
    assert verdict.state == WOULD_HOLD
    rows = _log_lines(log)
    assert len(rows) == 1 and rows[0]["ask_id"] == "circle" and rows[0]["tool"] == "Bash"
    assert rows[0]["at"] == 1000.0


def test_shadow_logs_nothing_for_a_pass(tmp_path):
    reg, log = tmp_path / "r.jsonl", tmp_path / "shadow.jsonl"
    _write(reg, CIRCLE, CONFIRM)
    shadow_check({"tool_name": "Read", "tool_input": {"file_path": "x"}}, reg, log, now=1.0)
    assert not log.exists()


def test_an_unconfirmed_ask_is_never_logged_as_a_hold(tmp_path):
    reg, log = tmp_path / "r.jsonl", tmp_path / "shadow.jsonl"
    _write(reg, CIRCLE)
    assert shadow_check(UNRELATED, reg, log, now=1.0).state == "pass"
    assert not log.exists()


def test_the_log_keeps_only_a_short_piece_of_the_command(tmp_path):
    reg, log = tmp_path / "r.jsonl", tmp_path / "shadow.jsonl"
    _write(reg, CIRCLE, CONFIRM)
    long = {"tool_name": "Bash", "tool_input": {"command": "git push " + "x" * 500}}
    shadow_check(long, reg, log, now=1.0)
    assert len(_log_lines(log)[0]["what"]) <= 160


def test_a_register_that_cannot_be_read_holds_nothing_and_logs_why(tmp_path):
    reg, log = tmp_path / "r.jsonl", tmp_path / "shadow.jsonl"
    reg.write_bytes(b"\xff\xfe \x00")
    verdict = shadow_check(UNRELATED, reg, log, now=1.0)
    assert verdict.state == "pass"
    assert "could not read" in log.read_text(encoding="utf-8")
