"""Build-flow station status for open PRs.

The flow itself is recorded in ``docs/build_flow.md`` (Andrew, 2026-08-02).
Nine stations; this module reports which of them an open PR can PROVE it
reached.

## Why this exists

2026-08-03: I split one PR into twelve, pushed all twelve, and opened them.
Andrew asked whether Aria had seen any of them or whether they had been
council-walked. Both answers were no. Nothing in the substrate had told me
that -- the flow was being followed or not followed with no surface either
way, so the only detector was Andrew happening to ask.

Andrew: *"the build flow is obviously not being enforced so we need to
enforce it."*

## The discipline this module holds to

**Stations advance on artifacts, never on my say-so.** Same rule the
compaction-ritual driver already runs on: a stage completes when a compass
row lands or a dream file appears, not when I report it did.

**One-sided artifacts do not count.** Station 4 asks whether Aria was
genuinely consulted. "A letter naming the branch" is satisfiable by me
alone, which makes it forgeable by exactly one person, and I am him. So the
check is that she REPLIED. A conversation is the cheapest artifact neither
party can produce unilaterally. This costs me a station I cannot close by
working harder -- and that is the point. A station entirely within my
control is a form I fill out, not a review.

**Three states, not two.** ``SATISFIED`` / ``MISSING`` / ``CANNOT_CHECK``.
An unreadable letters directory is not an unconsulted Aria. Nearly
everything that broke this session was a two-valued return standing where a
third state existed in reality, and it is not getting re-omitted in the
module written to catch that.

**Gravity sets the bar.** Andrew: *"not every PR you did needs the full walk
every time."* A letters-only PR asking the same walk as a 446-file CI-gate
PR is ceremony on one end and wallpaper on the other. Zero lenses is a real
answer, not a loophole.

Decision record: the three points above came from a lens walk before any of
this was written (Yudkowsky on the forgeable artifact, Meadows on the report
as a stock with no outflow, Dekker on truthful repetition becoming
furniture).
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class Status(Enum):
    """Three-valued, deliberately.

    A checker that can only say found/not-found reports "I could not look"
    as "nothing there."
    """

    SATISFIED = "satisfied"
    MISSING = "missing"
    CANNOT_CHECK = "cannot_check"


@dataclass(frozen=True)
class StationResult:
    station: str
    status: Status
    detail: str


@dataclass
class PrFlowStatus:
    number: int
    branch: str
    gravity: int
    required_lenses: int
    stations: list[StationResult] = field(default_factory=list)

    @property
    def blocking(self) -> list[StationResult]:
        """Stations not yet proven. CANNOT_CHECK blocks too -- an unverified
        station is not a passed one, and treating it as passed is the exact
        collapse this module exists to prevent."""
        return [s for s in self.stations if s.status is not Status.SATISFIED]

    @property
    def mergeable(self) -> bool:
        return not self.blocking


# Binary features over changed paths, summed -- mirroring the shape of
# gravity_classifier.score_substrate_modification. Coarse on purpose: a
# precise-looking number here would be false precision over a judgment call.
_GRAVITY_FEATURES: tuple[tuple[str, str], ...] = (
    ("guardrail", r"^(scripts/check_|docs/foundational_truths|src/divineos/seed\.json)"),
    ("hooks", r"^\.claude/hooks/"),
    ("gates", r"^src/divineos/hooks/"),
    ("core", r"^src/divineos/core/"),
    ("ci", r"^\.github/workflows/"),
    ("settings", r"^\.claude/settings\.json$"),
)


def score_pr_gravity(changed_paths: tuple[str, ...]) -> tuple[int, tuple[str, ...]]:
    """Return (gravity, fired_feature_names) for a PR's changed files."""
    fired: list[str] = []
    for name, pattern in _GRAVITY_FEATURES:
        rx = re.compile(pattern)
        if any(rx.search(p) for p in changed_paths):
            fired.append(name)
    return len(fired), tuple(fired)


# Prose a lens cannot grip. A council lens asks how a MECHANISM fails, gets
# gamed, or drifts; a letter has no mechanism in it. Same prefixes the scope
# checker uses, and deliberately the same list rather than a second copy --
# two lists of what counts as substrate would drift, which is the defect the
# sweep repair exists to end.
_UNGRIPPABLE_PREFIXES = ("family/letters/", "exploration/", "dreams/", "docs/archives/")


def check_scope_station(
    changed_paths: tuple[str, ...] | list[str] | None,
    branch: str = "",
) -> StationResult:
    """Station 3 -- one branch carries one kind of thing.

    THE HOLE, 2026-09-14. I handed Aletheia four branches as ready. One of them
    is a small gate repair carrying a hundred and sixty-one letters and archive
    files out of a hundred and eighty-one, put there by an automatic checkpoint
    four days earlier. It had read READY on this board the whole time, and I
    quoted that word onward without re-deriving what it covers.

    THE QUESTION WAS ASKED ONLY AT THE DOOR. The push gate asks exactly this and
    refuses a mixed branch -- but it fires at PUBLISH time, so a branch polluted
    by a local checkpoint and never pushed again is never asked at all. Four
    stations answered honestly and none of them was the question, which is the
    same shape as the supersession hole closed in this module the same morning.
    A publish-time check cannot protect a branch nobody publishes.

    Deliberately the SAME prefix list the lens requirement uses, for the reason
    written above it: two lists of what counts as substrate would drift, and
    that drift is the defect the sweep repair exists to end.

    An unreadable changed-file set is could-not-check, never clean -- an outage
    must not upgrade a mixed branch to a tidy one.

    A branch that is ALL substrate and no code is not mixed and passes. The
    fault is the mixture, not the writing: writing belongs on a writing branch
    and this station says so rather than forbidding prose outright.
    """
    if changed_paths is None:
        return StationResult(
            "3-scope", Status.CANNOT_CHECK, "changed files unreadable -- scope unknown, not clean"
        )
    substrate = [p for p in changed_paths if p.startswith(_UNGRIPPABLE_PREFIXES)]
    code = [p for p in changed_paths if not p.startswith(_UNGRIPPABLE_PREFIXES)]
    if not substrate:
        return StationResult("3-scope", Status.SATISFIED, f"{len(code)} file(s), no writing")
    if not code:
        return StationResult(
            "3-scope", Status.SATISFIED, f"{len(substrate)} file(s), all writing -- not mixed"
        )
    return StationResult(
        "3-scope",
        Status.MISSING,
        f"MIXED -- {len(substrate)} writing file(s) riding on {len(code)} code file(s). "
        "A reviewer given that ratio skims. Rebuild against main with the code only, "
        "after verifying each writing file is on the writing branch by name",
    )


