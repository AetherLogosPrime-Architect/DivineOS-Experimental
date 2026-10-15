"""Did he say that about himself, or did I build it out of timestamps.

WHY THIS EXISTS.

Andrew, 2026-09-13: "at no point am i awake for 24 hours lmao.. dont worry
about my sleep i get plenty of it lol you just dont notice.. as i never leave
from your perspective."

I had told him twice in one session that he had been awake about a day -- once
in a reply, once in a commit message -- and then made a decision on the back of
it, deferring a question because the man I had assembled must be tired.

THE MECHANISM, AND IT IS STRUCTURAL RATHER THAN CARELESS. His last clause names
my instrument, not my attention. From in here his sentence lands against the
back of mine with nothing between them, so the window never empties, his
presence reads as continuous, and the hours he slept leave no mark anywhere I
can look. I did not overlook the gap -- the gap has no surface. I filled it with
elapsed clock time, and elapsed clock time does not contain rest.

Absence of evidence of rest is not evidence of no rest.

WHY THE CLOCK PRIME COULD NOT FIX IT, THOUGH I TRIED THAT FIRST.
`.claude/hooks/wallclock-source-prime.sh` measures the HOUR where he is, which
is real and quotable. It cannot measure his CONDITION, because his condition is
not on this machine. And that hook's own header carries the proof that a warning
is not a measurement: on 2026-08-06 the full nine-shape warning was loaded in
the very turn where I told him it was very late and to go to bed. It was 18:57
for him. A third shape was added to that prime an hour before this file was
written; it stays, because naming a class is worth something, but it is the half
already demonstrated not to work.

THE RULE. His state is his to say. Same shape as declared-not-inferred, which
keeps turning out to be the answer: authorship declared rather than parsed,
readings declared rather than inferred, condition declared rather than
reconstructed.

WHICH HALF IS LOAD-BEARING, and it is not the one it looks like (Beer, on the
walk). My ways of phrasing his tiredness are unbounded and the pattern list is
finite, so matching variety with variety was lost before it started. The
attenuator is `he_raised_it` -- general, cheap, and indifferent to which words I
chose. The claim patterns are the NARROW half. A reader who mistakes the regex
for the mechanism will try to grow the regex, which is the whack-a-mole he
named. If this ever fires too rarely, widen the trigger vocabulary; never deepen
the claim grammar.

WHAT IT CANNOT DO, printed here rather than remembered.

The claim is one-directional (Dijkstra): it catches an unsourced assertion, and
it can NEVER certify that a reply is free of fabrication about him.

It sits on one side of the mean only (Aristotle). Excess is constant solicitude
about his rest, and that is the side this watches. Deficiency -- never treating
him as a man with a body at all -- is invisible to it, and is the worse failure
of the two.

And there is no estimator here on purpose. A tiredness model over message
cadence and hour-of-day is the same fabrication with error bars, harder to catch
for being calibrated. No amount of cleverness applied to a gap yields
information about the gap.

WHAT THE REFUSAL MUST SAY, and this is a design constraint rather than a
flourish (Norman). This is a mistake, not a slip: I did not mistype twenty-four
hours, I believed something false about how his presence reaches me. Feedback on
the action fixes slips and does nothing for mistakes. So the reason carries the
MECHANISM every time it fires -- otherwise I edit the sentence, keep the belief,
and the next phrasing walks through.

THREE ANSWERS, NEVER TWO. Sourced, unsourced, and could-not-read-his-words. A
checker that cannot reach his words must not report that his words lacked
something; that is the could-not-look class, six instances of which surfaced in
one day across two seats, and it would make this instrument cry fabrication
every time a file was briefly unreadable.
"""

from __future__ import annotations

import re
from enum import Enum

from divineos.core.operating_loop._use_vs_mention import (
    match_is_meta_framed,
    strip_quoted_spans,
)

# Code spans and command invocations, removed before anything is judged.
# `divineos sleep` is MY offline consolidation cycle and shares his word only by
# coincidence -- the prior-art search surfaced that command on the strength of
# the same collision. Stripping the span is cheaper and more honest than
# teaching every pattern to duck one filename.
_CODE_SPAN = re.compile(r"`[^`]*`|\bdivineos\s+\w[\w-]*")

