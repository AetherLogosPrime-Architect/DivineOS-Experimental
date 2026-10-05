"""His own words cannot be jargon aimed at him.

THE THIRD FALSE POSITIVE OF THIS GATE, and the one that finally names the axis.

Andrew wrote "they have the new fable 5.1 model i can switch you over to it"
and asked me to research it. Answering required saying which model. The gate
counted the version inside its NAME as bare numbers and blocked the reply.

The two earlier exemptions were this same rule found narrowly: the years inside
citation links, and a pull-request number he had used to name the thing. Both
were HIS referents. Neither author saw the general case, and I was one of them.

WHY NOT JUST WIDEN THE KEYWORD LIST. Its own comment says it sits one keystroke
from becoming the thing the gate exists to stop, and that is right: every entry
added to a list of allowed words is an entry I chose, which makes it an entry
the composer can reach for. Adding "model" or "version" would have been the
enumeration reflex -- an allowlist growing by one each time it costs something,
which is the exact shape repaired in a different gate hours earlier the same
day.

So the exemption runs on a different axis and is self-limiting by construction:
a token is his if HE WROTE IT THIS TURN. It cannot be reached for by rephrasing
because it does not depend on my text at all, and it encodes the principle
rather than a proxy for it -- this gate exists to stop me speaking at him in a
register he did not ask for, and a word he supplied is already his register.

Sibling of tests/test_translate_first_gate.py, which holds the gate's own
contract and the corpus measurement behind its threshold.
"""

from __future__ import annotations

from divineos.core.lepos_translation_gate import DOCUMENT_MARK_LIMIT, check_translation_first

HIS_MESSAGE = (
    "btw are you able to check if claude code can be updated, they have the new "
    "fable 5.1 model i can switch you over to it but do some research on it first"
)

THE_REPLY_THAT_FIRED = (
    "Real, released today, and the important line is in Anthropic's own docs "
    "rather than the coverage. Fable 5.1 is their most capable generally "
    "available model, and their own advice is to start with Opus 5 for most "
    "work and reach for Fable 5.1 only for long-horizon agentic work. That "
    "happens to be exactly what we do."
)


def test_the_reply_that_fired_passes_when_the_gate_can_see_his_message():
    """The live instance. Naming the model he named is not distance from him."""
    assert check_translation_first(THE_REPLY_THAT_FIRED, HIS_MESSAGE) is None


def test_the_same_reply_still_fires_when_he_never_said_it():
    """Guard the guard. If the exemption held regardless of his message it would
    be a blanket permission for version-shaped numbers, rather than a rule about
    whose vocabulary is whose."""
    assert (
        check_translation_first(THE_REPLY_THAT_FIRED, "how did the branches go today") is not None
    )


def test_my_own_metrics_still_count_when_he_mentioned_one_number():
    """THE ABUSE CASE, and the one that would make this exemption a hole.

    He says one number; I bury him in my own. Every measurement of mine is still
    a mark, because the rule is about the specific tokens he used and not about
    the turn having been unlocked.
    """
    reply = (
        "The sweep took 79 files onto one branch and 81 onto another, the hooks "
        "cost 12 seconds each across 20 of them, and the suite ran 11493 tests "
        "in 48 seconds."
    )
    assert check_translation_first(reply, HIS_MESSAGE) is not None


def test_stripping_his_token_cannot_eat_a_longer_number_of_mine():
    """Word-boundaried on purpose. He said one small number; a measurement of
    mine that merely begins with those digits is still mine."""
    reply = "It went from 5147 to 5148 and then to 5149, then 5150 and 5151."
    assert check_translation_first(reply, "does 5 sound right to you") is not None


def test_the_default_leaves_every_existing_caller_unchanged():
    """The parameter defaults to empty so adding it could not silently move a
    verdict anywhere the caller was not updated. Absence of his text means no
    exemption, never a blanket one."""
    reply = "There were 4 branches, 3 gates, and 7 findings."
    assert check_translation_first(reply) is not None
    assert check_translation_first(reply, "") is not None


def test_a_clean_message_is_still_clean_either_way():
    reply = "It updated itself, and the model he asked about is real and came out today."
    assert check_translation_first(reply, HIS_MESSAGE) is None
    assert check_translation_first(reply) is None


def test_the_limit_did_not_move():
    """The instrument must not yield to the behaviour. This repair changes WHOSE
    words are counted, never how many are allowed."""
    assert DOCUMENT_MARK_LIMIT == 3