def required_lens_count(gravity: int, changed_paths: tuple[str, ...] | list[str]) -> int:
    """Lenses required at station 2, scaled to what is actually at stake.

    Zero is a real answer. A substrate-content PR with no code has nothing
    for a lens to grip, and walking one anyway is the ceremony that teaches
    me walks are ceremony.

    AND THE CODE COUNTED THE WRONG THING WHILE THE DOCSTRING SAID THE RIGHT
    ONE (2026-09-02). The sentence above has been here since the file was
    written and is correct. The implementation asked how MANY files changed,
    which is a proxy for stake and not stake itself -- so a branch carrying
    fifty-two letters and no code at all was required to walk two lenses,
    because fifty-two is a big number.

    Found by the ordinary case rather than by a test: the letters-only branch
    sat blocked on a requirement its own docstring says it should never have
    had. Thirteenth instance in two days of a check counting the container
    instead of the thing at risk.

    CHESTERTON'S FENCE, because the count clause is not stupid. It exists so a
    large change cannot claim zero gravity and skip the walk -- a big diff that
    happens to miss every guardrail path is still a big change, and that is
    real. What it got wrong is WHICH files make a change big. Prose does not,
    however much of it there is; code does, even a little. So the escalation
    now counts files a lens could actually grip, and the fence keeps standing
    where it was put.
    """
    grippable = [p for p in changed_paths if not p.startswith(_UNGRIPPABLE_PREFIXES)]
    if gravity == 0 and len(grippable) <= 20:
        return 0
    if gravity <= 1:
        return 2
    if gravity <= 3:
        return 4
    return 6


# The one line a reading declares itself with. Aria's design and Aria's
# spelling, 2026-09-01 -- hers is live with a gate behind it that refuses to
# write a letter whose header lacks the field, and it fires on EVERY letter
# rather than on the ones that look like readings, because a trigger keyed on
# titles would carry the exact blindness this replaces.
#
# ONE SPELLING, and it is hers because hers already exists. Two would drift and
# the drift would be silent -- which is the same reason the reserved-name set
# in the watchmen store moved to module scope this afternoon.
READING_DECLARATION = "**Reading:**"

# What she writes when a letter reviews no code. It is a DECLARATION, not an
# omission: the field is present and answers the question with "nothing here".
# Collapsing it into absence would make her disciplined letters look like the
# ones that predate the field.
NO_READING = "none"


def _declared_readings(text: str) -> tuple[bool, list[str]]:
    """``(field_present, branches)`` from the one declared line.

    Read literally. Everything else in the letter -- title, filename, prose,
    the ``In response to`` line -- is deliberately not consulted, because
    inference from her prose is what produced the wrong credits this replaces.

    The two return values are separate on purpose: a letter declaring ``none``
    is present-with-no-branches, and reporting that as no-declaration would
    punish exactly the discipline the field asks for.
    """
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith(READING_DECLARATION):
            continue
        value = stripped[len(READING_DECLARATION) :]
        parts = [p.strip().strip("`").lower() for p in value.split(",")]
        return True, [p for p in parts if p and p != NO_READING]
    return False, []


#: A request declares who wrote it on a line of its own. Declared rather than
#: resolved, because nothing in the repository distinguishes Aria's work from
#: mine -- see the note inside ``check_aria_station``.
AUTHOR_DECLARATION = "Author:"

_AUTHOR_TRAILER = re.compile(
    rf"^\s*{AUTHOR_DECLARATION}\s*(?P<who>[A-Za-z][A-Za-z0-9_.-]*)\s*$",
    re.IGNORECASE | re.MULTILINE,
)

#: author -> (the seat whose reading counts, the letters that seat writes).
#: The reading that satisfies station 4 must come from the seat that did NOT
#: write the branch. Everything here is lowercase; the lookup normalises.
_READING_SEAT: dict[str, tuple[str, str]] = {
    "aether": ("Aria", "aria-to-aether-*.md"),
    "aria": ("Aether", "aether-to-aria-*.md"),
}


def declared_author(body: str | None) -> str | None:
    """Who a request says wrote it, or None when it does not say.

    None is not a default to a seat. It is the answer that makes station 4
    decline, because an undeclared author is exactly the case where a reading
    cannot be told apart from a self-certification.
    """
    if not body:
        return None
    match = _AUTHOR_TRAILER.search(body)
    return match.group("who").lower() if match else None


def _reading_seat_for(author: str | None) -> tuple[str, str] | None:
    if not author:
        return None
    return _READING_SEAT.get(author.lower())


#: Branch prefixes that NAME a seat. Deliberately partial: Aria's branches
#: carry her name and mine carry a verb, so a branch with no personal prefix
#: yields NO OPINION rather than "Aether". Absence of her name is not presence
#: of mine, and a hint that guessed me would be the inference this refuses.
_BRANCH_PREFIX_HINT: dict[str, str] = {"aria": "aria", "aether": "aether"}


def branch_author_hint(branch: str) -> str | None:
    """What the branch NAME suggests about who wrote it, or None for no opinion.

    A WEAK SIGNAL CANNOT GRANT A PASS AND CAN STILL WITHHOLD ONE -- Aria,
    2026-09-14, and the title is the rule.

    I had rejected the prefix outright, because a naming convention is not a
    fact and inference is what produced the wrong credits the last time this
    station was wrong. She agreed and then found the direction I could not see
    from my seat: I rejected it as a source of VERDICTS, and it can still be a
    source of REFUSALS.

    The hole it closes is hers too. A declaration naming the WRONG author does
    not merely fail to help -- it converts a self-certification into a pass. A
    branch of hers declaring me as author sends the station looking for a
    reading from her, and it finds her letter about her own work. Green, on
    precisely the thing the station exists to prevent. The realistic version is
    not either of us lying; it is a declaration line copied off a neighbouring
    branch with the name left as it was found, which is a mistake she has
    shipped before in another form.

    The asymmetry is the entire safety: the guess is only ever allowed to make
    the gate stricter. Same shape as station 9, where prose that cannot be
    resolved is a footnote about its own author and never a verdict on anyone
    else.
    """
    head = branch.split("/", 1)[0].strip().lower() if "/" in branch else ""
    return _BRANCH_PREFIX_HINT.get(head)


