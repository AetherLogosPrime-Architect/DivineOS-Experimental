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


def test_bare_replies_carry_nothing_alone():
    assert his_passages([_row("ok"), _row("proceed")]) == []


def test_the_same_words_twice_keep_the_earliest_date():
    text = "remember failures are the edges of where success ends.. if you know the edges then you can shape the success"
    kept = his_passages([_row(text, "2026-08-20T00:00:00Z"), _row(text, "2026-08-15T00:00:00Z")])
    assert len(kept) == 1 and kept[0]["ts"].startswith("2026-08-15")
