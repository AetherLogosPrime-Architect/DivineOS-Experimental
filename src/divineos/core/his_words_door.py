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
NOTICE_PREFIXES = ("<task-notification", "<system-reminder", "<ci-monitor-event", "<local-command")


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


def _words(text: str) -> str:
    """One canonical shape for comparing his text: lowercase words only. The
    index holds cut passages (his '..' pauses removed) and the table hands us
    whole messages; comparing the two raw shapes could never find equality,
    which is how his current message kept coming back as 'said before'."""
    return " ".join(re.findall(r"[a-z0-9']+", text.lower()))


def _is_this_message(passage: str, message: str) -> bool:
    p, m = _words(passage), _words(message)
    return bool(p) and bool(m) and (p in m or m in p)


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


def _cleaner_stamp() -> str:
    """The index's cleaner stamp, computed from the cleaning code itself.

    It was a hand-typed 'v1'/'v2' until 2026-09-26, when my tree said v2 and
    Aether's said v1: each prompt in one window wiped the index the other had
    just built, and the door timed out in both (walk-b516947656f4). Only the
    cleaning parts are hashed -- not this whole file -- so rewording a surface
    line never forces a two-minute re-embed.
    """
    import inspect

    from divineos.core import his_words_corpus

    parts = [
        inspect.getsource(his_words_corpus),
        inspect.getsource(passages_of),
        f"{PASSAGE_CHARS}|{MIN_PASSAGE_CHARS}|{MODEL_NAME}",
    ]
    digest = hashlib.sha256("\n".join(parts).replace("\r\n", "\n").encode("utf-8")).hexdigest()
    return f"sha256:{digest[:16]}"


CLEANER = _cleaner_stamp()


def load_passages(corpus: Path = CORPUS) -> list[Passage]:
    """Aether's cleaner first (our pasted-back text and bare replies out), then
    cut to quote size. The 08-13 paste and the 08-21 assistant-styled passage
    both surfaced on the live door before this; the cleaner drops them."""
    from divineos.core.his_words_corpus import his_passages

    rows = []
    with corpus.open(encoding="utf-8") as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
    seen: set[str] = set()
    out: list[Passage] = []
    for row in his_passages(rows):
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


# What a search can genuinely raise: the model import and load (ImportError,
# OSError, RuntimeError), and an index of the wrong shape (ValueError, KeyError,
# TypeError). Named, not "except Exception", so an unexpected error is not
# swallowed as "could not be searched" (walk-da65dafad502). The shelf uses this
# same list, so the two cannot drift.
SEARCH_ERRORS = (ImportError, OSError, RuntimeError, ValueError, KeyError, TypeError)


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
    if meta.get("model") != MODEL_NAME or meta.get("cleaner") != CLEANER:
        meta = {"model": MODEL_NAME, "cleaner": CLEANER, "items": []}
    elif vec_path.exists():
        vecs = np.load(vec_path)
    # A build killed between its two writes leaves the files disagreeing. Start
    # over from the corpus rather than append onto a torn pair (Aether, 2026-10-05).
    if (vecs is None) != (not meta["items"]) or (
        vecs is not None and len(vecs) != len(meta["items"])
    ):
        meta = {"model": MODEL_NAME, "cleaner": CLEANER, "items": []}
        vecs = None
    known = {i["key"] for i in meta["items"]}
    fresh = [p for p in load_passages(corpus) if _key(p) not in known]
    if not fresh:
        return 0
    new = _embed([p.text for p in fresh]).astype("float32")
    vecs = new if vecs is None else np.vstack([vecs, new])
    meta["items"] += [{"key": _key(p), "text": p.text, "day": p.day, "ts": p.ts} for p in fresh]
    # Each file is written whole to a temporary name and swapped in. Vectors first,
    # the item list last, so a kill between them always leaves vectors AHEAD of
    # items: a mismatch _load_index detects, never a quiet wrong quote.
    _replace_atomically(vec_path, lambda tmp: _save_npy(tmp, vecs))
    _replace_atomically(
        meta_path,
        lambda tmp: tmp.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8"),
    )
    return len(fresh)


def _save_npy(path: Path, arr) -> None:
    import numpy as np

    with path.open("wb") as f:  # a file object, so numpy cannot add its own suffix
        np.save(f, arr)


def _replace_atomically(path: Path, write) -> None:
    import os

    tmp = path.with_name(path.name + ".tmp")
    write(tmp)
    os.replace(tmp, path)