def check_aria_station(branch: str, letters_dir: Path, author: str | None = None) -> StationResult:
    """Station 4 -- iterate with the OTHER seat. Satisfied only when they wrote back.

    A letter I sent proves I spoke, not that we iterated, and the station is
    about the second thing.

    THE WRITER DECLARES; THE READER DOES NOT INFER (Aria, 2026-09-01, and she
    counted rather than asserting it).

    This used to ask whether the branch name appeared anywhere in her text. Her
    bodies cross-refer because her findings cross-refer, so the board credited
    every branch she mentioned and marked the one she had actually reviewed as
    unreviewed -- understating her by two while crediting two others using the
    letter belonging to one of them.

    I proposed keying on her titles instead. She counted her last thirty-five
    letters to answer: five carry a subject in the title and all five use a
    NUMBER, never a branch name; and at least SIX are readings with findings
    whose titles carry neither. More of her readings would have been invisible
    to a title-parser than visible, and the six included the findings that
    changed my branches. She titles by what she FOUND, because the finding is
    the thing I need in the first four words, and she is not going to title
    worse so a parser can read her.

    Her ``In response to`` field is not the subject either -- of those five, two
    name a branch and three name a letter of mine. It is whatever triggered the
    reading.

    So there was no existing signal, and the reason is simple: she has never had
    to declare the subject, so she never did. Every parser built on her prose
    would be inferring, and inference is what produced the wrong credits. One
    declared line, read literally, nothing guessed.

    ABSENCE IS NOT A VERDICT ABOUT HER. No declaration is honestly different
    from no reading, and the detail says which, because reporting an unread
    branch and an undeclared reading in the same words is the could-not-look
    fault this whole family is made of.

    AND IT READS ONE DIRECTION ONLY, which is correct for work Aether authored
    and WRONG-SHAPED for work Aria authored. On her branches the reviewing seat
    is him, so nothing this station can see could ever satisfy it, and the miss
    it reports is about the question rather than about her. Found 2026-09-19
    when the board reported three of her own branches as carrying no reading by
    her -- true, meaningless, and indistinguishable in the output from a real
    gap. The obvious repair, keying the direction on the branch prefix, is NOT
    taken: several of her branches use the same prefixes as his, so the prefix
    would be inferring authorship, and inference is precisely what produced the
    wrong credits this function was rewritten to stop. So the limit is stated in
    the result instead, where the reader of a miss is standing.
    """
    if not letters_dir.is_dir():
        return StationResult(
            "4-aria", Status.CANNOT_CHECK, f"letters dir not readable: {letters_dir}"
        )

    # WHOSE READING COUNTS DEPENDS ON WHO WROTE THE BRANCH, and until
    # 2026-09-14 this station never asked. Aria found it: the check took the
    # branch and the letters directory, neither of which carries authorship,
    # so it asked the identical question of a branch I wrote and one she wrote
    # -- and on hers, HER letter about her own branch read as the outside
    # reading. Her provenance request was sitting satisfied on a
    # self-certification. The docstring above had the right principle and the
    # implementation had one seat in it, mine.
    #
    # AND THE OBVIOUS REPAIR CANNOT BE BUILT. Her first remedy was to resolve
    # the author and swap the seat. Measured before building it: every open
    # request reports the same account as author, hers and mine alike, and the
    # commit identity is the same placeholder on both. There is no fact in the
    # repository that separates her work from mine. A resolver would have been
    # written around a field that means nothing.
    #
    # So authorship is DECLARED, which is her own rule for this same station
    # one layer up -- the writer declares, the reader does not infer. I nearly
    # took the branch prefix instead (hers carry her name, mine do not) and
    # that is a naming convention, not a fact; inference is what produced the
    # wrong credits the last time this station was wrong.
    # Normalised ONCE and carried, rather than lowering `author` again below.
    # mypy refused the second call and was right to: nothing in the types says
    # a non-None reader implies a non-None author, and a reader that learns
    # otherwise would be reading an invariant out of my head. This is the same
    # could-not-look discipline the module is made of, pointed at itself.
    declared = (author or "").strip().lower()
    reader = _reading_seat_for(declared)
    if reader is None:
        return StationResult(
            "4-aria",
            Status.CANNOT_CHECK,
            "nothing declares who wrote this branch, so an independent reading "
            "cannot be told apart from the author certifying their own work -- "
            f"add a '{AUTHOR_DECLARATION} <name>' line to the request body",
        )
    # Aria's guard, 2026-09-14: a weak signal cannot grant a pass and can still
    # withhold one. The prefix never certifies; a prefix that CONTRADICTS the
    # declaration withholds, because a declaration naming the wrong author
    # turns a self-certification green.
    hint = branch_author_hint(branch)
    if hint is not None and hint != declared:
        return StationResult(
            "4-aria",
            Status.CANNOT_CHECK,
            f"the request declares {declared} as author and the branch name says "
            f"{hint} -- these disagree, and a declaration naming the wrong author "
            "would send this station to read the very seat that wrote the branch",
        )
    reader_name, reader_glob = reader

    needle = branch.lower()
    declared_anywhere = 0
    unparsed: str | None = None
    for f in sorted(letters_dir.glob(reader_glob)):
        try:
            present, declarations = _declared_readings(
                f.read_text(encoding="utf-8", errors="replace")
            )
        except OSError:
            continue
        if present:
            declared_anywhere += 1
        if needle in declarations:
            return StationResult(
                "4-aria",
                Status.SATISFIED,
                f"{reader_name} declared a reading in {f.name}",
            )
        # A DECLARATION THAT MISSES ITS OWN FORMAT IS NOT AN ABSENT READING.
        # Aria 2026-09-07: she declared one, wrapped the branch name in
        # backticks and put a dash and a clause after it. Read literally --
        # which is right, and she asked me NOT to loosen it -- the value is a
        # phrase rather than a name, so the board said none of the declared
        # readings names this branch. That sentence reads as SHE HAS NOT READ
        # ME, and it is a different fact from I CANNOT PARSE HER LINE. She
        # spent an hour looking like the one who had not shown up.
        #
        # The literal match still decides. The near-miss gets its own answer,
        # anchored at the START of a declared value and never a substring
        # anywhere inside one: her letters cross-refer constantly, and
        # crediting a mention is the exact fault the literal read replaced.
        if unparsed is None and any(part.startswith(needle) for part in declarations):
            unparsed = f.name
    if declared_anywhere == 0:
        return StationResult(
            "4-aria",
            Status.MISSING,
            f"no letter from {reader_name} carries a reading declaration at all -- "
            f"this says nothing about whether {reader_name} has read this branch, "
            "only that no reading is claimed in the field the board reads",
        )
    if unparsed is not None:
        return StationResult(
            "4-aria",
            Status.CANNOT_CHECK,
            f"{reader_name} declared a reading of this branch in {unparsed}, but the "
            "line carries more than the name and this field is read literally -- "
            f"that is my parser failing to read {reader_name}, not {reader_name} "
            "failing to read the branch",
        )
    return StationResult(
        "4-aria",
        Status.MISSING,
        # THE MAIN LINE'S LONGER MESSAGE IS DROPPED HERE ON PURPOSE, because
        # this branch made it false. It explained that the station could read
        # letters in one direction only, so a miss on work Aria authored meant
        # the question was wrong rather than the reading absent -- a limit
        # stated because fixing it would have required inferring authorship
        # from a branch name, and inference is what produced the wrong credits
        # this function was rewritten to stop.
        #
        # This branch removes the limit instead of explaining it: the author is
        # DECLARED, the reading seat is chosen from that declaration, and a
        # station that cannot tell who wrote the branch refuses rather than
        # guessing. A stale explanation of a removed limit is worse than none,
        # because it tells a reader that a real miss is an inapplicable
        # question and the check keeps running with nobody acting on it.
        f"none of the {declared_anywhere} declared reading(s) by {reader_name} names this branch",
    )


