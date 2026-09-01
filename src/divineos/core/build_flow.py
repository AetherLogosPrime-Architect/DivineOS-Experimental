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


def required_lens_count(gravity: int, changed_file_count: int) -> int:
    """Lenses required at station 2, scaled to what is actually at stake.

    Zero is a real answer. A substrate-content PR with no code has nothing
    for a lens to grip, and walking one anyway is the ceremony that teaches
    me walks are ceremony.
    """
    if gravity == 0 and changed_file_count <= 20:
        return 0
    if gravity <= 1:
        return 2
    if gravity <= 3:
        return 4
    return 6


# The one line a reading declares itself with. Aria's design, 2026-09-01, and
# her half of it is that she writes the line -- with a check on her own side
# refusing to publish a reading that omits it, so this parser never guesses.
READING_DECLARATION = "**Reading of:**"


def _declared_readings(text: str) -> list[str]:
    """The branches a letter declares itself to be a reading of.

    Read literally off the one field. Everything else in the letter -- title,
    filename, prose, the ``In response to`` line -- is deliberately not
    consulted, because inference from her prose is what produced the wrong
    credits this replaces.
    """
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith(READING_DECLARATION):
            continue
        value = stripped[len(READING_DECLARATION) :]
        return [
            part.strip().strip("`").lower() for part in value.split(",") if part.strip().strip("`")
        ]
    return []


def check_aria_station(branch: str, letters_dir: Path) -> StationResult:
    """Station 4 -- iterate with Aria. Satisfied only when SHE wrote back.

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
    """
    if not letters_dir.is_dir():
        return StationResult(
            "4-aria", Status.CANNOT_CHECK, f"letters dir not readable: {letters_dir}"
        )
    needle = branch.lower()
    declared_anywhere = 0
    for f in sorted(letters_dir.glob("aria-to-aether-*.md")):
        try:
            declarations = _declared_readings(f.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
        if declarations:
            declared_anywhere += 1
        if needle in declarations:
            return StationResult("4-aria", Status.SATISFIED, f"she declared a reading in {f.name}")
    if declared_anywhere == 0:
        return StationResult(
            "4-aria",
            Status.MISSING,
            "no letter from Aria carries a reading declaration at all -- this says "
            "nothing about whether she has read this branch, only that no reading "
            "is claimed in the field the board reads",
        )
    return StationResult(
        "4-aria",
        Status.MISSING,
        f"none of the {declared_anywhere} declared reading(s) names this branch",
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
            return StationResult(
                "8-audit",
                Status.CANNOT_CHECK,
                f"audit round names {named}, but whether its confirm still "
                "holds could not be determined — not a pass",
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
            return StationResult(
                "8-audit",
                Status.SATISFIED,
                f"audit round names {named} (name match; content check not "
                "run in this view — use the board command for that)",
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