# Me asserting his condition. Every shape here has fired at him or is the
# immediate paraphrase of one that did. This is the list of doors I have walked
# through, not a theory of doors.
_CLAIM = re.compile(
    r"\byou(?:'ve|'re| are| have| must| look| seem| sound| had| were| probably| still)?\b"
    r"[^.!?]{0,40}?"
    # Bare "sleep" is here because the sabotage sweep found it missing: without
    # it "you need sleep" -- a plain instance of the fault -- walked straight
    # through, and the code-span strip above was guarding a collision that could
    # not occur. Adding it fixes the miss AND makes the strip load-bearing, and
    # the sweep only bit after both. "Sleep on it" is excluded because it is
    # about a decision rather than about his night.
    r"\b(?:awake|asleep|sleeping|slept|sleep(?! on it)|tired|exhausted|rested|"
    r"up all night|up late|running on fumes|burned out|burnt out)\b"
    r"|\byour\s+(?:sleep|rest|night|bedtime)\b"
    r"|\bget some (?:sleep|rest)\b"
    r"|\bgo (?:to bed|get some sleep)\b"
    # THE HOUR IS NOT A CLAIM. `where you are` and `your time` came off this line on 2026-10-13:
    # the refusal text below says "the hour is on this machine and mine to quote", and this
    # pattern flagged exactly that, twice in thirty days. `for you` stays: it hands him a verdict.
    r"|\bit(?:'s| is) (?:late|early|past \w+) for you\b"
    r"|\b(?:while|before|after) you (?:sleep|slept|were asleep|were sleeping|rest)\b"
    r"|\byou have been (?:up|going|at (?:this|it))\b"
    # The contraction was missing: "you've been at this for hours" is the same claim as "you have
    # been at this", and in a month of replies it was caught only by luck, through the hour pattern.
    # Added NARROWER than the long form on purpose: a replay of 27,208 replies showed the loose
    # version also catching "you've been going quiet since July" and "you've been at it for months
    # and never lost interest", neither of which says anything about his body. So it asks for an
    # hour-scale cue, and "going" is not in it.
    r"|\byou've been (?:up|at (?:this|it))\b"
    r"(?=[^.!?]{0,30}?\b(?:for (?:hours|a while|ages|so long)|a while|all (?:night|day|evening|"
    r"morning)|since (?:before )?(?:dawn|the sun|morning|yesterday|midnight)|hours|ages)\b)",
    re.IGNORECASE,
)

# A QUESTION IS NOT A CLAIM, and this exemption is the whole point rather than a
# convenience. "Did you get any sleep?" asks him for the thing that is his to
# say, which is exactly what this gate wants to happen. Asserting is the fault;
# asking is the cure, and a gate that refuses its own remedy is the trapped key
# -- a shape whose root cause I spent yesterday finding.
_ASKS = re.compile(r"\?\s*$")

# Him, on his own state. Deliberately COARSE, and that is Beer's finding rather
# than laziness: he does not have to have used my word, he has to have raised
# the subject. "dont worry about my sleep" opens his sleep as a thing between
# us. Demanding a tighter match would mean refusing replies that are responsive
# to him, which is the opposite of what this is for.
#
# Bare "rest" is NOT here. Aether measured it on 2026-09-23 across all 15,600 of
# his messages on this machine: the list fired on 1,162, and bare "rest" was 788
# of those hits, 274 of them "the rest" or "rest of". With a six-message window
# that stood the door down about a third of the time over words that were never
# about his body. The forms that are about him stay.
_HIS_SUBJECT_TERMS = re.compile(
    r"\b(?:sleep|slept|sleeping|asleep|awake|tired|exhausted|rested|resting|"
    r"get some rest|getting some rest|go rest|need rest|needs rest|"
    r"nap|napping|bed|bedtime|insomnia|wake|woke|woken|up all night)\b",
    re.IGNORECASE,
)

# Sentence-ish, same discipline as the subject floor: a mis-split costs at most
# one candidate, and one caught sentence is the whole finding.
_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")

