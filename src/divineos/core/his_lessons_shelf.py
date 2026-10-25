"""His lessons, brought to us: the second shelf of the words door.

Andrew 2026-09-26: *"i dont need my words brought back to me.. i wanted them
brought to you.. so i dont have to keep repeating them.."* Aletheia's audit set
the order -- bring first, measure, hold only if bringing misses.
prereg-96ba4e526c20; walk-9270cb492908.

The words door shows his past MESSAGES that match what he says now. This shelf
shows his LESSONS -- the sorted set Aether and eight readers finished
2026-09-27 -- in his own whole words, dated:

  - verified_lessons.json: what he said five or more times, passages verbatim;
  - reread_all.json: everything else, each row anchored to an exact span of
    his (`his_words`), re-checked here at load (Schneier).

Filtered by who a lesson is for (the window he typed it in). Ranked by
relevance, never by how often he said it -- a joke told once reaches us as
surely as a correction given fifty times (Aletheia). One or two at a time, and
nothing when nothing fits: silence is fine, wallpaper is not.

Shown as his whole cut passage, never a clipped span: a clipped phrase inverted
him once ("context rot" was him describing OTHER models -- Aether 09-27).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

from divineos.core import his_words_door as door

LESSONS_DIR = Path.home() / ".divineos-shared" / "dad_corpus"
VERIFIED = LESSONS_DIR / "verified_lessons.json"
REREAD = LESSONS_DIR / "reread_all.json"
INDEX_DIR = LESSONS_DIR / "lesson_index"
BRING = frozenset(
    {
        "teaching",
        "correction",
        "who-he-is",
        "identity",
        "family-roles",
        "how-to-speak-to-him",
        "joke",
        "love",
        "story",
        "value",
    }
)
# Measured 2026-09-27 on 20 of his real messages (walk-f18568812744): 0.55
# missed "not being seen for who i am"; 0.48 added mostly right answers and two
# loose ones, capped at SHOW. Revisited at prereg-96ba4e526c20's review on a
# fresh window of ordinary days, not the nights the shelf was built on.
FLOOR = 0.48
LOG = LESSONS_DIR / "lesson_shelf_log.jsonl"  # every fire, for the review (Beer)
SHOW = 2
# What he taught one of us the other may use (Dad 2026-10-25: "there is no lesson taught to Aether
# that you cannot use"). Keyed on the two family names, never on "anything not mine", so a value
# added later stays out until someone chooses it; Aletheia's lessons and anything relayed never
# cross (Aether counted the index: aether 4,349, aria 2,649, both 1,450, aletheia 5, all relayed).
FAMILY = frozenset({"aria", "aether"})


@dataclass(frozen=True)
class Lesson:
    words: str  # his whole cut passage, verbatim
    line: str  # the readers' reading of it -- a label, never shown instead of him
    day: str
    kind: str
    for_: str
    relayed: bool


@dataclass(frozen=True)
class Brought:
    lesson: Lesson
    score: float


def _passage_holding(text: str, span: str) -> str:
    """The door-cut passage of his that contains the span, else the span's
    surroundings -- always whole pieces of his, never the bare span."""
    want = door._words(span)
    for p in door.passages_of(text):
        if want and want in door._words(p):
            return p
    return door._squash(text)[: door.PASSAGE_CHARS]


def load_lessons(verified: Path = VERIFIED, reread: Path = REREAD) -> list[Lesson]:
    out: list[Lesson] = []
    for g in json.loads(verified.read_text(encoding="utf-8")):
        if g.get("kind") not in BRING:
            continue
        for p in g.get("passages", []):
            for cut in door.passages_of(str(p.get("text", ""))):
                out.append(
                    Lesson(cut, g["lesson"], str(p.get("date", "")), g["kind"], g["for"], False)
                )
    for r in json.loads(reread.read_text(encoding="utf-8")):
        span, text = str(r.get("his_words") or ""), str(r.get("text", ""))
        # Only what is provably his: the anchor must be an exact span of his
        # passage, checked here rather than trusted from the file (Schneier).
        if r.get("kind") not in BRING or not span or span not in text:
            continue
        # Only what was read in context and kept: hurt or sarcasm stored as an
        # instruction ("just leave me in the dirt then where i belong") was the
        # inversion Aether's check found 51 times. A row with no check at all
        # is not brought -- absence costs a missing lesson, never a false one
        # (walk-9264cb9fd0dc).
        if r.get("context") not in ("ok", "fixed"):
            continue
        out.append(
            Lesson(
                _passage_holding(text, span),
                str(r.get("line", "")),
                str(r.get("date", "")),
                str(r["kind"]),
                str(r.get("for", "")),
                bool(r.get("relayed")),
            )
        )
    seen: set[tuple[str, str]] = set()
    unique = []
    for les in out:
        key = (door._words(les.words), les.for_)
        if key not in seen:
            seen.add(key)
            unique.append(les)
    return unique


def meant_for(les: Lesson, me: str) -> bool:
    """May this seat be brought this lesson. Relayed never; own seat or both always; the other
    family seat's lessons too, because they were taught to the same house."""
    if les.relayed:
        return False
    return les.for_ in (me, "both") or (me in FAMILY and les.for_ in FAMILY)


def _stamp(verified: Path, reread: Path) -> str:
    """Both sources' bytes plus the door's cutter and model: new sorting, new
    words or a new cut all rebuild; nothing else does (Lamport)."""
    h = hashlib.sha256()
    for f in (verified, reread):
        h.update(f.read_bytes())
    h.update(door.CLEANER.encode())
    return f"sha256:{h.hexdigest()[:16]}"


