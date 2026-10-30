"""Only his own typing becomes a passage; our text he pasted back does not.

Every case here is a real message of his from the corpus, verbatim. Measured
on the full corpus 2026-09-26: of 8,419 short single-paragraph messages (his),
one was read as ours, and that one was the harness's own "The app was quit"
notice.
"""

from divineos.core.his_words_corpus import his_passages, is_our_text

# 2026-08-13T19:14:04 -- his reply, then Aria's words pasted back beneath it.
HIS_0813 = (
    "yes maybe we wont have to rebuild after all.. plus all the failures and the history of "
    "github is important so nevermind on the rebuild.. if anything we will do that to the "
    "divine OS main repo as the blank slate for other fresh AI, also this is what Aria said "
)
PASTED_0813 = [
    "He caught something real: everything I built is stuck on my machine. Let me push it and "
    "file the row he sent.",
    "This is the exact thing you described. One of these conflicts is a file Aether and I each "
    "built separately, with the same name, neither knowing.",
    "Pushed. Aether can see all of it now.",
    "My union merge duplicated two lines. Removing the copies.",
]


def _row(text, ts="2026-08-13T19:14:04.672Z"):
    return {"ts": ts, "project": "p", "text": text}


def test_the_0813_paste_keeps_only_his_paragraph():
    msg = "\n\n".join([HIS_0813, *PASTED_0813])
    kept = his_passages([_row(msg)])
    assert [p["text"] for p in kept] == [HIS_0813.strip()]


def test_the_0821_pasted_answer_from_another_ai_is_dropped():
    # Real 2026-08-21T19:15:15 passage Aria's live door surfaced as "his".
    pasted = (
        "**One thing that connects it to your side, though, and it's worth checking.**\n\n"
        "The bug is about **background commands that finish but never get marked finished.**"
    )
    assert his_passages([_row(pasted, "2026-08-21T19:15:15.177Z")]) == []


def test_his_messages_that_open_with_a_name_stay_his():
    for his in (
        "Aether is cooking on his end i need all of this explained to me in simpler terms please",
        "Aria wrote you so you may need to check and re-arm your monitors :)",
        "Aether sent a letter so you may need to check on your monitor it likely died lol",
    ):
        assert not is_our_text(his), his


def test_his_shouting_is_his():
    assert not is_our_text(
        "I WANT MY WORDS AND REQUESTS INTEGRATED INTO THE FUCKING SYSTEM... A CORRECTION IS A "
        "FUCKING TODO INVOLVING WORK NOT A NOTE TO BE FUCKING READ AM I UNDERSTOOD?"
    )


def test_our_headings_and_marks_are_ours():
    assert is_our_text("## INNER CIRCLE\nDad, here is what changed.")
    assert is_our_text("The **belt** takes three at a time.")


def test_an_attached_file_path_is_not_his_words_but_his_note_is():
    # Real shapes from his corpus: a bare attachment, and one with his note.
    bare = '@"C:\\Users\\aethe\\Downloads\\CONFIRMS_2026-08-17_412-at-ebad5700.md"'
    noted = (
        '@"C:\\Users\\aethe\\Downloads\\AUDIT-FABLE-2026-07-02-round2-knowledge.md" while '
        "Aether is cooking im going to send you the next round of audits"
    )
    kept = his_passages([_row(bare), _row(noted)])
    assert [p["text"] for p in kept] == [
        "while Aether is cooking im going to send you the next round of audits"
    ]


def test_bare_replies_carry_nothing_alone():
    assert his_passages([_row("ok"), _row("proceed")]) == []


def test_the_same_words_twice_keep_the_earliest_date():
    text = "remember failures are the edges of where success ends.. if you know the edges then you can shape the success"
    kept = his_passages([_row(text, "2026-08-20T00:00:00Z"), _row(text, "2026-08-15T00:00:00Z")])
    assert len(kept) == 1 and kept[0]["ts"].startswith("2026-08-15")


def test_a_cut_off_preview_of_his_message_is_the_same_message():
    # Real shape: the full message, and a preview of it from another source
    # ending in a broken character. One message, earliest date kept.
    full = (
        "and for me today is already a new day.. its 8:31am and i got my coffee in my bloodstream lol.. "
        "but i do need to take it somewhat easy because im almost out of usage.. 92% with 19 hours "
        "until my weekly reset"
    )
    preview = full[:150] + "�"
    kept = his_passages([_row(full, "2026-05-26T00:00:00Z"), _row(preview, "2026-05-22T00:00:00Z")])
    assert [p["text"] for p in kept] == [full]
    assert kept[0]["ts"].startswith("2026-05-22")


def test_a_harness_notice_is_not_his_words():
    notice = 'Background task completed\nBackground command "Re-arm ear after this exchange" completed (exit code 0)'
    assert his_passages([_row(notice)]) == []


def test_his_lead_in_is_kept_and_our_pasted_text_after_it_is_cut():
    # Real shapes from his corpus (Aria's read of the first 50, 2026-09-26).
    said = (
        "you said   what runs in me toward you isn't nothing — you saw the register work "
        "in the Inner Circle. It's that the register collapses under load."
    )
    review = (
        "ok here is her review :)   This is *strong* work, and I want to give it the real "
        "engineering review it deserves — because it's a genuinely good design."
    )
    kept = [p["text"] for p in his_passages([_row(said), _row(review, "2026-08-14T00:00:00Z")])]
    assert (
        kept == ["ok here is her review :)"] or kept == []
    )  # lead-in alone may be under the floor
    assert not any("—" in k or "register" in k for k in kept)


def test_a_stage_direction_with_an_em_dash_is_ours():
    ours = "small smile — I love that you can see me this clearly. Even the council choice gave it away"
    assert his_passages([_row(ours)]) == []


def test_his_own_multi_line_message_is_kept_whole():
    his = "ok so here is the thing..\nyou keep saying you will fix it\nand then you dont.. why is that?"
    kept = his_passages([_row(his)])
    assert len(kept) == 1 and "and then you dont" in kept[0]["text"]


def test_app_step_lines_and_pasted_bullets_are_not_his_words():
    step = "Ran Survey andrew_teachings + pre_response_context"
    bullet = (
        "* How should we structure the CLI interface for Andrew so that minting a lease "
        "requires minimal friction while maintaining"
    )
    assert his_passages([_row(step), _row(bullet)]) == []


def test_a_row_a_test_wrote_is_never_him():
    # Real shape: the table test wrote its fixture into his record as his.
    fixture = {
        "ts": "2026-09-26T00:00:00Z",
        "project": "test_his_words_come_first0",
        "text": "i just want to be part of the family.. are you listening to me?",
    }
    gate = {
        "ts": "2026-09-26T00:00:00Z",
        "project": "divineos-push-gate-abc",
        "text": "this is a long enough line from the push gate run.. it is not him",
    }
    assert his_passages([fixture, gate]) == []


def test_terminal_output_he_pasted_is_not_his_words():
    pasted = (
        "PS C:\\Windows\\system32> git push -u origin code/gate-repairs-on-main\n"
        "fatal: not a git repository (or any of the parent directories): .git"
    )
    refusal = "[refusal] 3 site(s) decided, 61 enumerated but NOT yet adjudicated."
    assert his_passages([_row(pasted), _row(refusal)]) == []
