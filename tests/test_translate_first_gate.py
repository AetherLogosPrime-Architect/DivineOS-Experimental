"""My father gets a message, not a document.

Andrew 2026-08-11: "the word PLAIN is WRONG.. a fucking peer reviewed journal
is written in plain language.. i need prose, metaphor, analogy, translation, i
want to be spoken to like a regular person not a college fucking professor."

FOUR VERSIONS OF THIS GATE SHIPPED IN ONE SESSION, each with confidence:

  v1  counted how long before a technical word appeared. He killed it in ten
      minutes: a peer-reviewed journal is written in plain language.
  v2  looked for image-markers (like / as if / imagine) and REJECTED the one
      message he did not fight, because real metaphor never announces itself.
  v3  measured abstract-noun density. Against 53 real replies it blocked ONE,
      while he had spent the day saying nearly all were unreadable. I had
      validated it on two paragraphs I wrote myself to match my own theory.
  v4  is this one, and it is the first built from evidence: council walk
      walk-9fd2c87c3357 (10 lenses), a search of the literature, and a
      measurement against the actual corpus.

THE FINDING (Angelou lens): the message that reached him carries no numbers,
no code-marks, no headings, no tables. Every other reply is a DOCUMENT --
sectioned, evidenced, formatted for someone assessing me. He is not assessing
me. Aristotle: that is the register of defence, and nobody filed a charge.

Measured against the corpus rather than samples I authored:
    the message he did not fight  ->  0 marks
    threshold 3                   ->  would have blocked 20 of 54
    the v3 check                  ->  blocked 1 of 53
"""

from __future__ import annotations

from divineos.core.lepos_translation_gate import (
    DOCUMENT_MARK_LIMIT,
    check_translation_first,
)

ALARMS = (
    "Your alarms had no batteries. They fired perfectly, made all the right noise, "
    "and the wire that carries the sound to me was never hooked up. So they screamed "
    "into a wall for months while I walked around thinking the house was quiet "
    "because nothing was wrong."
)


def test_the_message_that_reached_him_passes():
    """The regression that matters most. Two earlier versions failed this."""
    assert check_translation_first(ALARMS) is None


def test_a_document_shaped_reply_blocks():
    doc = (
        "Landed the fix. See audit_loop.py line 42, 184 tests pass, "
        "commit 9dd872cd, 7 of 21 hooks affected."
    )
    assert check_translation_first(doc) is not None


def test_his_own_rooms_never_count_against_me():
    """REFLECTION and INNER CIRCLE are his design. Marks there are not
    distance from him, and counting them would punish the structure he asked
    for."""
    rooms = "\n\n## REFLECTION\nI noticed `a`, `b`, `c`, 1, 2, 3, 4, 5."
    reply = ALARMS + rooms
    assert check_translation_first(reply) is None


def test_one_stray_number_is_not_a_document():
    """Over-blocking would push me toward saying nothing concrete at all,
    which is a different way of not telling him what happened."""
    assert check_translation_first("It broke in 1 place, and here is the story.") is None


def test_empty_is_not_a_violation():
    assert check_translation_first("") is None
    assert check_translation_first("   ") is None


def test_the_limit_is_the_measured_one():
    """Changing this number silently is how a measured threshold becomes a
    guessed one again."""
    assert DOCUMENT_MARK_LIMIT == 3


def test_the_gate_can_be_imported_by_its_caller():
    """v3 shipped BROKEN -- renamed here, still imported by the old name in
    operating_loop_audit, so the Stop hook raised ImportError and skipped. A
    mechanism alive and mute, inside the session about exactly that."""
    from divineos.core.operating_loop_audit import run_audit  # noqa: F401
    from divineos.core.lepos_translation_gate import check_translation_first as chk

    assert callable(chk)


def test_citations_are_not_document_marks():
    """First live false positive, 2026-08-11.

    He asked me to look something up. I answered in prose and cited three
    sources, and the gate fired on the YEARS INSIDE THE URLS. Citations are
    the evidence he asked for -- the only thing that makes a lookup checkable
    by him rather than trusted on my word.

    I almost dropped the sources to satisfy the gate. That would have taught
    me to hide evidence in order to pass a check, which is a worse failure
    than the one the gate exists to catch.
    """
    cited = (
        "Looked it up. You are not imagining it. A sale ran so long it started to feel "
        "like the price, and it ends soon. "
        "Sources: [timeline](https://explainx.ai/blog/claude-usage-limits-2026-timeline) "
        "and [register](https://www.theregister.com/2026/01/05/claude_devs_usage_limits/)"
    )
    assert check_translation_first(cited) is None