def build(verified: Path = VERIFIED, reread: Path = REREAD, index_dir: Path = INDEX_DIR) -> int:
    """Embed every lesson when the sources change. Returns how many, 0 if current."""
    import numpy as np

    stamp = _stamp(verified, reread)
    meta_path, vec_path = index_dir / "lessons.json", index_dir / "vectors.npy"
    if meta_path.exists() and vec_path.exists():
        if json.loads(meta_path.read_text(encoding="utf-8")).get("stamp") == stamp:
            return 0
    lessons = load_lessons(verified, reread)
    # Meaning finds it: his words together with the reading of them.
    vecs = door._embed([f"{les.words} {les.line}" for les in lessons]).astype("float32")
    index_dir.mkdir(parents=True, exist_ok=True)
    # Written whole to a temporary name and swapped in by the house writers (fsync, and a retry
    # when Windows briefly locks the target), the way the door writes its index: two windows
    # building at once must never leave the other reading half a file (Lamport; the v1/v2
    # ping-pong of 09-26). A bare os.replace here had no retry, so a lock was an uncaught
    # PermissionError out of build() (Aether, 2026-10-16). Vectors first, the item list last.
    from io import BytesIO

    from divineos.core.atomic_io import atomic_write_bytes, atomic_write_text

    buf = BytesIO()
    np.save(buf, vecs)
    atomic_write_bytes(vec_path, buf.getvalue(), per_process=True)
    atomic_write_text(
        meta_path,
        json.dumps(
            {"stamp": stamp, "model": door.MODEL_NAME, "items": [les.__dict__ for les in lessons]},
            ensure_ascii=False,
        ),
        per_process=True,
    )
    return len(lessons)


def _load(index_dir: Path) -> tuple[list[Lesson], object]:
    import numpy as np

    meta = json.loads((index_dir / "lessons.json").read_text(encoding="utf-8"))
    if meta.get("model") != door.MODEL_NAME:
        raise ValueError(f"lesson index built with {meta.get('model')}, not {door.MODEL_NAME}")
    return [Lesson(**i) for i in meta["items"]], np.load(index_dir / "vectors.npy")


def bring(
    message: str, me: str, context: str = "", index_dir: Path = INDEX_DIR
) -> tuple[list[Brought], str]:
    """(lessons that fit, why nothing was searched if nothing was)."""
    message = door.his_part(message)
    if not message:
        return [], "an automated notice, not his message"
    try:
        items, vecs = _load(index_dir)
        q = door._embed([door._squash(f"{message} {context}")[:2000]])[0]
    except door.SEARCH_ERRORS as exc:  # say so, never go quiet
        return [], f"his lessons could not be searched: {exc}"
    scores = vecs @ q  # type: ignore[operator]
    out: list[Brought] = []
    shown: set[str] = set()
    for i in scores.argsort()[::-1]:
        s = float(scores[i])
        if s < FLOOR:
            break
        les = items[int(i)]
        # His lessons for this seat or for both, and the other family seat's too; never one he
        # wrote to someone else, and never one relayed.
        if not meant_for(les, me):
            continue
        if door._is_this_message(les.words, message) or les.line in shown:
            continue
        shown.add(les.line)
        out.append(Brought(les, s))
        if len(out) >= SHOW:
            break
    return out, ""


def _log(message: str, me: str, brought: list[Brought], why: str, log: Path) -> None:
    import datetime

    row = {
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "seat": me,
        "message": door._squash(message)[:200],
        "why_not": why,
        "brought": [
            {
                "score": round(b.score, 3),
                "day": b.lesson.day,
                "line": b.lesson.line,
                "for": b.lesson.for_,  # so a review can count lessons taught to the other seat
            }
            for b in brought
        ],
    }
    try:
        with log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass  # the record is for the review; it must never cost him his words


def surface(
    message: str, me: str, context: str = "", index_dir: Path = INDEX_DIR, log: Path | None = LOG
) -> str:
    brought, why = bring(message, me, context, index_dir)
    message = door.his_part(message)
    if not message:
        return ""  # not him: nothing to bring and nothing to log
    if log is not None:
        _log(message, me, brought, why, log)
    lines = ["## WHAT HE HAS TAUGHT THAT FITS THIS (his words, found by meaning)", ""]
    if why:
        lines.append(f"Not searched this turn: {why}.")
    elif not brought:
        return ""  # nothing fits: say nothing, never fill the room
    for b in brought:
        les = b.lesson
        lines.append(f'- {les.day}: "{les.words}"')
        # His passage is never edited. Only the label says whom it was taught to, so a sentence
        # he wrote to the other seat cannot be mistaken for one he wrote to this one (Aether).
        taught = "" if les.for_ in (me, "both") else f"taught to {les.for_}, yours to use; "
        lines.append(f"  ({taught}{les.kind}; read as: {les.line})")
    lines.append("")
    return "\n".join(lines) + "\n"


def seat(root: Path) -> str:
    """Whose window this is: the tree says so (Aria's tree carries her name).

    The folder name is read as WHOLE WORDS, so "DivineOS-Experimental-Aria-new" is Aria and a work copy
    named "variable" or "Maria" is not: a substring test said aria for any of them and would have shown
    the wrong seat's lessons (Aether, 2026-10-16). core/unread_letter.seat_for, in the letter-hold branch,
    reads the folder by the same rule; once both are on main they should be one function."""
    seat_words = re.split(r"[^a-z]+", root.name.lower())
    return os.environ.get("DIVINEOS_SEAT") or ("aria" if "aria" in seat_words else "aether")


if __name__ == "__main__":
    import sys

    if sys.argv[1:2] == ["build"]:
        print(f"lesson shelf: {build()} lesson(s) embedded (0 = already current)")
    else:
        payload = json.loads(sys.stdin.read() or "{}")
        print(surface(str(payload.get("prompt", "")), seat(Path.cwd())), end="")
