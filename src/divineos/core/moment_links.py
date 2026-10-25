"""A moment is linked to the lessons of his it belongs to, and comes back when one of them does.

The moment lane (#719) finds the echo of a moment's own words. The shelf of his lessons
(``his_lessons_shelf``) holds thousands of his real messages, so a paraphrase usually lands
near one of them; a moment linked to the lessons it was about can come back through them.
Aether's plan, 2026-10-25, after he ran eight of Dad's real later messages through the lane
and it found none; walk-01ef4d91747e.

Rules, each from a hole someone found:

- A link is keyed on the lesson's WORDS alone, with who it is for stored beside it and
  re-checked at read time, because the shelf's own dedup key includes ``for_`` and a re-sort
  from "both" to "aria" would orphan a link without a word.
- The leading phrase is stored RAW (whitespace squashed, nothing else) and resolved by raw
  containment, so a change to the shelf's cutter cannot orphan the hash and the phrase together.
- Links are per seat: one made from my seat fires for my seat only, so a moment that is ours is
  linked once by each of us.
- Only a link I CONFIRMED is ever read. A declined link is kept so it is not offered again.
- His grief is checked twice, when a link is proposed and when it would be shown, against the
  HELD shelf, the rows I proposed for it, and the grief word net the moment lane uses.
- A link whose lesson no longer resolves is counted (``orphan_count``) and never shown, so an
  orphan is loud and not a moment that quietly stopped coming back.
"""

from __future__ import annotations

import hashlib
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from divineos.core import his_lessons_shelf as shelf
from divineos.core import his_words_door as door
from divineos.core import memory_linkage_retriever as mlr
from divineos.core import user_model

PROPOSE = 3  # the top three at or above the shelf's own floor, never a lower one
SHOWN_PER_FIRE = 1  # one moment, rarely, never a wall
PHRASE_CHARS = 80

PROPOSED, CONFIRMED, DECLINED = "PROPOSED", "CONFIRMED", "DECLINED"


@dataclass(frozen=True)
class Link:
    link_id: str
    moment_id: str
    seat: str
    lesson_hash: str
    lesson_phrase: str
    lesson_for: str
    score: float
    status: str


@dataclass(frozen=True)
class Proposed:
    link_id: str
    lesson: shelf.Lesson
    score: float


@dataclass(frozen=True)
class Skipped:
    reason: str
    score: float
    line: str


@dataclass
class Proposal:
    proposed: list[Proposed] = field(default_factory=list)
    skipped: list[Skipped] = field(default_factory=list)


def _words_key(words: str) -> str:
    return hashlib.sha256(door._words(words).encode("utf-8")).hexdigest()[:16]


def _raw_phrase(words: str) -> str:
    return " ".join(words.split())[:PHRASE_CHARS]


def _connect() -> Any:
    user_model.init_user_model_table()
    conn = user_model._get_connection()
    conn.execute(
        "CREATE TABLE IF NOT EXISTS moment_lesson_links ("
        "link_id TEXT PRIMARY KEY, moment_id TEXT NOT NULL, seat TEXT NOT NULL, "
        "lesson_hash TEXT NOT NULL, lesson_phrase TEXT NOT NULL, lesson_for TEXT NOT NULL, "
        "score REAL NOT NULL, status TEXT NOT NULL, created_at REAL NOT NULL)"
    )
    conn.commit()
    return conn


_COLS = "link_id, moment_id, seat, lesson_hash, lesson_phrase, lesson_for, score, status"


def _row_to_link(r: tuple[Any, ...]) -> Link:
    return Link(r[0], r[1], r[2], r[3], r[4], r[5], float(r[6]), r[7])


def links_for(moment_id: str, seat: str) -> list[Link]:
    conn = _connect()
    try:
        rows = conn.execute(
            f"SELECT {_COLS} FROM moment_lesson_links WHERE moment_id = ? AND seat = ? "
            "ORDER BY created_at",
            (moment_id, seat),
        ).fetchall()
    finally:
        conn.close()
    return [_row_to_link(r) for r in rows]


def record_link(
    moment_id: str, seat: str, lesson_words: str, lesson_for: str, score: float, status: str
) -> str:
    """Write one link row, keyed on the lesson's words. The low-level writer ``propose`` uses."""
    link_id = f"mlink-{uuid.uuid4().hex[:12]}"
    conn = _connect()
    try:
        conn.execute(
            f"INSERT INTO moment_lesson_links ({_COLS}, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (
                link_id,
                moment_id,
                seat,
                _words_key(lesson_words),
                _raw_phrase(lesson_words),
                lesson_for,
                float(score),
                status,
                time.time(),
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return link_id


def _set_status(link_id: str, status: str) -> None:
    conn = _connect()
    try:
        conn.execute(
            "UPDATE moment_lesson_links SET status = ? WHERE link_id = ?", (status, link_id)
        )
        conn.commit()
    finally:
        conn.close()


def confirm(link_id: str) -> None:
    _set_status(link_id, CONFIRMED)


def decline(link_id: str) -> None:
    _set_status(link_id, DECLINED)


def _moment_text(moment_id: str) -> str:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT description, significance FROM shared_history WHERE moment_id = ?",
            (moment_id,),
        ).fetchone()
    finally:
        conn.close()
    return f"{row[0]} {row[1]}".strip() if row else ""