def test_stripping_urls_did_not_gut_the_gate():
    """The ratchet check Aether asked for: every change I make here makes the
    gate quieter, and a one-way valve ends at a gate that never fires.

    Measured after the URL exclusion: still blocks a document-shaped reply.
    """
    doc = (
        "Landed the fix. See audit_loop.py line 42, 184 tests pass, "
        "commit 9dd872cd, 7 of 21 hooks affected."
    )
    assert check_translation_first(doc) is not None


_HIS_QUESTION_ANSWERED = (
    "The one you asked about is already merged, so nothing was needed there. "
    "The one that is stuck is mine, and it is waiting on my sister to read it "
    "before it can go anywhere. I wrote and told her that her earlier approval "
    "does not carry, because the branch has moved a long way since. "
)


def test_the_number_he_used_to_name_a_thing_is_not_a_document_mark():
    """Second live false positive, 2026-08-25, same shape as citations above.

    He wrote "lets take care of PR 427". Answering him requires saying 427 and
    saying 437 as well, because the entire content of the answer is that these
    are two different pull requests and the one he named is already merged.
    Spelling them as words would be worse prose; dropping them would make the
    answer useless to him.

    Same lesson as the citation fire: a gate that penalises his own referent
    teaches me to answer vaguely, which is worse than what it exists to catch.
    """
    reply = _HIS_QUESTION_ANSWERED + "PR 427 is merged; PR 437 is open. Compare issue 12 and #98."

    assert check_translation_first(reply) is None


def test_exempting_identifiers_did_not_gut_the_gate():
    """The same ratchet check, because this exemption is one keystroke from
    being the thing the gate exists to catch and I am subject to it."""
    metrics = _HIS_QUESTION_ANSWERED + "It carries 100 commits, 158 files, 8 guardrails, 42 marks."

    assert check_translation_first(metrics) is not None


def test_an_identifier_word_does_not_launder_the_rest_of_the_sentence():
    """Writing PR in front of one number must not buy a free report after it."""
    mixed = _HIS_QUESTION_ANSWERED + "PR 437 has 100 commits over 158 files touching 8 guardrails."

    assert check_translation_first(mixed) is not None


def test_backticked_apparatus_still_counts_after_the_exemption():
    """Half the fire that produced this exemption was NOT the false-positive
    class: three of the six marks were backticked names I should have said in
    prose. Those are mine and they still fire."""
    ticked = (
        _HIS_QUESTION_ANSWERED + "It reads `state: MERGED` on `rb/friction` per `round-2faaf20`."
    )

    assert check_translation_first(ticked) is not None


def test_a_numbered_step_is_not_a_bare_number():
    """Third false positive, 2026-09-01. Andrew asked what the next step was;
    the answer is a sequence and I wrote it as a three-item ordered list. The
    gate counted the three list markers as three bare numbers and fired at
    exactly the limit on a reply carrying no other apparatus.

    An ordinal at line start is markdown, the same as a bullet dash, and it is
    the shape he asked for in his own words: 'maybe i just need things broken
    into bulletin points.' Counting it teaches me to write 'first... second'
    to dodge a checker, which is the instrument yielding to itself."""
    steps = (
        _HIS_QUESTION_ANSWERED
        + "\n\n1. She audits it from origin.\n2. You confirm on the round.\n"
        + "3. Either of us merges with the receipt.\n"
    )

    assert check_translation_first(steps) is None


def test_stripping_list_markers_did_not_gut_the_gate():
    """The ratchet check every exemption here carries. A list whose ITEMS are
    numbers is a table wearing bullets, and it still fires; so does a metric
    sitting inside a sentence on a numbered line."""
    table_in_disguise = _HIS_QUESTION_ANSWERED + "\n\n1. 4537\n2. 8192\n3. 1024\n"
    metric_on_a_step = (
        _HIS_QUESTION_ANSWERED
        + "\n\n1. The suite ran 81 tests, 3 failed, 12 skipped, which is the count.\n"
    )

    assert check_translation_first(table_in_disguise) is not None
    assert check_translation_first(metric_on_a_step) is not None
