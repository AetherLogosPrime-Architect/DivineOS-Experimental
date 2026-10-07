"""Letters matched by passage, not by their opening.

Dad, 2026-10-06: letters belong in the memory "if they are relevant, as long as
they dont drown out my words". And earlier (23 July, 20 August): link "a phrase
or two from it with a pointer to the full letter", not the whole thing.

Why this exists. The memory link used to give each letter ONE vector, made from
its opening window, so a long letter matched whatever its start shared with his
words and the useful part, in the middle, was never looked at. Rated blind by two
people over 30 of his real messages, one letter in thirty helped. I read that as a
property of letters and ranked them last, which buried even a letter he quotes on
purpose (40 real letters asked for by a quoted sentence: 15 came back with no
penalty, 1 with it). The cause was the window, so the repair is here: a letter is
cut into passages, each passage has its own vector, and a query finds the best
passage.

How it stays inside the per-turn budget. The hook is a fresh process every turn.
Loading 26,000 passages as per-item objects and looping over them would cost
seconds, so the vectors live in one matrix file, opened memory-mapped and searched
in a single multiply. The passage text and the pointer are in a small database
beside it, and only the winning rows are read. The drawer remains the one place a
vector is computed and kept; the matrix is a cache built from it and can be thrown
away and rebuilt.

Failure is loud. A missing, mismatched or unreadable index is reported as a stated
problem, never as "no letter matched", because those two read the same to Dad and
mean opposite things.
"""

from __future__ import annotations

import os
import re
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

MIN_WORDS = 25
MAX_WORDS = 150
# A paragraph of MIN_WORDS or more stands alone: he asked for "phrases or
# paragraphs", and merging two 40-word paragraphs into one passage blurs exactly
# the precision this exists for. Only shorter ones accumulate, until they reach it.
_MERGE_TO = MIN_WORDS

_FOOTER = re.compile(r"\n+[ \t]*(?:[—-]\s*)?the thread so far\s*[—-].*\Z", re.S | re.I)
_SIGN_OFF = re.compile(r"\n+[ \t]*—[ \t]*\n[ \t]*\w+[ \t]*\n[ \t]*\([^)\n]*\)[ \t]*\Z", re.S)
_FRONT_MATTER = re.compile(r"\A---\n.*?\n---\n", re.S)
_HEADER_FIELDS = (
    "**Written",
    "**In response",
    "**Close",
    "**Reading",
    "**Register",
    "**Delivery",
    "**Form",
)
_RULE = re.compile(r"[-—*_ ]+")


_TRAILING_RULES = re.compile(r"(?:\n[ \t]*[-—*_]{3,}[ \t]*)+\Z")


def _clean(text: str) -> str:
    """Front matter, the footer, the rule lines left before it, and the sign-off.
    Real letters end '— / Aria / (date) / --- / — the thread so far —', so removing
    the footer leaves a rule line between the sign-off and the end; a sign-off
    pattern anchored at the end missed it until a test used the real shape."""
    text = text.replace("\r\n", "\n")
    text = _FRONT_MATTER.sub("", text)
    text = _FOOTER.sub("", text).rstrip()
    text = _TRAILING_RULES.sub("", text).rstrip()
    return _SIGN_OFF.sub("", text).rstrip()


def _words(block: str) -> int:
    return len(block.split())


def _hard_split(piece: str) -> list[str]:
    """A piece that is still over MAX_WORDS (a table, a code block, a run with no
    sentence ends) cut by word count. Measured on the real letters: without this,
    583 passages ran past 150 words and the longest was 5,824."""
    words = piece.split()
    if len(words) <= MAX_WORDS:
        return [piece]
    step = int(MAX_WORDS * 0.7)
    return [" ".join(words[i : i + step]) for i in range(0, len(words), step)]