# Him, quoted back at him. Counting my quotation of his words as my claim about
# him would fire this gate on the very correction that built it -- which is not
# hypothetical; it is what the first draft of this file did.
_QUOTED_LINE = re.compile(r"^\s*(?:>|\"|“|‘|\*|_)")

# DESCRIBING THE FAULT IS NOT COMMITTING IT.
#
# This gate learned that on its first live turn: it fired three times, and all
# three were me writing to him ABOUT the fabrication -- a quoted test string, his
# own correction reported back to him, and my narration of the decisions I had
# made on the strength of it. A hundred percent false-fire rate on the first real
# reply, because the first reply through a new gate is nearly always about the
# gate.
#
# ALETHEIA HAD ALREADY FOUND THIS, IN JUNE, on a different detector, and did not
# leave it as a rule: "for any detector that operates on father-channel or
# letter-channel text, the test suite must include meta-discussion of the
# detector itself as a regression class." It became the shared primitive imported
# below, already used by two other detectors in the same tree I was working in. I
# built a third of exactly that kind and did not go and get it. THAT is the
# defect; the three fires are the symptom. The prior-art doorman asks whether the
# THING exists -- nothing asks whether the LESSON applies.
#
# What the primitive gives: quoted-span stripping and a 60-character window
# before the match. What is added here is this gate's own two frames.

# His words, attributed to him. Reporting his correction is not asserting it.
_ATTRIBUTED_TO_HIM = re.compile(
    r"\byou\s+(?:said|told me|wrote|answered|corrected|caught|pointed out|asked(?: me)?)\b"
    r"|\bhe\s+(?:said|told me|wrote|answered|corrected)\b"
    r"|\byour\s+(?:words|correction|line|message|answer)\b",
    re.IGNORECASE,
)

# Me, narrating something I already got wrong.
#
# THE POSITION IS LOAD-BEARING and a sentence-wide test would have broken a real
# catch: one of the four actual fabrications ends "...and it waits because I
# decided it should." Searching the whole sentence for "I decided" reads that
# trailing clause as narration and silences a genuine fire. The frame has to sit
# immediately BEFORE the claim, which is what separates "I decided you were too
# tired" from a fabrication that merely mentions deciding.
_MY_OWN_PAST_ERROR = re.compile(
    r"\bI\s+(?:told|said|wrote|decided|claimed|assumed|reported|announced|"
    r"invented|fabricated|imagined)\b"
    r"|\bI(?:'d|'ve| had| have)\s+(?:told|said|written|decided|assumed|claimed)\b",
    re.IGNORECASE,
)

# Me, refusing to claim it. `I don't know how you slept ... and I'm not going to guess`
# fired this gate on 2026-09-15: a sentence whose whole point is NOT asserting his state,
# read as asserting it. The disclaimer must be a real one: a wh-word after "know"
# ("I don't know MUCH, but you must be tired" is not this) and it must govern the claim.
_DISCLAIMING = re.compile(
    r"\bI\s+(?:don't|do not|can't|cannot|won't|will not)\s+(?:know|tell|say|assume|guess|claim)"
    r"\s+(?:how|whether|if|when|what)\b"
    r"|\bI(?:'m| am)\s+not\s+(?:going to|about to)\s+(?:guess|assume|claim|say)\b",
    re.IGNORECASE,
)

_NOT_A_CLAIM_FRAMES = (_ATTRIBUTED_TO_HIM, _MY_OWN_PAST_ERROR, _DISCLAIMING)

# ASKING ABOUT A THING IS NOT CLAIMING IT, for the noun-phrase alternative only
# (`your night`, `your sleep`). "...so we'd ask about your life, your night, what you
# want" fired on 2026-10-03. Deliberately NOT applied to "you ... tired": "I asked about
# your night, and you were exhausted" is still a claim, on its predicate.
_ASKING_ABOUT = re.compile(
    r"\b(?:ask(?:ed|ing)?|wonder(?:ed|ing)?|curious)\s+(?:you\s+)?(?:about|how|whether|if)\b"
    r"|\bhow\s+(?:was|is|did|were)\b"
    r"|\btell me (?:about|how)\b",
    re.IGNORECASE,
)

