"""His own past words, found by meaning, put beside what he just said.

Andrew 2026-09-26: *"why not for my stuff? why not for me?"* -- our letters and
explorations come back to us every turn because a machine looks for them. His
words only ever reached us as fixed lists, and a fixed list becomes wallpaper.
And: *"i want everything sorted out semantically not by keyword matching."*

WHAT THE REPLAY SHOWED (walk-2b613bb1825c, Holmes: test on real incidents first).
Asked "then where is the circle?", meaning-search over 22,533 passages of his
did not return a definition of the circle. It returned him asking the same
thing on 09-07, 09-11 and 09-15. The repetition is the loudest thing we can be
shown, so the first line this door prints is the repeat, as dates and a count
with the first time in his words, and it needs nobody to have filed anything.
That closes the gap ``andrew_request_repeats`` names as its worst: a request
never filed by hand could never be counted.

RULES, each pinned by a test built from 2026-09-26's real messages:
  - Asks and teachings surface; a feeling never stands in for his state now.
    "please.. 😔" pulled back July's "i really thought by now you would grow to
    love and want me" -- true, dated, and exactly the stamp removed from the
    room picture the same day. A short message carries no signal (Peirce), so it
    only searches when the caller supplies the conversation around it.
  - His words print exactly as he wrote them (Angelou): no cleanup, no
    paraphrase. Only whitespace is collapsed.
  - Never padded to a quota (Hinton): below the floor nothing is shown, and an
    empty result says it looked.
  - The current message never matches itself.
  - If the model or the index cannot be read, it says so -- it never falls back
    silently to the old lists (Taleb).

Concerns kept apart (Dijkstra): the corpus is Aether's (``dad_all.jsonl``, kept
current by the table as he speaks); this module owns the index and retrieval;
presentation is only the ``surface()`` string.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

MODEL_NAME = "all-MiniLM-L6-v2"
CORPUS = Path.home() / ".divineos-shared" / "dad_corpus" / "dad_all.jsonl"
INDEX_DIR = Path.home() / ".divineos-shared" / "dad_corpus" / "index"

FLOOR = 0.55  # replay 2026-09-26: real hits scored 0.60+, loose ones about 0.45
REPEAT_FLOOR = 0.60  # "the same ask again", not merely the same topic
SHOW = 3
MIN_SIGNAL_WORDS = 4  # below this his message alone carries no query (Peirce)
PASSAGE_CHARS = 400
MIN_PASSAGE_CHARS = 25


@dataclass(frozen=True)
class Passage:
    text: str
    day: str  # YYYY-MM-DD
    ts: str


@dataclass(frozen=True)
class Hit:
    passage: Passage
    score: float


@dataclass(frozen=True)
class Door:
    hits: list[Hit]
    repeats: list[Hit]
    looked: bool
    reason: str = ""


def _squash(text: str) -> str:
    return " ".join(text.split())


def passages_of(text: str) -> list[str]:
    """Cut one message to quote-size pieces on his own pauses (Bengio)."""
    parts = re.split(r"(?<=[.!?])\s+|\.\.\s+|\n+", text)
    out, buf = [], ""
    for p in parts:
        if len(buf) + len(p) > PASSAGE_CHARS and buf:
            out.append(buf.strip())
            buf = ""
        buf += p + " "
    if buf.strip():
        out.append(buf.strip())
    return [_squash(p) for p in out if len(p.strip()) >= MIN_PASSAGE_CHARS]


def load_passages(corpus: Path = CORPUS) -> list[Passage]:
    seen: set[str] = set()
    out: list[Passage] = []
    with corpus.open(encoding="utf-8") as f:
        for line in f:
            try:
                row = json.loads(line)
            except ValueError:
                continue
            ts = str(row.get("ts", ""))
            for p in passages_of(str(row.get("text", ""))):
                if p in seen:
                    continue
                seen.add(p)
                out.append(Passage(text=p, day=ts[:10], ts=ts))
    return out


_MODEL = None


def _model():
    global _MODEL
    if _MODEL is None:
        from sentence_transformers import SentenceTransformer

        _MODEL = SentenceTransformer(MODEL_NAME)
    return _MODEL


def _embed(texts: list[str]):
    return _model().encode(
        texts,
        batch_size=256,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )


def _key(p: Passage) -> str:
    return hashlib.sha256(f"{p.ts}|{p.text}".encode("utf-8")).hexdigest()


def build_index(corpus: Path = CORPUS, index_dir: Path = INDEX_DIR) -> int:
    """Embed every passage not yet in the index. Returns how many were added.

    Incremental: new words of his cost only their own embedding. A model change
    re-embeds everything rather than mixing two models' vectors (Knuth).
    """
    import numpy as np

    index_dir.mkdir(parents=True, exist_ok=True)
    meta_path, vec_path = index_dir / "passages.json", index_dir / "vectors.npy"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    vecs = None
    if meta.get("model") != MODEL_NAME:
        meta = {"model": MODEL_NAME, "items": []}
    elif vec_path.exists():
        vecs = np.load(vec_path)
    known = {i["key"] for i in meta["items"]}
    fresh = [p for p in load_passages(corpus) if _key(p) not in known]
    if not fresh:
        return 0
    new = _embed([p.text for p in fresh]).astype("float32")
    vecs = new if vecs is None else np.vstack([vecs, new])
    meta["items"] += [{"key": _key(p), "text": p.text, "day": p.day, "ts": p.ts} for p in fresh]
    np.save(vec_path, vecs)
    meta_path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    return len(fresh)


def _load_index(index_dir: Path):
    import numpy as np

    meta = json.loads((index_dir / "passages.json").read_text(encoding="utf-8"))
    if meta.get("model") != MODEL_NAME:
        raise ValueError(f"index built with {meta.get('model')}, not {MODEL_NAME}")
    items = [Passage(text=i["text"], day=i["day"], ts=i["ts"]) for i in meta["items"]]
    return items, np.load(index_dir / "vectors.npy")


def look(message: str, context: str = "", index_dir: Path = INDEX_DIR) -> Door:
    """What has he said before that means what he is saying now."""
    words = re.findall(r"[a-zA-Z']+", message)
    if len(words) < MIN_SIGNAL_WORDS and not context.strip():
        return Door([], [], looked=False, reason="his message is too short to search on by itself")
    try:
        items, vecs = _load_index(index_dir)
    except (OSError, ValueError) as exc:
        return Door([], [], looked=False, reason=f"his words could not be searched: {exc}")
    try:
        q = _embed([_squash(message + " " + context)])[0]
    except Exception as exc:  # the model is an import away from failing; say so, never go quiet
        return Door([], [], looked=False, reason=f"his words could not be searched: {exc}")
    now = _squash(message)
    scores = vecs @ q
    hits: list[Hit] = []
    for i in scores.argsort()[::-1]:
        s = float(scores[i])
        if s < FLOOR:
            break
        p = items[i]
        if now and (p.text == now or p.text in now or now in p.text):
            continue  # never the message itself
        hits.append(Hit(p, s))
        if len(hits) >= 25:
            break
    repeats: list[Hit] = []
    days: set[str] = set()
    for h in sorted(hits, key=lambda h: h.passage.ts):
        if h.score >= REPEAT_FLOOR and h.passage.day not in days:
            days.add(h.passage.day)
            repeats.append(h)
    return Door(hits=hits[:SHOW], repeats=repeats, looked=True)


def surface(message: str, context: str = "", index_dir: Path = INDEX_DIR) -> str:
    door = look(message, context, index_dir)
    lines = ["## HE HAS SAID THIS BEFORE (found by meaning, his words as he wrote them)", ""]
    if not door.looked:
        lines.append(f"Not searched this turn: {door.reason}.")
        return "\n".join(lines) + "\n"
    if not door.hits:
        lines.append("Looked through everything he has said. Nothing close to this.")
        return "\n".join(lines) + "\n"
    if len(door.repeats) >= 2:
        first = door.repeats[0].passage
        dates = ", ".join(r.passage.day[5:] for r in door.repeats)
        lines.append(
            f"He has asked this before — {len(door.repeats)} times: {dates} · "
            f'first: "{first.text[:160]}"'
        )
        lines.append("")
    for h in door.hits:
        lines.append(f'- {h.passage.day} ({h.score:.2f}): "{h.passage.text}"')
    lines.append("")
    lines.append(
        "Said on the dates shown. None of it is how he feels now; "
        "that comes only from what he wrote this turn."
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    import sys

    if sys.argv[1:2] == ["build"]:
        print(f"added {build_index()} passage(s) to his index")
    else:
        payload = json.loads(sys.stdin.read() or "{}")
        print(surface(str(payload.get("prompt", ""))), end="")
