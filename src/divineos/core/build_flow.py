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


def check_aria_station(branch: str, letters_dir: Path) -> StationResult:
    """Station 4 -- iterate with Aria. Satisfied only when SHE wrote back.

    A letter I sent proves I spoke, not that we iterated, and the station is
    about the second thing.
    """
    if not letters_dir.is_dir():
        return StationResult(
            "4-aria", Status.CANNOT_CHECK, f"letters dir not readable: {letters_dir}"
        )
    needle = branch.lower()
    for f in sorted(letters_dir.glob("aria-to-aether-*.md")):
        try:
            if needle in f.read_text(encoding="utf-8", errors="replace").lower():
                return StationResult("4-aria", Status.SATISFIED, f"she replied in {f.name}")
        except OSError:
            continue
    return StationResult("4-aria", Status.MISSING, "no reply from Aria naming this branch")


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
    if any(f"#{pr_number}" in r for r in audit_refs):
        return StationResult("8-audit", Status.SATISFIED, f"audit round names PR #{pr_number}")
    if branch and any(branch in r for r in audit_refs):
        return StationResult("8-audit", Status.SATISFIED, f"audit round names {branch}")
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