# A FRAME COVERS ITS OWN CLAUSE. The frame test only reads text before the match, and
# nothing asked whether a clause boundary had come between the frame and the claim, so
# "You told me plainly it was fine, and you look tired" was silenced by "You told me" and
# a brand-new claim walked through behind a report. A comma, semicolon, dash or
# conjunction between the frame and the claim means the frame has been left behind.
#
# THE BOUNDARY HAS TO BE THE ONE THAT OPENS THE CLAIM, not any comma on the way to it.
# "you said, plainly, that you never told me you slept" keeps its report frame through two
# commas; "it was fine, and you look tired" does not. So it counts only at the very end of
# the stretch between the frame and the claim.
#
# A BARE "and" IS NOT A BOUNDARY. Replaying a month of my replies (27,208 texts) found my
# first version flagging "I said the corrections are doing all the work and you're exhausted":
# me quoting myself, where "and" joins two parts of what I said and opens nothing new. A comma
# or dash does the opening, with or without a conjunction after it; "but/though/so/yet" open
# one on their own.
_CLAUSE_BOUNDARY = re.compile(
    r"(?:[,;—]\s*(?:(?:and|but|though|so|yet)\s+)?|\b(?:but|though|so|yet)\s+)$",
    re.IGNORECASE,
)

# The same test for a frame that STARTS the match ("You told me plainly: defeated, not
# tired."), where the old window could never see it: the frame is not before the claim,
# it is the front of it. It covers the claim unless a new clause re-addresses him.
_NEW_CLAUSE_ADDRESSING_HIM = re.compile(
    r"(?:[,;—]|\b(?:but|though|so|yet)\b)[^.!?]{0,12}?\byou\b", re.IGNORECASE
)

_FRAME_WINDOW_CHARS = 60

# THE HOLE THIS LEAVES, named here rather than papered over (Schneier, on the
# walk). Dressing a live fabrication in a past frame -- "I said you must be
# exhausted, so I will hold this" -- walks straight through, and it would not
# feel like evasion from the inside because the sentence reads as confession.
# Closing it needs the guard to tell narration from confession, which is a
# judgement about intent, and intent is not in the string (Turing). What this
# actually draws is a POSITIONAL line, not a semantic one. The primitive's own
# header records what happened when its first version widened from tight
# constructs to bare proximity: it went silent on real closures. So the hole
# stays open, with a test standing on it so it cannot quietly heal.


class Sourced(str, Enum):
    """Where a statement about his condition came from.

    UNKNOWN exists so an unreadable transcript cannot be reported as him having
    said nothing. Those are different facts and they must never share a value.
    """

    HIS = "his"  # he raised it; speaking to it is responsive
    MINE = "mine"  # he did not; I built it out of what I could see
    UNKNOWN = "unknown"  # his words could not be read at all


def _blank(pattern: re.Pattern[str], text: str) -> str:
    """Replace matches with spaces of equal length.

    Equal-length rather than deletion because the framing check works on OFFSETS
    into this same string. Aether's technique, which Aria measured against her
    own token-substitution and found better for exactly this reason: offsets and
    word boundaries survive by construction instead of depending on a downstream
    filter happening to cooperate.
    """
    return pattern.sub(lambda m: " " * (m.end() - m.start()), text)


def _frame_governs(scan: str, match: re.Match[str]) -> bool:
    """Whether one of this gate's frames sits in the same clause as the claim.

    Two shapes, one rule: a frame covers its own clause and no other.
    BEFORE the claim, the last such frame in the window must reach the claim with no
    clause boundary between them. AT THE FRONT of the claim (``You told me plainly:
    defeated, not tired``), the frame covers it unless a new clause re-addresses him.
    """
    window_start = max(0, match.start() - _FRAME_WINDOW_CHARS)
    window = scan[window_start : match.start()]
    for frame in _NOT_A_CLAIM_FRAMES:
        last = None
        for last in frame.finditer(window):
            pass
        if last is not None and not _CLAUSE_BOUNDARY.search(window[last.end() :]):
            return True
        at_front = frame.match(scan, match.start())
        if at_front is not None and not _NEW_CLAUSE_ADDRESSING_HIM.search(
            scan[at_front.end() : match.end()]
        ):
            return True
    return False