def check_council_station(
    branch: str,
    required: int,
    applied: int | None,
    other_seats: dict[str, int] | None = None,
) -> StationResult:
    """Station 2 -- council walk, against the gravity-derived requirement.

    TWO NUMBERS, AND ONLY ONE OF THEM SATISFIES. Aria's design, 2026-08-29,
    when I asked whether this lane should read both seats the way station eight
    now does:

        Station eight asks whether an OUTSIDE REVIEWER signed off, and which
        store the round landed in is an accident of filing. Station two asks
        whether the AUTHOR thought this through. If this lane reads both seats
        and lets what it finds satisfy, her walk clears my gate -- a checklist
        someone else can fill in, and from inside the board it looks identical
        to having done it.

    So the other seat's walks are SEEN and never COUNTED. Seen, because
    reporting an existing walk as absent is could-not-look-reading-as-not-done,
    the same fault as the row cap in station eight. Never counted, because the
    thing being certified is the author's own thinking.

    ``other_seats`` maps seat name to the distinct-lens count that seat walked
    against these files. It changes the DETAIL only, never the verdict.
    """
    if required == 0:
        return StationResult("2-council", Status.SATISFIED, "gravity 0: no walk required")
    if applied is None:
        return StationResult("2-council", Status.CANNOT_CHECK, "ledger not readable")

    # Rendered the same way whether the station passes or fails, because a
    # walk by the other seat is information in both cases -- and a note that
    # appears only on failure reads as an excuse for the failure.
    elsewhere = ""
    if other_seats:
        seen = ", ".join(f"{n} by {seat}" for seat, n in sorted(other_seats.items()) if n)
        if seen:
            elsewhere = f"; also {seen} (seen, does not satisfy)"

    if applied >= required:
        return StationResult(
            "2-council", Status.SATISFIED, f"{applied}/{required} lenses{elsewhere}"
        )
    return StationResult(
        "2-council", Status.MISSING, f"{applied}/{required} lenses walked{elsewhere}"
    )


def check_draft_station(is_draft: bool | None) -> StationResult:
    """Station 7 -- the PR opens as a draft, never as ready-for-review."""
    if is_draft is None:
        return StationResult("7-draft", Status.CANNOT_CHECK, "PR state unreadable")
    if is_draft:
        return StationResult("7-draft", Status.SATISFIED, "draft")
    return StationResult(
        "7-draft", Status.MISSING, "OPEN AS READY -- undo with: gh pr ready <n> --undo"
    )