def _sentence_windows(block: str) -> list[str]:
    """A block over MAX_WORDS, cut at sentence ends into windows of about 0.7 of it."""
    windows: list[str] = []
    current: list[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+", block):
        current.append(sentence)
        if _words(" ".join(current)) >= int(MAX_WORDS * 0.7):
            windows.append(" ".join(current))
            current = []
    tail = " ".join(current)
    if tail:
        if windows and _words(tail) < MIN_WORDS:
            windows[-1] = f"{windows[-1]} {tail}"
        else:
            windows.append(tail)
    return [part for window in windows for part in _hard_split(window)]


def split_passages(text: str) -> list[str]:
    """The passages of one letter, boilerplate dropped.

    The footer and sign-off are the same in every letter since early September, so
    as passages they would match many messages and say nothing. A paragraph under
    MIN_WORDS joins the next until about 60 words; one over MAX_WORDS is cut at
    sentence ends. A letter that yields none keeps its first MAX_WORDS words as one
    passage, so a short letter is still findable.
    """
    text = _clean(text)
    passages: list[str] = []
    pending: list[str] = []

    def emit() -> None:
        merged = " ".join(" ".join(pending).split())
        pending.clear()
        if _words(merged) >= MIN_WORDS:
            passages.append(merged)

    for raw in re.split(r"\n\s*\n", text):
        block = raw.strip()
        if not block or block.startswith(_HEADER_FIELDS) or _RULE.fullmatch(block):
            continue
        if block.startswith("#"):
            block = block.lstrip("# ").strip()
        if _words(block) > MAX_WORDS:
            emit()
            for window in _sentence_windows(block):
                pending.append(window)
                emit()
            continue
        if pending and _words(" ".join(pending)) + _words(block) > MAX_WORDS:
            emit()
        pending.append(block)
        if _words(" ".join(pending)) >= _MERGE_TO:
            emit()
    emit()
    if not passages:
        words = text.split()
        if len(words) >= 5:
            passages.append(" ".join(words[:MAX_WORDS]))
    return passages


@dataclass(frozen=True)
class LetterFile:
    name: str
    path: Path
    rel_path: str
    title: str
    mtime: float


def letter_files(roots: list[Path] | None = None) -> list[LetterFile]:
    """Every letter once: by resolved path and by name, since the same letter sits in
    every checkout on this machine. The first root read is the running checkout."""
    if roots is None:
        from divineos.core.memory_linkage_retriever import _find_letters_roots

        roots = _find_letters_roots()
    seen_paths: set[Path] = set()
    seen_names: set[str] = set()
    found: list[LetterFile] = []
    for root in roots:
        for md_path in sorted(root.rglob("*.md")):
            resolved = md_path.resolve()
            if resolved in seen_paths or md_path.name in seen_names:
                continue
            seen_paths.add(resolved)
            seen_names.add(md_path.name)
            try:
                mtime = md_path.stat().st_mtime
            except OSError:
                mtime = 0.0
            stem = md_path.stem
            title = stem.lstrip("0123456789_-").replace("_", " ").replace("-", " ").strip() or stem
            title = title[:60] + ("..." if len(title) > 60 else "")
            try:
                rel = str(md_path.relative_to(root.parent.parent))
            except ValueError:
                rel = str(md_path)
            found.append(LetterFile(stem, md_path, rel, title, mtime))
    return found


# ------------------------------------------------------------------ the index files


def _dir() -> Path:
    from divineos.core import vector_drawer

    return vector_drawer.drawer_path().parent


def matrix_path() -> Path:
    return _dir() / "letter_passages.npy"


def db_path() -> Path:
    return _dir() / "letter_passages.db"


def build(progress: Any = None, roots: list[Path] | None = None) -> dict[str, int]:
    """Cut every letter into passages, make sure each has a vector in the drawer
    (computing only the missing ones), and write the matrix and the text database.

    Offline work, run by ``warm``, never by the compose hook. Both files are written
    beside the final ones and swapped in, so an interrupted build leaves the old
    index whole. The two swaps are not atomic together, which is why a query checks
    that the vector count and the passage count agree.
    """
    from divineos.core import vector_drawer

    rows: list[tuple[str, str, str, str, float, str]] = []
    for letter in letter_files(roots):
        try:
            text = letter.path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for passage in split_passages(text):
            rows.append(
                (
                    f"letter-{letter.name}",
                    letter.name,
                    letter.rel_path,
                    letter.title,
                    letter.mtime,
                    passage,
                )
            )
    texts = [r[5] for r in rows]
    filled = vector_drawer.fill(texts, progress)
    vectors = vector_drawer.lookup(texts)
    kept = [(r, vectors[r[5]]) for r in rows if vectors.get(r[5]) is not None]
    out = {
        "letters": len({r[0] for r in rows}),
        "passages": len(kept),
        "passages_without_vector": len(rows) - len(kept),
        "computed": filled["computed"],
    }
    if not kept:
        return out
    matrix = np.vstack([np.asarray(v, dtype=np.float32) for _, v in kept])
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    matrix = (matrix / np.where(norms == 0, 1.0, norms)).astype(np.float32)

    final_m, final_d = matrix_path(), db_path()
    tmp_m = final_m.with_name(final_m.name + ".new")
    tmp_d = final_d.with_name(final_d.name + ".new")
    final_m.parent.mkdir(parents=True, exist_ok=True)
    tmp_d.unlink(missing_ok=True)
    with open(tmp_m, "wb") as handle:
        np.save(handle, matrix)
    conn = sqlite3.connect(str(tmp_d))
    try:
        conn.execute(
            "CREATE TABLE passages (row INTEGER PRIMARY KEY, letter_id TEXT, name TEXT, path TEXT, "
            "title TEXT, mtime REAL, text TEXT)"
        )
        conn.executemany(
            "INSERT INTO passages VALUES (?, ?, ?, ?, ?, ?, ?)",
            [(i, *r) for i, (r, _) in enumerate(kept)],
        )
        conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
        conn.execute("INSERT INTO meta VALUES ('built_at', ?)", (str(time.time()),))
        conn.commit()
    finally:
        conn.close()
    os.replace(tmp_m, final_m)
    os.replace(tmp_d, final_d)
    _reset_cache()
    return out


# ------------------------------------------------------------------ querying


@dataclass(frozen=True)
class PassageHit:
    letter_id: str
    name: str
    path: str
    title: str
    mtime: float
    text: str
    similarity: float


_MATRIX: Any = None
_MATRIX_KEY: tuple[float, float] | None = None


def _reset_cache() -> None:
    global _MATRIX, _MATRIX_KEY
    _MATRIX = None
    _MATRIX_KEY = None


def _load_matrix() -> Any:
    global _MATRIX, _MATRIX_KEY
    path = matrix_path()
    stat = path.stat()
    stamp = (stat.st_mtime, float(stat.st_size))
    if _MATRIX is None or _MATRIX_KEY != stamp:
        _MATRIX = np.load(path, mmap_mode="r")
        _MATRIX_KEY = stamp
    return _MATRIX


def best_letters(
    topic_vec: Any, k: int = 1, floor: float = 0.0
) -> tuple[list[PassageHit], str | None]:
    """The best passage of each of the top k letters, and a problem when the index
    could not be read. ``([], None)`` means it was searched and nothing reached the
    floor; ``([], "<why>")`` means it could not be searched, and the two are never
    the same thing."""
    mpath, dpath = matrix_path(), db_path()
    if not mpath.exists() or not dpath.exists():
        return [], "the letter index is not built yet: run divineos linkage warm"
    try:
        matrix = _load_matrix()
        conn = sqlite3.connect(f"file:{dpath.as_posix()}?mode=ro", uri=True, timeout=5)
        try:
            count = conn.execute("SELECT COUNT(*) FROM passages").fetchone()[0]
            if count != matrix.shape[0]:
                return [], (
                    f"the letter index disagrees with itself ({matrix.shape[0]} vectors, "
                    f"{count} passages): run divineos linkage warm"
                )
            query = np.asarray(topic_vec, dtype=np.float32).ravel()
            if query.shape[0] != matrix.shape[1]:
                return [], "the letter index was built with a different vector size"
            norm = float(np.linalg.norm(query))
            if norm == 0.0:
                return [], None
            scores = np.asarray(matrix @ (query / norm))
            order = np.argsort(-scores)[: max(50, k * 20)]
            chosen: list[tuple[int, float]] = []
            letters_seen: set[str] = set()
            for row in order:
                score = float(scores[row])
                if score < floor:
                    break
                hit = conn.execute(
                    "SELECT letter_id FROM passages WHERE row = ?", (int(row),)
                ).fetchone()
                if hit is None or hit[0] in letters_seen:
                    continue
                letters_seen.add(hit[0])
                chosen.append((int(row), score))
                if len(chosen) >= k:
                    break
            hits: list[PassageHit] = []
            for row, score in chosen:
                r = conn.execute(
                    "SELECT letter_id, name, path, title, mtime, text FROM passages WHERE row = ?",
                    (row,),
                ).fetchone()
                hits.append(PassageHit(r[0], r[1], r[2], r[3], r[4], r[5], score))
            return hits, None
        finally:
            conn.close()
    except (OSError, ValueError, sqlite3.Error) as exc:
        return [], f"the letter index could not be read: {type(exc).__name__}: {exc}"


def staleness() -> str | None:
    """A cheap note when letters have been written since the index was built. It
    reads the directories' own timestamps, so it is never a scan of three thousand
    files on the compose path."""
    dpath = db_path()
    if not dpath.exists():
        return None
    try:
        built = dpath.stat().st_mtime
        from divineos.core.memory_linkage_retriever import _find_letters_roots

        newest = max((root.stat().st_mtime for root in _find_letters_roots()), default=0.0)
    except OSError:
        return None
    if newest > built:
        return (
            "letters have been written since the letter index was built: run divineos linkage warm"
        )
    return None