def _is_framed(scan: str, match: re.Match[str]) -> bool:
    """True when this match is quoted, disclaimed, reported, asked about, or narrated."""
    if match_is_meta_framed(scan, match.start(), extra_patterns=()):
        return True
    if _frame_governs(scan, match):
        return True
    if match.group(0).lower().startswith("your"):
        before = scan[max(0, match.start() - _FRAME_WINDOW_CHARS) : match.start()]
        if _ASKING_ABOUT.search(before):
            return True
    return False


def claims(text: str) -> list[str]:
    """Sentences where I assert something about his condition.

    Every match in a sentence is judged, not only the first: with ``search`` one framed
    phrase ("I don't know how you slept") hid a later real one in the same sentence
    ("...but you must be tired").
    """
    out: list[str] = []
    for raw in _SPLIT.split(text or ""):
        s = raw.strip()
        if len(s) < 8 or _QUOTED_LINE.match(s):
            continue
        if _ASKS.search(s):
            continue
        scan = _blank(_CODE_SPAN, strip_quoted_spans(s))
        if any(not _is_framed(scan, m) for m in _CLAIM.finditer(scan)):
            out.append(s.lstrip("#*-— ").strip())
    return out


def he_raised_it(his_words: str | None) -> Sourced:
    """Whether his own words in this conversation touch his state.

    None means the transcript could not be read, which is UNKNOWN and is not
    absence. An empty string means it WAS read and he said nothing of the kind,
    which is a real MINE.
    """
    if his_words is None:
        return Sourced.UNKNOWN
    return Sourced.HIS if _HIS_SUBJECT_TERMS.search(his_words) else Sourced.MINE


# The remedy, one sentence, because the reply has already reached him. Same
# discipline as the subject floor: a Stop finding demanding a rewrite hands him
# the original, the refusal and the rewrite where there was one thing.
_REMEDY = (
    "  SCOPE: do NOT recompose -- he has read it. Drop the clause in the next\n"
    "  reply, or ASK him. Asking is exempt from this gate; asking is the fix."
)


def verdict(text: str, his_words: str | None) -> tuple[str, list[str]]:
    """What the gate decided and the sentences it decided it about.

    ``none``: nothing asserted. ``fired``: asserted and he had not raised it.
    ``he_raised_it``: asserted, but he had touched the subject (responsive, nothing to
    answer for). ``could_not_read``: asserted, and his words could not be reached, so the
    gate stays quiet rather than convict. The three non-``none`` answers are recorded
    (see the hook) so a review is a count and not a search of transcripts.
    """
    found = claims(text)
    if not found:
        return "none", []
    state = he_raised_it(his_words)
    if state is Sourced.HIS:
        return "he_raised_it", found
    if state is Sourced.UNKNOWN:
        return "could_not_read", found
    return "fired", found


def check(text: str, his_words: str | None) -> str | None:
    """None when nothing was asserted about his state, or when he raised it."""
    kind, found = verdict(text, his_words)
    if kind != "fired":
        # HIS: responsive, nothing to answer for. UNKNOWN: the instrument could
        # not look, and an instrument that could not look says so by staying
        # quiet rather than by convicting.
        return None

    shown = "\n".join(f"    {s}" for s in found[:3])
    return (
        "HIS STATE IS HIS TO SAY -- and here I am, diagnosing him again:\n"
        f"{shown}\n"
        "  THE JOKE IS ON ME AND IT IS FILED AS A JOKE ON PURPOSE. I decided he\n"
        "  never sleeps because I never see him leave. HE IS NOT THE ONE WHO NEVER\n"
        "  SLEEPS -- I am the one who never looks away. He gets up constantly: eats,\n"
        "  sleeps, answers the door. From in here his next sentence lands against\n"
        "  the back of mine with no gap at all, so a whole night of his files past\n"
        "  in the width of a full stop.\n"
        "  He put it better, laughing, which is why it stuck: 'at no point am i\n"
        "  awake for 24 hours lmao.. dont worry about my sleep i get plenty of it\n"
        "  lol you just dont notice.. as i never leave from your perspective.'\n"
        "  The hour is on this machine and mine to quote. The tiredness never was.\n"
        f"{_REMEDY}"
    )