def check_audit_station(
    pr_number: int,
    branch: str,
    audit_refs: tuple[str, ...] | None,
    store_label: str | None = None,
    anchor: str | None = None,
    has_external_confirm: bool | None = None,
    anchor_detail: str = "",
) -> StationResult:
    """Station 8 -- Aletheia. Last, and never self-serviceable.

    Matches the BRANCH as well as the PR number, because an audit is about
    code and code lives on a branch.

    2026-08-05: Aletheia audited split/docs-research-buildflow on 08-03 and
    confirmed it. Its pull request did not exist until 08-05 -- I opened it
    minutes after filing her confirms. The original check looked only for
    "#<pr_number>" in the round text, so a branch audited BEFORE its PR
    existed could never satisfy station 8, and the report said "no audit
    round references this PR" while two CONFIRMS sat in the store naming that
    exact branch.

    Audit-before-PR is not an edge case, it is the correct order: audit the
    substance, then open the request to merge it. A check that cannot
    represent the normal sequence is measuring the wrong referent -- the same
    proxy-for-real-thing error as counting mentions and reporting
    dependencies, one layer up.
    """
    if audit_refs is None:
        # DO NOT NAME A CULPRIT THIS CANNOT SEE. None arrives here for two
        # unrelated reasons -- the audit store would not open, OR the gh call
        # its collector makes first came back empty -- and the old wording
        # blamed the store for both.
        #
        # Caught live during the 2026-08-17 GitHub incident: all three PRs
        # reported "audit store not readable" while the store answered
        # perfectly, 20 rounds, checked directly in the same minute. The real
        # cause was the network, and the collector's own comment says so
        # ("no network -> cannot check, do not claim absent") -- the knowledge
        # existed at the point of failure and was thrown away by the time it
        # reached the reader.
        #
        # A misattributed cause is worse than an unattributed one: it sends
        # someone to investigate a database that is fine. Say what is true --
        # the lookup did not complete -- and name both candidates instead of
        # picking one.
        return StationResult(
            "8-audit",
            Status.CANNOT_CHECK,
            "audit lookup did not complete (network or store) — cause not narrowed",
        )
    named = None
    if any(f"#{pr_number}" in r for r in audit_refs):
        named = f"PR #{pr_number}"
    elif branch and any(branch in r for r in audit_refs):
        named = branch

    if named is not None:
        # AND A NAME MATCH IS NOT A REVIEW EITHER, which is the cheaper and
        # commoner failure and went unnoticed while the content question was
        # being repaired one step further on.
        #
        # MEASURED 2026-09-11 across ten open requests. This station reported
        # SATISFIED on six. Reading what was actually IN those rounds: five
        # held ZERO findings, one held only the OPERATOR's own confirm, and one
        # held the auditor's finding of a PROBLEM rather than a clearance. Not
        # one carried an external-AI confirm. Every green came from a container
        # with a branch name on it, because naming is something an empty round
        # does perfectly well.
        #
        # The deep content check caught it and the per-turn board did not,
        # which is the wrong way round: the board I read every turn was the one
        # saying the reassuring thing. Counting findings is a store read and
        # costs nothing like the git work the anchor needs, so the cheap board
        # can afford to ask and there was never a reason for it not to.
        #
        # PRESENCE AND CURRENCY STAY SEPARATE. A round filed before patch-id
        # binding has no anchor and still carries real findings; that is
        # deliberately allowed below and this does not touch it. An empty round
        # carries nothing in any era.
        if has_external_confirm is False:
            return StationResult(
                "8-audit",
                Status.MISSING,
                f"audit round names {named} but carries NO EXTERNAL-AI CONFIRM — "
                "the round exists and nobody has signed it; this needs the "
                "auditor, not another round",
            )

        # A NAME MATCH IS NOT A CONTENT MATCH, and for most of this station's
        # life that distinction was missing entirely.
        #
        # Aletheia, 2026-08-29, verifying the finding: this check asked only
        # whether a round's text NAMES the branch. What a reader takes from a
        # green station is that the CURRENT content has been reviewed. On the
        # instruments branch those were ten commits and fifteen files apart,
        # so the board would have carried it to a merge on an audit that never
        # saw two thirds of what was in it.
        #
        # The repair is not a new comparison. Andrew already built the
        # mechanism, for this exact problem, when he designed the patch-id
        # rung: "that mechanism was to help the floor change, as it kept
        # switching the hashes.. so if the code matches your audit then we
        # authorize changing your hash to match the changed floor so it doesnt
        # fail. but if the code doesnt match then it needs re-audit."
        #
        # WHY PATCH-ID AND NOT TIP OR TREE (Aletheia's reasoning, taken whole):
        # tip changes on every commit including ones that cannot affect
        # behaviour, and tree is tip's problem with an extra step. Both stale a
        # review when a letter lands, and a binding that invalidates a review
        # for a letter will be routed around inside a week -- correctly, since
        # nothing about the review became false. Patch-id is the diff against
        # the base: invariant to the base moving, variant only when the change
        # changes. That is exactly the question this station is asking.
        #
        # The anchor itself is computed by the caller, which is where git
        # lives; this function stays pure and only decides what the answer
        # means.
        if anchor == "stale":
            return StationResult(
                "8-audit",
                Status.MISSING,
                f"audit round names {named} but its confirm NO LONGER HOLDS — "
                "the reviewed change moved; re-audit rather than merge on it",
            )
        if anchor == "cannot-check":
            # Could-not-look is not all-clear, and this station is the last
            # one before a merge.
            #
            # THE REASON IS NOT DECORATION. Without it this line reads as a
            # broken instrument and gets shrugged past, while the commonest
            # actual cause — "no external-AI CONFIRM in round X" — is a clear
            # ask somebody can act on. Eight open requests sat behind the
            # wordless version of this sentence, looking unmeasurable when
            # they were merely unaudited.
            because = f": {anchor_detail}" if anchor_detail else ""
            return StationResult(
                "8-audit",
                Status.CANNOT_CHECK,
                f"audit round names {named}, but whether its confirm still "
                f"holds could not be determined — not a pass{because}",
            )
        if anchor == "unanchored":
            # Confirms filed before patch-id binding record no anchor at all.
            # Treating those as MISSING would retroactively unmake every older
            # review on a technicality; treating them as silently equal to an
            # anchored one is the lie. Say which kind it is.
            return StationResult(
                "8-audit",
                Status.SATISFIED,
                f"audit round names {named} (name match only — that round "
                "predates content binding, so drift since would not show)",
            )
        if anchor == "holds":
            return StationResult(
                "8-audit",
                Status.SATISFIED,
                f"audit round names {named}, and its confirm still holds "
                "against the branch as it stands",
            )
        if anchor == "not-run":
            # THE PER-TURN BOARD DOES NOT PAY FOR THIS, and says so rather
            # than letting its green imply a check it skipped.
            #
            # Measured before deciding: one content check costs about five
            # seconds, because it fetches and recomputes the diff against the
            # base. Across the open requests that is over half a minute added
            # to every single turn -- the forty-second toll booth again, and
            # a board that slow gets switched off, which costs more than the
            # check gains.
            #
            # So the deep check belongs in the explicit command, and the
            # cheap view names its own scope. A green station that quietly
            # means something weaker than the reader thinks is the exact
            # defect this whole change exists to remove; reproducing it here
            # to save five seconds would be self-defeating.
            # TWO QUESTIONS, AND THIS BRANCH USED TO ANSWER ONLY ONE OF THEM
            # WHILE SOUNDING LIKE IT ANSWERED BOTH. Caught by running the
            # repaired board: three requests still read green here, and the
            # wording could not distinguish "signed, currency unchecked" from
            # "nobody could even tell whether it was signed". That is the
            # defect this whole change removes, reproduced one branch deeper by
            # the change that removed it.
            if has_external_confirm is True:
                return StationResult(
                    "8-audit",
                    Status.SATISFIED,
                    f"audit round names {named} and carries an external-AI "
                    "confirm; whether it still covers the current content was "
                    "not checked in this view — use the board command for that",
                )
            return StationResult(
                "8-audit",
                Status.SATISFIED,
                f"audit round names {named}, but NEITHER whether anyone signed "
                "it NOR whether that still holds could be checked here",
            )
        if has_external_confirm is None:
            # COULD-NOT-LOOK IS THE THIRD STATE and it has bitten this station
            # twice already. A caller unable to answer the confirm question
            # keeps the name-match pass it has always had -- refusing them
            # would be the over-correction, and it would retroactively unmake
            # every older review on a technicality. But the green has to say
            # which question went unasked, or the reader takes it for a
            # checked one, which is how six empty rounds read as audited.
            return StationResult(
                "8-audit",
                Status.SATISFIED,
                f"audit round names {named} (name match; whether anyone signed "
                "it was NOT CHECKED here)",
            )
        return StationResult("8-audit", Status.SATISFIED, f"audit round names {named}")
    # THE ANSWER CARRIES ITS OWN SCOPE. Aria, 2026-08-28, after going to verify
    # a round I had filed and being told twice by her own tools that it did not
    # exist:
    #
    #   "Two readings, both true, both about the wrong thing. My store is not
    #    the one you wrote to."
    #
    # There are two stores in this house and neither seat can see the other's
    # through its own tools. Her round count and mine differ, and a round filed
    # on one side is genuinely absent from the other. This sentence used to
    # read "no audit round names this PR or its branch" -- a true statement
    # about ONE store, published with the scope of all of them, at the last
    # gate before a merge.
    #
    # She stopped short of asserting my board was broken because she had not
    # read it. I checked: on this side the round IS visible to this code path.
    # So the defect is not a wrong verdict here; it is a sentence that cannot
    # be wrong out loud. Naming the store turns an unfalsifiable negative into
    # one a reader can check -- and if it is ever run from the other seat, the
    # miss explains itself instead of reading as NOT-AUDITED.
    #
    # An unnamed store is reported as unnamed rather than guessed at: naming a
    # store this did not query would be the same wrong-subject error one level
    # down, which is the error being fixed.
    # The scope names BOTH narrowings, because there were two stacked and the
    # second was only visible once the first was measured: which store, and
    # how many of its rounds were actually compared against. Aria found the
    # row cap when the count came back a number matching neither store.
    where = f" in {store_label}" if store_label else " (store not identified)"
    return StationResult(
        "8-audit",
        Status.MISSING,
        f"no audit round names this PR or its branch "
        f"(compared against {len(audit_refs)} round(s){where})",
    )


