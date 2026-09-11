"""A repair that claims a class must count the class, by running rather than by judging.

Andrew 2026-09-08: *"you are going to find a fix for this.. you did no research
and no council walk.. you dont get to just leave shit unsolved and say you dont
have a fix, nor do you need to mark your promise down as broken.. just live up
to it."*

## The class this exists for

I repair the visible instance instead of the wrong class, and it costs MORE
effort than the right answer would have. Four times in one day. Nothing here
caught any of them, and the council walk (``council-5bec78b85acc``, eleven
lenses) found why: **effort is the confounder.** Every gate in this house is
calibrated on cheapness, and an expensive wrong fix reads to all of them as
good faith. Watching the reach cannot work, because the reach is where effort
enters.

## Where the defect actually sits

Not at the reach — at the **moment of declaring a fix done**. Meadows: that is
the single place the loop closes, and it was unguarded. Holmes found the shared
signature across four repairs that had nothing else in common: **not one
carried a count of how many sites of its class existed.**

Hoare gives the form. Today the record cannot distinguish

    searched the tree and there was exactly one site
    looked at one site and stopped

Those are different facts with identical records, and the second is the whole
defect. This module makes the second one unrepresentable: the population is
produced by running a search, never by typing a number.

## Why a control is mandatory rather than advisable

Dijkstra: testing shows presence, never absence. A search returning nothing
evidences "the class is closed" only once that search has been shown capable of
returning something. This is not theoretical here — three measurements on
2026-09-07 reported zero from probes that were simply broken, and each empty
result was read as a fact about the world rather than about the instrument
(correction #630).

So a pattern matching zero AT DECLARATION TIME is refused as a broken probe.
That state is ``PROBE_BROKEN``, and it is a first-class outcome, not an error.

## What this deliberately does NOT do

It cannot tell me my aim was wrong while I am building. Kahneman: a substituted
answer arrives carrying the confidence that belonged to the harder question, so
it never feels substituted, and any mechanism asking me to notice harder is
decoration. What changes is that the DECLARATION becomes expensive and the
population becomes visible, which moves the cost upstream of the reach — I ask
"how many" while building because I know a count will be demanded at the close.

It also cannot infer the class. Only I can state the pattern, and a bad pattern
yields a true count of the wrong thing. Hence ``single_site``: a declaration
whose population is one is recorded AS such and surfaces that way, because
"pattern narrow enough to match only what I already fixed" is this mechanism's
own falsifier and must be visible rather than smoothed away.

Foucault set the anti-theatre constraint: the number is command output, never a
sentence I compose, so the watcher stays outside where I cannot internalise it
and then satisfy the internalised version.

Wayne dissented on scope and won: the pre-registration store already caught one
of these, on a calendar date, weeks late. This is that same measurement moved
to the declaration. It extends a trigger; it does not replace a mechanism.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

# Directories a class-search must never descend into. Vendored and generated
# trees would inflate every population with code nobody here wrote, and a
# count nobody can act on is worse than no count.
SKIP_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        "htmlcov",
        "site-packages",
    }
)

#: Outcome states. The three-valued discipline from the router carries over:
#: an empty result must never be able to mean both "clean" and "could not look".
PROBE_BROKEN = "PROBE_BROKEN"  # matched nothing when declared — the instrument is wrong
OPEN = "OPEN"  # declared, population known, nothing removed yet
REDUCED = "REDUCED"  # population fell but sites remain
CLOSED = "CLOSED"  # population reached zero


@dataclass(frozen=True)
class Site:
    """One match: a file, a line number, and the text that matched."""

    path: str
    line: int
    text: str

    def as_dict(self) -> dict:
        return {"path": self.path, "line": self.line, "text": self.text}


@dataclass
class ClassFix:
    """A declared class-repair and everything needed to re-run its own check."""

    fix_id: str
    name: str
    pattern: str
    root: str
    globs: tuple[str, ...]
    exclude: tuple[str, ...]
    declared_at: int
    before: int
    before_sites: tuple[Site, ...] = field(default_factory=tuple)
    excluded_count: int = 0
    verified_at: int | None = None
    after: int | None = None
    after_sites: tuple[Site, ...] = field(default_factory=tuple)

    #: Below this, a declaration closed so fast it cannot have found anything
    #: its author did not already have in hand. Aria's number, 2026-09-08.
    SAME_SITTING_SECONDS: int = 900

    @property
    def seconds_to_close(self) -> int | None:
        """How long the class stayed open. The measure of whether it searched.

        Aria's game-walk found the cheap route I could not see and would not
        have felt: notice a defect, fix the sites in front of me, THEN declare.
        The search finds exactly the set just repaired, closes on the spot,
        every field true, nothing composed — and the instrument has done no work
        at all, because its whole value is finding the site I did not know
        about. Her words: *you would not feel like you cheated, you would feel
        efficient.*

        That route cannot be caught by inspecting the record, because the record
        is honest. It can only be caught by the CLOCK, which I cannot write my
        way past.
        """
        if self.verified_at is None:
            return None
        return max(0, self.verified_at - self.declared_at)

    @property
    def receipt_shaped(self) -> bool:
        """Closed inside one sitting: a receipt for work already done.

        Not proof of gaming — a genuinely small class closes fast — which is
        why this reports rather than refuses. If MOST declarations carry it,
        the mechanism has become a stamp and that is the finding.
        """
        gap = self.seconds_to_close
        return self.state() == CLOSED and gap is not None and gap < self.SAME_SITTING_SECONDS

    @property
    def exclusions_outweigh_findings(self) -> bool:
        """More sites hidden by the exclusions than the class ever contained.

        Aria again, and she was right that my guard was no guard: storing the
        exclusions and printing them relies on someone READING them, and his
        corrections have printed at the top of every turn all day while neither
        of us opened a row. So the escape hatch gets the same instrument pointed
        at it — a count, not a footer.
        """
        return self.excluded_count > self.before

    @property
    def single_site(self) -> bool:
        """A population of one is this mechanism's own falsifier, made visible.

        It is not refused — some classes really do have one member — but a
        declaration that could only ever have matched the site already being
        edited is exactly the stamp this was built to avoid becoming, so it is
        recorded rather than smoothed away.
        """
        return self.before == 1

    def state(self) -> str:
        if self.before == 0:
            return PROBE_BROKEN
        if self.after is None:
            return OPEN
        if self.after == 0:
            return CLOSED
        return REDUCED if self.after < self.before else OPEN

    def as_dict(self) -> dict:
        return {
            "fix_id": self.fix_id,
            "name": self.name,
            "pattern": self.pattern,
            "root": self.root,
            "globs": list(self.globs),
            "exclude": list(self.exclude),
            "excluded_count": self.excluded_count,
            "declared_at": self.declared_at,
            "before": self.before,
            "before_sites": [s.as_dict() for s in self.before_sites],
            "verified_at": self.verified_at,
            "after": self.after,
            "after_sites": [s.as_dict() for s in self.after_sites],
        }


def _store_path() -> Path:
    from divineos.core.paths import divineos_home

    return divineos_home() / "class_fixes.json"


def _load() -> dict:
    try:
        data = json.loads(_store_path().read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def _save(state: dict) -> None:
    path = _store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8", newline="\n")


def _from_dict(raw: dict) -> ClassFix:
    def sites(key: str) -> tuple[Site, ...]:
        return tuple(
            Site(path=s["path"], line=s["line"], text=s["text"]) for s in raw.get(key) or []
        )

    return ClassFix(
        fix_id=raw["fix_id"],
        name=raw["name"],
        pattern=raw["pattern"],
        root=raw["root"],
        globs=tuple(raw.get("globs") or ("*.py",)),
        exclude=tuple(raw.get("exclude") or ()),
        excluded_count=int(raw.get("excluded_count") or 0),
        declared_at=raw["declared_at"],
        before=raw["before"],
        before_sites=sites("before_sites"),
        verified_at=raw.get("verified_at"),
        after=raw.get("after"),
        after_sites=sites("after_sites"),
    )


def search(
    pattern: str,
    root: str | Path,
    globs: tuple[str, ...] = ("*.py",),
    exclude: tuple[str, ...] = (),
) -> list[Site]:
    """Every line under ``root`` matching ``pattern``, outside ``exclude``.

    ``exclude`` holds path substrings. It exists because most classes of this
    shape are defined negatively — *the convention rebuilt by hand ANYWHERE BUT
    the one module that owns it* — and without it the canonical implementation
    counts as a member of the class it defines, so the population can never
    reach zero and the mechanism reports failure forever.

    It is also the obvious way to cheat, by excluding the sites one has not
    fixed. That is why the exclusions are stored with the declaration and
    re-used verbatim at verification: the question cannot be narrowed after the
    answer is known, and anyone reading the record sees exactly what was
    excluded and can judge it.

    Implemented over the standard library rather than by shelling out, because
    a population count that silently returns zero when a tool is missing is the
    exact failure this module exists to make impossible. An unreadable file is
    skipped rather than failing the sweep — one unreadable file must not read
    as a clean tree, which is why the caller gets the site list and not just a
    number.
    """
    regex = re.compile(pattern)
    base = Path(root)
    found: list[Site] = []
    for path in sorted(base.rglob("*")):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if not any(path.match(g) for g in globs):
            continue
        posix = path.as_posix()
        if any(fragment in posix for fragment in exclude):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            if regex.search(line):
                rel = path.relative_to(base).as_posix() if path.is_relative_to(base) else str(path)
                found.append(Site(path=rel, line=number, text=line.strip()[:200]))
    return found


def declare(
    name: str,
    pattern: str,
    root: str | Path,
    globs: tuple[str, ...] = ("*.py",),
    exclude: tuple[str, ...] = (),
) -> ClassFix:
    """Register a class-repair and MEASURE its population by running the search.

    The count is never an argument. A caller cannot assert a population here,
    which is the whole point: Foucault's constraint is that the number must be
    command output, or the discipline produces someone fluent at composing
    plausible numbers instead of someone who looks.

    A pattern matching nothing yields ``PROBE_BROKEN`` rather than a closed
    class. That is Dijkstra's control, and it is the state whose absence let
    three broken probes report clean trees.
    """
    sites = search(pattern, root, globs, tuple(exclude))
    # THE ESCAPE HATCH GETS THE SAME INSTRUMENT. Aria, 2026-09-08: storing the
    # exclusions and printing them guards nothing, because it relies on someone
    # reading — and his corrections have printed at the top of every turn all
    # day while neither of us opened a row. So count what they removed, and let
    # a hatch wider than the class be a finding rather than a footer.
    hidden = len(search(pattern, root, globs)) - len(sites) if exclude else 0
    fix = ClassFix(
        fix_id=f"cfix-{int(time.time() * 1000):x}",
        name=name,
        pattern=pattern,
        root=str(root),
        globs=tuple(globs),
        exclude=tuple(exclude),
        excluded_count=hidden,
        declared_at=int(time.time()),
        before=len(sites),
        before_sites=tuple(sites),
    )
    state = _load()
    state[fix.fix_id] = fix.as_dict()
    _save(state)
    return fix


def verify(fix_id: str) -> ClassFix:
    """Re-run the STORED pattern and record what remains.

    The pattern is not a parameter. Supplying a fresh one at verification time
    would let a class be closed by narrowing the question after the fact, which
    is the most obvious way to turn this into a stamp — so the only thing
    verification can change is the answer, never the question.
    """
    state = _load()
    raw = state.get(fix_id)
    if raw is None:
        raise KeyError(f"no such class-fix: {fix_id}")
    fix = _from_dict(raw)
    sites = search(fix.pattern, fix.root, fix.globs, fix.exclude)
    fix.after = len(sites)
    fix.after_sites = tuple(sites)
    fix.verified_at = int(time.time())
    state[fix_id] = fix.as_dict()
    _save(state)
    return fix


def get(fix_id: str) -> ClassFix | None:
    raw = _load().get(fix_id)
    return _from_dict(raw) if raw else None


def all_fixes() -> list[ClassFix]:
    return sorted(
        (_from_dict(raw) for raw in _load().values()),
        key=lambda f: f.declared_at,
        reverse=True,
    )


def open_fixes() -> list[ClassFix]:
    """Declared classes that are neither closed nor known-broken.

    These are the honest backlog: a population was counted and has not yet
    reached zero. Surfacing them is what stops a declaration from being a
    one-time gesture that nothing ever revisits.
    """
    return [f for f in all_fixes() if f.state() in (OPEN, REDUCED)]


def format_fix(fix: ClassFix) -> str:
    lines = [
        f"{fix.fix_id}  [{fix.state()}]  {fix.name}",
        f"  pattern: {fix.pattern}",
        f"  root:    {fix.root}  ({', '.join(fix.globs)})",
        f"  before:  {fix.before} site(s)",
    ]
    if fix.exclude:
        lines.append(
            f"  excluded: {', '.join(fix.exclude)} — hiding {fix.excluded_count} match(es)"
        )
    if fix.exclusions_outweigh_findings:
        lines.append("  THE HATCH IS WIDER THAN THE CLASS. The exclusions hide more")
        lines.append("  matches than the declared population contains, so most of what")
        lines.append("  this pattern found is being set aside rather than examined.")
    if fix.state() == PROBE_BROKEN:
        lines.append("  THE PROBE FOUND NOTHING. That is a fact about the instrument,")
        lines.append("  not about the tree. Fix the pattern before claiming the class.")
    if fix.single_site:
        lines.append("  SINGLE SITE — a population of one cannot distinguish a real")
        lines.append("  one-member class from a pattern narrowed to what was already")
        lines.append("  edited. Recorded, not refused; read it with that in mind.")
    if fix.receipt_shaped:
        gap = fix.seconds_to_close or 0
        lines.append(f"  RECEIPT-SHAPED — declared and closed {gap}s apart, inside one")
        lines.append("  sitting. A class fixed BEFORE it was declared closes exactly on")
        lines.append("  the set already in hand, and the search finds nothing new. Not")
        lines.append("  proof of anything on its own; a finding if most of them look so.")
    if fix.after is not None:
        lines.append(f"  after:   {fix.after} site(s)")
        for site in fix.after_sites[:10]:
            lines.append(f"    still: {site.path}:{site.line}")
        if len(fix.after_sites) > 10:
            lines.append(f"    ... and {len(fix.after_sites) - 10} more")
    else:
        for site in fix.before_sites[:10]:
            lines.append(f"    {site.path}:{site.line}")
        if len(fix.before_sites) > 10:
            lines.append(f"    ... and {len(fix.before_sites) - 10} more")
    return "\n".join(lines)