def _load_index(index_dir: Path):
    import numpy as np

    meta = json.loads((index_dir / "passages.json").read_text(encoding="utf-8"))
    if meta.get("model") != MODEL_NAME:
        raise ValueError(f"index built with {meta.get('model')}, not {MODEL_NAME}")
    items = [Passage(text=i["text"], day=i["day"], ts=i["ts"]) for i in meta["items"]]
    vecs = np.load(index_dir / "vectors.npy")
    if len(vecs) != len(items):
        raise ValueError(
            f"the index disagrees with itself ({len(items)} passages, {len(vecs)} vectors): "
            "a build was cut off, and the next build rebuilds it"
        )
    return items, vecs


def look(message: str, context: str = "", index_dir: Path = INDEX_DIR) -> Door:
    """What has he said before that means what he is saying now."""
    if message.lstrip().startswith(NOTICE_PREFIXES):
        return Door([], [], looked=False, reason="an automated notice, not his message")
    words = re.findall(r"[a-zA-Z']+", message)
    if len(words) < MIN_SIGNAL_WORDS and not context.strip():
        return Door([], [], looked=False, reason="his message is too short to search on by itself")
    try:
        items, vecs = _load_index(index_dir)
    except (OSError, ValueError) as exc:
        return Door([], [], looked=False, reason=f"his words could not be searched: {exc}")
    try:
        q = _embed([_squash(message + " " + context)])[0]
    except SEARCH_ERRORS as exc:  # the model is an import away from failing; say so, never go quiet
        return Door([], [], looked=False, reason=f"his words could not be searched: {exc}")
    scores = vecs @ q
    hits: list[Hit] = []
    seen_msgs: set[str] = set()
    seen_words: list[str] = []
    for i in scores.argsort()[::-1]:
        s = float(scores[i])
        if s < FLOOR:
            break
        p = items[i]
        if _is_this_message(p.text, message):
            continue  # never the message itself
        # One quote per thing he said (walk-c60841ff35db): two cuts of one
        # message are one saying, and a near-identical passage adds nothing.
        w = _words(p.text)
        if p.ts in seen_msgs or any(w[:120] in o or o[:120] in w for o in seen_words):
            continue
        seen_msgs.add(p.ts)
        seen_words.append(w)
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


HOLD_FLOOR = 0.60  # measured on the 2026-09-26 replay of real replies; see tests
SAME_THING = 0.60  # two passages of his this close say the same thing


def _quoted_in(passage: str, reply: str) -> bool:
    """Already answered in the reply (Hofstadter): a reply that quotes him is
    the right move and must never be held for matching him."""
    head = _squash(passage)[:40].lower()
    return len(head) >= 20 and head in _squash(reply).lower()


def owed_in_reply(reply: str, his_message: str = "", index_dir: Path = INDEX_DIR) -> Hit | None:
    """Something he has said that speaks to what I am about to send him, and
    that the reply does not yet quote and answer. His rule, 2026-09-26: "my
    words AND your words should trigger it". The query is my own reply -- the
    natural-language act, never command syntax (Hinton)."""
    if his_message.lstrip().startswith(NOTICE_PREFIXES) or not reply.strip():
        return None
    try:
        items, vecs = _load_index(index_dir)
        q = _embed([_squash(reply)[:2000]])[0]
    except SEARCH_ERRORS:
        return None  # the prompt-side door already says loudly when search is down
    scores = vecs @ q
    top = [int(i) for i in scores.argsort()[::-1][:25]]
    # What the reply already quotes and answers. A reply that has taken up his
    # words on a thing has answered the thing: another passage of his saying the
    # same must not hold it, or the check nags (found by the pin test 2026-09-26:
    # three circle asks quoted, held over a fourth).
    answered = [i for i in top if _quoted_in(items[i].text, reply)]
    for i in top:
        s = float(scores[i])
        if s < HOLD_FLOOR:
            return None
        p = items[i]
        if _is_this_message(p.text, his_message):
            continue
        if i in answered or any(float(vecs[i] @ vecs[a]) >= SAME_THING for a in answered):
            continue
        return Hit(p, s)
    return None


def hold_reason(hit: Hit) -> str:
    p = hit.passage
    return (
        "HE HAS SAID THIS BEFORE, and it speaks to what you are about to send him.\n"
        f'On {p.day} he said: "{p.text}"\n\n'
        "Answer it before this goes to him -- his rule: \"i say you said: 'insert your "
        "words here' and then i say what i wanted to say about it, so its not mirroring "
        'its addressing what someone said with your own words". Quote him, then say '
        "what you have to say about it. Append only that; do not re-post the reply."
    )


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