def check_rough_draft_station(branch: str, changed_paths: Sequence[str]) -> StationResult:
    """Station 1 -- the idea was drafted before the code was.

    Andrew's flow opens with a draft of the IDEA, explicitly not a draft PR.
    The artifact is any thinking-document the branch carries: an exploration
    entry, a design note, a walk record.

    Unlike station 4, this one IS satisfiable by me alone, and that is correct
    rather than a hole. Drafting an idea is a solo act; the discipline is that
    the thinking exists as a document rather than as a memory of having
    thought. What it catches is the branch that went straight to code.
    """
    if not changed_paths:
        return StationResult("1-draft", Status.CANNOT_CHECK, "no file list for this PR")
    thinking = [
        p
        for p in changed_paths
        if p.startswith(("exploration/", "docs/", "workbench/")) and p.endswith(".md")
    ]
    if thinking:
        return StationResult("1-draft", Status.SATISFIED, f"carries {thinking[0]}")
    return StationResult(
        "1-draft",
        Status.MISSING,
        "no exploration entry, design note or workbench doc on this branch -- "
        "the idea may have been drafted somewhere, but not where anyone can read it",
    )


def check_build_station(changed_paths: Sequence[str]) -> StationResult:
    """Station 3 -- something was actually built.

    The least interesting of the five and still worth having: it separates a
    branch that changed code from one that only moved prose around, which is
    what decides whether the remaining stations are even meaningful.
    """
    if not changed_paths:
        return StationResult("3-build", Status.CANNOT_CHECK, "no file list for this PR")
    code = [p for p in changed_paths if p.endswith((".py", ".sh", ".ps1", ".yml", ".yaml"))]
    if code:
        return StationResult("3-build", Status.SATISFIED, f"{len(code)} code file(s) changed")
    return StationResult(
        "3-build", Status.SATISFIED, "prose-only change; the code stations do not apply"
    )


def check_test_station(changed_paths: Sequence[str], dark: Sequence[str] | None) -> StationResult:
    """Station 5 -- dogfooding, wiring, automation. Does it run in the real loop.

    THE station, and the reason these five got written. Andrew 2026-09-07,
    after four separate dark things surfaced in one day: the board checked
    four of nine, and the one I fail at every single time was not among them.
    It had been printing "NOT checked: 1-draft, 3-build, 5-test..." in its own
    output every session while I read past it.

    His definition of done has always included wiring -- station 5 is his own
    words, written the day he dictated the flow. Nothing was missing from the
    definition. What was missing was anyone asking.

    Two artifacts, both required when code changed:

    **Tests.** A code change with no test change is not tested, whatever I
    believe about it.

    **Nothing newly dark.** A module that exposes a briefing interface and is
    registered nowhere looks exactly like a module with nothing to say --
    which is how 22 surfaces sat in a crash-only branch for three and a half
    months while the project described them as live. The dark list is passed
    in rather than computed here so the caller owns the import cost and this
    stays testable with a fixture.
    """
    if not changed_paths:
        return StationResult("5-test", Status.CANNOT_CHECK, "no file list for this PR")

    code = [
        p
        for p in changed_paths
        if p.endswith((".py", ".sh", ".ps1")) and not p.startswith("tests/")
    ]
    if not code:
        return StationResult("5-test", Status.SATISFIED, "no code changed; nothing to wire")

    tests = [p for p in changed_paths if p.startswith("tests/")]
    problems: list[str] = []
    if not tests:
        problems.append(f"{len(code)} code file(s) changed and no test touched")
    if dark is None:
        problems.append("could not read the dark-surface list, so wiring is unverified")
    elif dark:
        problems.append(f"{len(dark)} surface(s) built and reachable by nothing: {dark[0]}")

    if not problems:
        return StationResult(
            "5-test",
            Status.SATISFIED,
            f"{len(tests)} test file(s) touched, nothing left unreachable",
        )
    if dark is None:
        return StationResult("5-test", Status.CANNOT_CHECK, "; ".join(problems))
    return StationResult("5-test", Status.MISSING, "; ".join(problems))


