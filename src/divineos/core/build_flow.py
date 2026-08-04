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


def check_council_station(branch: str, required: int, applied: int | None) -> StationResult:
    """Station 2 -- council walk, against the gravity-derived requirement."""
    if required == 0:
        return StationResult("2-council", Status.SATISFIED, "gravity 0: no walk required")
    if applied is None:
        return StationResult("2-council", Status.CANNOT_CHECK, "ledger not readable")
    if applied >= required:
        return StationResult("2-council", Status.SATISFIED, f"{applied}/{required} lenses")
    return StationResult("2-council", Status.MISSING, f"{applied}/{required} lenses walked")


def check_draft_station(is_draft: bool | None) -> StationResult:
    """Station 7 -- the PR opens as a draft, never as ready-for-review."""
    if is_draft is None:
        return StationResult("7-draft", Status.CANNOT_CHECK, "PR state unreadable")
    if is_draft:
        return StationResult("7-draft", Status.SATISFIED, "draft")
    return StationResult(
        "7-draft", Status.MISSING, "OPEN AS READY -- undo with: gh pr ready <n> --undo"
    )


def check_audit_station(pr_number: int, audit_refs: tuple[str, ...] | None) -> StationResult:
    """Station 8 -- Aletheia. Last, and never self-serviceable."""
    if audit_refs is None:
        return StationResult("8-audit", Status.CANNOT_CHECK, "audit store not readable")
    token = f"#{pr_number}"
    if any(token in r for r in audit_refs):
        return StationResult("8-audit", Status.SATISFIED, "audit round references this PR")
    return StationResult("8-audit", Status.MISSING, "no audit round references this PR")


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

    parts: list[str] = []
    for s in sorted(statuses, key=lambda x: x.number):
        stations = ",".join(
            f"{r.station}={r.status.value}" for r in sorted(s.stations, key=lambda r: r.station)
        )
        parts.append(f"{s.number}:{s.branch}:{stations}")
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:16]