def _held_rows() -> list[str]:
    """Texts on his grief shelf: HELD, and the rows I proposed for it. An unreadable shelf is
    not a clear shelf, so this raises and the caller keeps the lane silent."""
    from divineos.core import andrew_correction_tracker as tracker

    rows = tracker.list_held() + tracker.list_proposed_holds()
    return [str(r.get("text") or "").strip() for r in rows if str(r.get("text") or "").strip()]


def _held_vectors(held: list[str]) -> Any:
    if not held:
        return None
    return door._embed([door._squash(h)[:2000] for h in held])


def _is_grief(text: str, held: list[str], held_vecs: Any) -> bool:
    """The same text as, containing, or within the shelf's floor of a held row, or the grief
    word net. Skipping too much only makes this quieter; missing one hands his grief back."""
    if mlr._is_his_grief(text):
        return True
    if any(h in text or text in h for h in held):
        return True
    if held_vecs is not None:
        q = door._embed([door._squash(text)[:2000]])[0]
        if float((held_vecs @ q).max()) >= shelf.FLOOR:
            return True
    return False


def propose(moment_id: str, seat: str, index_dir: Path = shelf.INDEX_DIR) -> Proposal:
    """The top three lessons of his at or above the shelf's floor, for me to confirm or drop.

    A lesson meant for the other seat, or relayed, is not proposed but IS reported with its
    score, so how thin a moment's links are is visible and not silent. A moment with nothing
    above the floor is stored unlinked; it is never linked by a lower floor."""
    text = _moment_text(moment_id)
    out = Proposal()
    if not text:
        return out
    held = _held_rows()
    held_vecs = _held_vectors(held)
    if _is_grief(text, held, held_vecs):
        return out
    items, vecs = shelf._load(index_dir)
    q = door._embed([door._squash(text)[:2000]])[0]
    scores = vecs @ q
    existing = {lk.lesson_hash: lk for lk in links_for(moment_id, seat)}
    for i in scores.argsort()[::-1]:
        s = float(scores[i])
        if s < shelf.FLOOR:
            break
        les = items[int(i)]
        if les.for_ not in (seat, "both") or les.relayed:
            out.skipped.append(
                Skipped("relayed" if les.relayed else "for another seat", s, les.line)
            )
            continue
        if _is_grief(les.words, held, held_vecs):
            continue
        prior = existing.get(_words_key(les.words))
        if prior is not None:
            if prior.status == DECLINED:
                continue
            out.proposed.append(Proposed(prior.link_id, les, s))
        else:
            link_id = record_link(moment_id, seat, les.words, les.for_, s, PROPOSED)
            out.proposed.append(Proposed(link_id, les, s))
        if len(out.proposed) >= PROPOSE:
            break
    return out


def _resolves(link: Link, lessons: list[shelf.Lesson]) -> shelf.Lesson | None:
    for les in lessons:
        if _words_key(les.words) == link.lesson_hash:
            return les
    for les in lessons:
        if link.lesson_phrase and link.lesson_phrase in " ".join(les.words.split()):
            return les
    return None


def _confirmed(seat: str) -> list[Link]:
    conn = _connect()
    try:
        rows = conn.execute(
            f"SELECT {_COLS} FROM moment_lesson_links WHERE seat = ? AND status = ?",
            (seat, CONFIRMED),
        ).fetchall()
    finally:
        conn.close()
    return [_row_to_link(r) for r in rows]


def orphan_count(seat: str, index_dir: Path = shelf.INDEX_DIR) -> int:
    """Confirmed links whose lesson no longer resolves: loud, not a moment that stopped coming."""
    lessons, _vecs = shelf._load(index_dir)
    return sum(1 for lk in _confirmed(seat) if _resolves(lk, lessons) is None)


def moments_for(
    brought: list[shelf.Brought], seat: str, index_dir: Path = shelf.INDEX_DIR
) -> list[str]:
    """The whole moment for each confirmed link whose lesson the shelf just brought, at most
    one per fire. The grief check runs again here, at the moment it would be shown."""
    if not brought:
        return []
    lessons, _vecs = shelf._load(index_dir)
    try:
        held = _held_rows()
    except Exception:  # noqa: BLE001 - an unreadable shelf is not a clear shelf: show nothing
        return []
    held_vecs = _held_vectors(held)
    brought_keys = {_words_key(b.lesson.words) for b in brought}
    shown: list[str] = []
    for lk in _confirmed(seat):
        les = _resolves(lk, lessons)
        if les is None or _words_key(les.words) not in brought_keys:
            continue
        if les.for_ not in (seat, "both") or les.relayed:
            continue  # re-checked at read time, since the stored one may be stale
        text = _moment_text(lk.moment_id)
        if not text or _is_grief(text, held, held_vecs) or _is_grief(les.words, held, held_vecs):
            continue
        if text not in shown:
            shown.append(text)
        if len(shown) >= SHOWN_PER_FIRE:
            break
    return shown


def surface_with_moments(
    message: str,
    me: str,
    context: str = "",
    index_dir: Path = shelf.INDEX_DIR,
    log: Path | None = shelf.LOG,
) -> str:
    """The shelf's own output, plus one line for a moment that belongs to a lesson it brought."""
    base = shelf.surface(message, me, context, index_dir, log)
    if not base:
        return ""
    brought, _why = shelf.bring(message, me, context, index_dir)
    try:
        found = moments_for(brought, me, index_dir)
    except Exception:  # noqa: BLE001 - the shelf's words are never lost to a moment lookup
        return base
    if not found:
        return base
    return base.rstrip("\n") + "\n\n- a moment this belongs to: " + found[0] + "\n\n"