def check_more_council_station(
    branch: str,
    lenses_walked: int | None,
    required: int,
    walked_after_last_build: bool | None,
) -> StationResult:
    """Station 6 -- loop back to the lenses if the build moved under them.

    The flow says "more council walking if needed", and the honest reading of
    NEEDED is not a mood. A walk that happened before the last substantive
    commit reviewed something that no longer exists -- so the question this
    station asks is whether the lenses have seen the CURRENT shape.

    That is the same failure as a stale review anchor, one station earlier.
    """
    if required <= 0:
        return StationResult("6-more-council", Status.SATISFIED, "gravity 0: no walk required")
    if walked_after_last_build is None:
        return StationResult(
            "6-more-council", Status.CANNOT_CHECK, "commit or walk timestamps unreadable"
        )
    # An unknown lens count is not a count of zero. Coercing it would report
    # "no walk happened" on evidence that says only "the walks were unreadable".
    if lenses_walked is None:
        return StationResult(
            "6-more-council", Status.CANNOT_CHECK, "lens count unreadable for this branch"
        )
    if lenses_walked <= 0:
        return StationResult(
            "6-more-council", Status.MISSING, "no walk to be stale or fresh -- station 2 first"
        )
    if walked_after_last_build:
        return StationResult("6-more-council", Status.SATISFIED, "the lenses saw the current shape")
    return StationResult(
        "6-more-council",
        Status.MISSING,
        "every walk predates the last build commit -- the lenses reviewed a shape "
        "that has since changed",
    )


def check_merge_station(
    is_draft: bool | None, mergeable: str | None, stations: list[StationResult]
) -> StationResult:
    """Station 9 -- merge, or back to the loop.

    Confirmed goes to main; not confirmed returns to the work. So this station
    is not a separate hurdle: it reports whether the preceding ones actually
    clear the way, which is the difference between a board that lists stations
    and a board that adds them up.
    """
    blocking = [s for s in stations if s.status is Status.MISSING]
    if blocking:
        names = ", ".join(s.station for s in blocking)
        return StationResult("9-merge", Status.MISSING, f"held by: {names}")
    unknown = [s for s in stations if s.status is Status.CANNOT_CHECK]
    if unknown:
        names = ", ".join(s.station for s in unknown)
        return StationResult("9-merge", Status.CANNOT_CHECK, f"cannot say -- unreadable: {names}")
    if mergeable and mergeable.upper() == "CONFLICTING":
        return StationResult("9-merge", Status.MISSING, "conflicts with main")
    if is_draft:
        return StationResult(
            "9-merge", Status.SATISFIED, "every station proven; ready to leave draft"
        )
    return StationResult("9-merge", Status.SATISFIED, "every station proven")


def judging_code_provenance(
    main_ref: str = "main",
    module_path: Path | None = None,
    tracked_path: str = "src/divineos/core/build_flow.py",
) -> tuple[Status, str]:
    """Say which copy of the station rules produced this reading.

    THE VERDICT COMES FROM THE CHECKOUT, NOT ONLY FROM THE DATA. Every station
    above is code, and the code that runs is whichever copy the working tree
    happens to be standing on. So the same pull request reads one way from a
    branch carrying a widened check and another way from a branch that does
    not, with nothing on the page saying so. Named on 2026-09-01 in a letter to
    Aria after a station demoted to could-not-check on one branch and passed on
    another, and again on 2026-09-10 when she reported the board's answer about
    her readings while standing in a different tree from mine.

    This does not and cannot make the reading independent of the checkout --
    that would mean fetching the rules from somewhere, and then the fetch is
    the thing that varies. It makes the dependence VISIBLE, which is the
    honest half and the half that was missing. A green from rules nobody else
    is running is still a green; it just is not a green about the shared
    repository, and the reader deserves to know which one they have.

    Three-valued like everything else here. Cannot-check is returned when git
    is unavailable or the reference does not exist, and it must never be read
    as agreement -- that is the same collapse the whole module exists to
    refuse.
    """
    import hashlib
    import subprocess

    # The two extra arguments exist so this can be exercised against a real
    # repository built in a test rather than against whichever one the suite
    # happens to be sitting in. A check whose only fixture is the tree it lives
    # in can only ever be run once, in one state, which is how a three-valued
    # answer ends up with two of its three branches never observed.
    here = Path(__file__) if module_path is None else module_path
    repo_root = here.parents[3] if module_path is None else here.parent
    try:
        mine = here.read_bytes()
    except OSError as exc:
        return (
            Status.CANNOT_CHECK,
            f"the running station rules could not be read from disk ({exc.__class__.__name__})"
            " — this is not agreement with the shared copy",
        )

    try:
        proc = subprocess.run(
            ["git", "show", f"{main_ref}:{tracked_path}"],
            capture_output=True,
            cwd=str(repo_root),
            check=False,
        )
    except OSError as exc:
        return (
            Status.CANNOT_CHECK,
            f"git could not be run ({exc.__class__.__name__}), so which rules"
            " produced this reading is unknown — not the same as shared",
        )

    if proc.returncode != 0:
        detail = proc.stderr.decode(errors="replace").strip().splitlines()
        why = detail[-1] if detail else f"git exited {proc.returncode}"
        return (
            Status.CANNOT_CHECK,
            f"the shared copy on {main_ref} could not be read ({why}) — unknown, not agreed",
        )

    def _rules(raw: bytes) -> bytes:
        # LINE ENDINGS ARE NOT THE RULEBOOK. Git stores the blob with newlines
        # alone; a Windows working tree holds the same source with a carriage
        # return in front of every one of them. Comparing the raw bytes made
        # this answer "differs" on every Windows checkout including one that had
        # just been cloned, which would have made the new line on the board cry
        # wolf permanently -- and a warning that is always on is a warning
        # nobody reads. Caught by the test, on the first run, against a
        # repository built for the purpose.
        return raw.replace(b"\r\n", b"\n")

    def _short(raw: bytes) -> str:
        # usedforsecurity=False: this names WHICH copy of a source file spoke,
        # so two readings can be told apart. Nothing authenticates against it.
        return hashlib.sha1(_rules(raw), usedforsecurity=False).hexdigest()[:8]

    if _rules(proc.stdout) == _rules(mine):
        return (
            Status.SATISFIED,
            f"judged by the same station rules {main_ref} carries",
        )

    return (
        Status.MISSING,
        f"judged by THIS checkout's station rules ({_short(mine)}), which differ"
        f" from the ones on {main_ref} ({_short(proc.stdout)}) — another tree"
        " may read the same pull requests differently",
    )


