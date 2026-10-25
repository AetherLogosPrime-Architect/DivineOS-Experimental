"""A reply may not say a pull request waits on Aletheia until a letter to her names it at its live head.

2026-10-25, Dad: *"you continue to say 'Waits for Aletheia' without sending her a letter lol so that needs
fixed."* The sentence cost nothing to write and was true of nobody: #722 and #723 sat "waiting" for hours with no
letter naming them, and #701 changed head after the letter that named it. A note that says it will remember is the
failure this house keeps meeting; this is the door that makes the claim and the letter arrive together.

Everything here injects the letters and the head lookup, so no network and no real folder is touched. The controls
(a letter that names the live head, a merged fix, a sentence that is not a waiting claim) matter as much as the cases.
"""

from __future__ import annotations

from divineos.core.waiting_claim import assess, render_block

HEAD_701 = "58eb739159d4991e9815a6af047d99b16dc37d3a"
HEAD_722 = "5b7be7f1c263006eaaf64e9f4ce1627713f391ab"


def heads(table):
    return lambda n: table.get(n)


OPEN = {701: ("OPEN", HEAD_701), 722: ("OPEN", HEAD_722)}


def test_a_waiting_claim_with_no_letter_is_refused():
    v = assess("#722 waits on Aletheia.", {}, heads(OPEN))
    assert [m.pr for m in v.missing] == [722]
    assert "722" in render_block(v)


def test_two_numbers_in_one_sentence_are_both_checked():
    v = assess("#701 and #722 are waiting on Aletheia now.", {}, heads(OPEN))
    assert sorted(m.pr for m in v.missing) == [701, 722]


def test_a_letter_that_names_the_pr_and_its_live_head_clears_it():
    letters = {"aether-to-aletheia-2026-10-25-x.md": "#722 at `5b7be7f1c` is ready for your read."}
    v = assess("#722 waits on Aletheia.", letters, heads(OPEN))
    assert v.missing == []


def test_a_letter_naming_an_older_head_does_not_clear_it():
    letters = {"aether-to-aletheia-2026-10-25-x.md": "#701 at `3b1996b81` is ready for your read."}
    v = assess("#701 is waiting for Aletheia.", letters, heads(OPEN))
    assert [m.pr for m in v.missing] == [701]
    assert "58eb73915" in render_block(v)


def test_a_letter_to_somebody_else_does_not_count():
    letters = {"aether-to-aria-2026-10-25-x.md": "#722 at 5b7be7f1c, please read."}
    v = assess("#722 waits on Aletheia.", letters, heads(OPEN))
    assert [m.pr for m in v.missing] == [722]


def test_a_sentence_that_is_not_a_waiting_claim_is_left_alone():
    for text in (
        "I sent Aletheia the letter for #722.",
        "#722 is a draft of two prose files.",
        "Aletheia confirmed #701 this morning.",
        "I will write to Aletheia about #722 next.",
    ):
        assert assess(text, {}, heads(OPEN)).missing == [], text


def test_a_merged_or_closed_fix_is_not_asked_for():
    table = {701: ("MERGED", HEAD_701)}
    assert assess("#701 waited on Aletheia and merged.", {}, heads(table)).missing == []
    assert assess("#701 is waiting on Aletheia.", {}, heads(table)).missing == []


def test_an_unreadable_head_is_could_not_check_never_a_pass_and_never_a_block():
    v = assess("#722 waits on Aletheia.", {}, heads({}))
    assert v.missing == []
    assert v.could_not_check


def test_a_waiting_claim_about_nobody_in_particular_is_not_this_door():
    assert assess("#722 is waiting on checks.", {}, heads(OPEN)).missing == []


def test_a_pronoun_in_a_different_sentence_is_not_a_claim_this_door_can_place():
    v = assess("Aletheia has the letter. #722 is with her now.", {}, heads(OPEN))
    assert v.missing == []


def test_the_refusal_names_what_to_do_and_prescribes_the_existing_request_writer():
    v = assess("#722 waits on Aletheia.", {}, heads(OPEN))
    assert "divineos landing --request" in render_block(v)


# ---- the wiring: the surface exists, is registered on Stop, and refuses through the real functions ----------------


def test_the_surface_is_registered_on_stop():
    from divineos.core import hook_router as hr
    from divineos.core import hook_surfaces as hs

    hs.install()
    assert "waiting_claim" in hr.registered("Stop")


def test_the_real_surface_refuses_a_waiting_claim_and_passes_a_told_one(monkeypatch):
    from divineos.core import hook_surfaces as hs
    from divineos.core import landing_status, waiting_claim

    monkeypatch.setattr(hs, "_last_assistant_text", lambda payload: "#722 waits on Aletheia.")
    monkeypatch.setattr(waiting_claim, "real_head_of", heads(OPEN))
    monkeypatch.setattr(landing_status, "read_letters", lambda: {})
    out = hs.waiting_claim_surface({})
    assert out.refused and "722" in out.reason

    told = {"aether-to-aletheia-2026-10-25-x.md": "#722 at 5b7be7f1c is ready for you."}
    monkeypatch.setattr(landing_status, "read_letters", lambda: told)
    assert not hs.waiting_claim_surface({}).refused
