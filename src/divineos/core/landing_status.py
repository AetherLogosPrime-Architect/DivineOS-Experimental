"""Where each waiting fix stands toward the external auditor, from the real facts.

Dad, 2026-10-10: the pile is fixes that never land. The auditor is on a
different platform and her letters are carried by hand, so the state of a fix
cannot be read from memory. It is worked out from three facts that exist
without anyone typing them: which of my letters named the fix, which of her
letters confirmed it and at what head, and what the readiness board still
holds.

Two errors, unequal cost (council walk-4137c02c4be4, Taleb): a false READY
could lead a runner to merge something she never confirmed, a false NEVER TOLD
costs one extra ask. So confirms are read strictly and anything that cannot be
read reads as UNKNOWN, never READY.

Nothing here changes anything. It is a signal channel; ``stamp-ready`` stays the
judge that re-checks at merge time.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date

NEVER_TOLD = "NEVER TOLD"
NO_ANSWER = "NO ANSWER"
CHANGED = "CHANGED"
CONFIRMED = "CONFIRMED"
READY = "READY"
UNKNOWN = "UNKNOWN"

_HER_LETTER = "aletheia-to-aether-"
_MY_LETTER = "aether-to-aletheia-"
_CONFIRM = re.compile(r"CONFIRMS:\s*#(\d+)\s+at\s+([0-9a-fA-F]{7,40})")
_FILE_DATE = re.compile(r"-(\d{4})-(\d{2})-(\d{2})-")
_MIN_SHA = 7


@dataclass(frozen=True)
class Status:
    label: str
    detail: str
    next_step: str


def confirms_from_letters(letters: Mapping[str, str]) -> dict[int, list[str]]:
    """PR number -> the shas she confirmed, read only from her own letters."""
    found: dict[int, list[str]] = {}
    for name, text in letters.items():
        if not name.startswith(_HER_LETTER):
            continue
        for number, sha in _CONFIRM.findall(text):
            found.setdefault(int(number), []).append(sha.lower())
    return found


def told_dates_from_letters(
    letters: Mapping[str, str], branches: Mapping[int, str]
) -> dict[int, date]:
    """PR number -> the newest day one of my letters to her named it.

    A letter names a fix by its number or its branch. The number must not run
    into a longer one (#5961 is not #596).
    """
    told: dict[int, date] = {}
    for name, text in letters.items():
        if not name.startswith(_MY_LETTER):
            continue
        match = _FILE_DATE.search(name)
        if match is None:
            continue
        day = date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        for pr, branch in branches.items():
            named = re.search(rf"#{pr}(?!\d)", text) or (branch and branch in text)
            if named and (pr not in told or day > told[pr]):
                told[pr] = day
    return told


def _at_head(shas: Iterable[str], head_sha: str) -> bool:
    return bool(head_sha) and any(
        len(sha) >= _MIN_SHA and head_sha.lower().startswith(sha) for sha in shas
    )


def classify(
    *,
    pr: int,
    branch: str,
    head_sha: str,
    confirms: Mapping[int, list[str]],
    told_dates: Mapping[int, date],
    held_stations: Iterable[str],
    today: date,
) -> Status:
    """The one label for a fix, and the one next step.

    READY holds only when her confirm names the live head and the board holds
    nothing else. A head that cannot be read can never be READY.
    """
    held = tuple(held_stations)
    shas = confirms.get(pr, [])

    if not head_sha:
        return Status(
            UNKNOWN,
            "could not read this fix's current head",
            "look again; could not look is not a pass",
        )
    if _at_head(shas, head_sha):
        if held:
            return Status(
                CONFIRMED,
                f"she confirmed this head; still held by {', '.join(held)}",
                "clear what is held, then it is ready",
            )
        return Status(READY, "she confirmed this head; nothing else held", f"stamp-ready {pr}")
    if shas:
        return Status(
            CHANGED,
            f"she confirmed an older head, now {head_sha[:9]}",
            "send the new head for a fresh confirm",
        )
    if pr in told_dates:
        days = (today - told_dates[pr]).days
        unit = "day" if days == 1 else "days"
        return Status(
            NO_ANSWER,
            f"asked {told_dates[pr].isoformat()}, {days} {unit}, no confirm",
            "put it in the next confirm request and check the last letter reached her",
        )
    return Status(NEVER_TOLD, "no letter to her names it", "put it in the next confirm request")


def render_request(waiting: list[tuple[int, str, str]]) -> str:
    """A confirm request that asks one thing and nothing else.

    Dad, 2026-10-10: a confirms letter is just that, confirm or say what is
    wrong. A question inside the ask is what turns her confirm into an answer.
    """
    if not waiting:
        return ""
    lines = ["Aletheia — these fixes are waiting for your confirm or your hold.", ""]
    for pr, title, head_sha in waiting:
        lines.append(f"- #{pr} at {head_sha[:9]}: {title}")
    lines += [
        "",
        "One line each, please. If it is good: CONFIRMS: #N at <sha>",
        "If it needs holding: HOLD: #N at <sha>, then what is wrong and needs fixing.",
        "",
        "— Aether",
    ]
    return "\n".join(lines)