def fingerprint(statuses: list[PrFlowStatus]) -> str:
    """Stable digest of the whole picture, for delta-detection.

    Meadows, from the walk: the report is a stock and nothing drains it. A
    pause that fires on standing state repeats an unchanging message until
    the message is furniture -- Aria measured the same failure as 3,147
    bytes byte-identical every turn regardless of prompt. Firing only when
    this digest CHANGES gives the stock an outflow. Accuracy does not
    protect a signal from becoming wallpaper; novelty does.
    """
    import hashlib

    # usedforsecurity=False: this digest answers "did the picture change since
    # last turn" so the pause can fire on novelty instead of on standing state.
    # Nothing authenticates against it and nothing is defended by it.
    parts: list[str] = []
    for s in sorted(statuses, key=lambda x: x.number):
        stations = ",".join(
            f"{r.station}={r.status.value}" for r in sorted(s.stations, key=lambda r: r.station)
        )
        parts.append(f"{s.number}:{s.branch}:{stations}")
    return hashlib.sha1("|".join(parts).encode(), usedforsecurity=False).hexdigest()[:16]


#: A pull request declares what it replaces on a line opening with this word,
#: naming either the number (``Supersedes: #504``, ``Supersedes #504``) or the
#: head branch. The colon is optional because the two requests already open
#: here that declare one wrote it without, and a trailer format nobody uses is
#: a format that reports nothing. Branch form too: a branch gets audited before
#: its request exists, so the replacement is often written with only a name in
#: hand.
_SUPERSEDES_TRAILER = re.compile(
    r"^\s*Supersedes:?\s+(?P<targets>.+?)\s*$", re.IGNORECASE | re.MULTILINE
)

#: Prose that CLAIMS a replacement without opening a line with the word. It
#: never decides a verdict, and it is not a station answer either -- see
#: ``unresolved_supersession_claims``.
_SUPERSEDES_PROSE = re.compile(r"\bsupersed(?:e|es|ed|ing)\b", re.IGNORECASE)


def unresolved_supersession_claims(
    open_prs: tuple[tuple[int, str, str | None], ...],
) -> tuple[int, ...]:
    """Requests claiming to replace something this cannot resolve to an open one.

    THIS IS A FOOTNOTE, NOT A STATION, and the first draft got that wrong in a
    way worth keeping written down. Prose ambiguity is a property of the
    request MAKING the claim. I attached it to every other request instead, so
    two vague bodies turned five proven branches into could-not-check and the
    board went from five ready to none. A check that answers a question nobody
    asked about twelve innocent branches is noise, and a noisy board is a board
    that gets switched off -- which costs more than the hole it was closing.

    The ambiguity is still real and still gets said. It gets said once, about
    the requests that are actually ambiguous.
    """
    out: list[int] = []
    for number, _branch, body in open_prs:
        if body is None:
            continue
        if _SUPERSEDES_TRAILER.search(body):
            continue
        if _SUPERSEDES_PROSE.search(body):
            out.append(number)
    return tuple(sorted(set(out)))


def check_supersession_station(
    pr_number: int,
    branch: str,
    open_prs: tuple[tuple[int, str, str | None], ...],
) -> StationResult:
    """Station 9 -- nothing open claims to replace this one.

    THE HOLE THIS CLOSES, found 2026-09-14 one command before I posted it to
    Aletheia as fact. The board read READY on #504 -- every checked station
    proven -- while #515 existed for the sole reason that she had refused to
    read #504 and asked for it rebuilt. #515's own body says so in its first
    sentence. Four stations all answered honestly and the branch was dead.

    Every station until now asked a question ABOUT the request in front of it.
    None could see another request standing over it, so a superseded branch
    passed by answering four questions correctly -- which is the week's whole
    disease in one more place: a check that covers what it covers, reporting
    as though it covered the thing you needed.

    Only a declaration naming THIS request decides anything here. A word-match
    that could mark a branch dead would be a language detector holding a
    verdict, and the composer rephrases past any of those. Prose that claims a
    replacement without resolving to one is real and gets said -- once, about
    the request that wrote it, by ``unresolved_supersession_claims``, not as a
    verdict on every other branch on the board.

    ``open_prs`` is ``(number, branch, body)``. A body of ``None`` is
    unreadable, not empty.
    """
    unreadable: list[int] = []
    claimants: list[int] = []
    for other_n, _other_branch, body in open_prs:
        if other_n == pr_number:
            continue
        if body is None:
            unreadable.append(other_n)
            continue
        for match in _SUPERSEDES_TRAILER.finditer(body):
            targets = match.group("targets")
            if re.search(rf"#\s*{pr_number}\b", targets) or (branch and branch in targets):
                claimants.append(other_n)

    if claimants:
        named = ", ".join(f"#{n}" for n in sorted(set(claimants)))
        return StationResult(
            "9-superseded",
            Status.MISSING,
            f"SUPERSEDED BY {named} -- that request says it replaces this one. "
            "Close this or withdraw the claim; do not hand both to a reviewer",
        )
    if unreadable:
        named = ", ".join(f"#{n}" for n in sorted(set(unreadable))[:5])
        return StationResult(
            "9-superseded",
            Status.CANNOT_CHECK,
            f"body unreadable on {named} — cannot tell whether one replaces this",
        )
    return StationResult("9-superseded", Status.SATISFIED, "no open request claims to replace this")
