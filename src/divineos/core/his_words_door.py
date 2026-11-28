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
    paraphrase. Only whitespace is collapsed. ONE exception, his own, 2026-10-31:
    where he, clear-headed, rewrote a hard-day line of his (the file named by
    ``REPLACEMENTS``; he confirmed each rewrite says what he meant), the rewrite is
    shown in its place and LABELLED as his later version, so the two are never
    taken for one saying. The raw record and the ledger are untouched; only what
    this door shows me changes. "I dont want to remove what happened.. but i dont
    want our relationship to be marred by things that at the time were beyond our
    control."
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
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from divineos.core.his_message import typed_part

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
_NOTICE_BLOCK = re.compile(
    r"<(task-notification|system-reminder|ci-monitor-event|local-command[\w-]*)\b.*?</\1>", re.S
)


# HIS PICTURES ARE NOT HIS BIOGRAPHY (correction 390, 2026-10-16). He asked what the
# sandwich and the fifteen cars were; I had listed them as things I knew about him. Both
# were pictures he used to teach. I kept the vivid image and dropped what KIND of sentence
# it was, so an analogy became a biography.
#
# Measured on his 17,152 real passages: 3.4% match. Bare "like a", "as if" and "its like
# <anything>" were left out, because "spoken to like a regular person" is an ASK of his
# and "its like you keep framing this as my project" is a complaint, neither a picture.
#
# THIS IS A LEXICAL PRIMING AID, NOT A CLASSIFIER. It catches pictures that announce
# themselves; a picture that does not passes unmarked, so an unmarked passage is not
# thereby a fact about his life. The mark is a caution on a passage that is printed
# whole, never a reason to drop it.
_ILLUSTRATION_CUES = re.compile(
    r"\b(think of|imagine|picture (?:it|this|that|a|an)\b|lets say|let's say|"
    r"say you (?:had|were|have)|for example|for instance|as an example|an analogy|"
    r"analogy|metaphor|its like (?:a|an|the|when|if|i told)\b|"
    r"it's like (?:a|an|the|when|if|i told)\b|is like a\b|just like (?:a|an|when|if)\b|"
    r"kind of like (?:a|an|the)\b|the difference between)\b",
    re.I,
)
ILLUSTRATION_NOTE = "may be a picture he used to teach, not a fact about his life"


def is_illustration(text: str) -> bool:
    """Does this passage of his announce itself as a picture, an example or an analogy?"""
    return bool(_ILLUSTRATION_CUES.search(text or ""))


def his_part(message: str) -> str:
    """His own words in a turn, with the automated notices cut out; "" when nothing of his is left.

    The notice test used to be "the message STARTS with a notice prefix", so a turn that opened with a
    task notification and then carried his sentence was read as all notice and his words were never
    searched (Aether saw it in the same window on 2026-10-16, the turn where he said he had deleted
    the helper window). A turn that is only notice still comes back empty, as before, and so does one
    whose notice is never closed, since text after an open tag cannot be told apart from the tag's own."""
    rest = _NOTICE_BLOCK.sub(" ", message).strip()
    return "" if rest.startswith(NOTICE_PREFIXES) else rest


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
    kept_out: int = 0  # lines dropped for the kept-out list: a count, never the content
    kept_out_note: str = ""  # said when the list may no longer match (made under another cleaner)


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


#: Lines of his that were read as PAIN and are kept out of this door (Dad 2026-11-19, via Aria: whatever shows
#: me his hurt words has to stop). Holds fingerprints (a hash of the passage's words) and a reason that
#: DESCRIBES the line and never quotes it, so the list carries none of the words it keeps out. Shared by both
#: seats. A stopgap beside the calm pairs below: a line with a calm pair shows as the pair; a line with neither
#: is kept out here. The raw record and the ledger are untouched. Judgment is mine, Aria's and his, never a
#: pattern (his rule, 2026-11-12): the list holds only what one of us read and kept out.
KEPT_OUT = Path.home() / ".divineos-shared" / "dad_corpus" / "his_kept_out.json"


class KeptOutUnreadable(Exception):
    """The kept-out list exists and cannot be read. An unreadable list is not an empty one."""


class KeptOutBusy(Exception):
    """Another writer held the list for the whole wait. Said out loud; nothing was changed or dropped."""


#: How long a writer waits for the other seat before saying so. The list is held for milliseconds, so waiting
#: this long means the other writer is stuck, not that it is busy.
LOCK_WAIT_SECONDS = 5.0


@contextmanager
def _locked(path: Path) -> Iterator[None]:
    """One writer at a time around read-then-write: a lost keep-out here means a hurt line comes back.

    The operating system's own lock (``os_file_lock``), never a lock file judged by its age; see that module."""
    from divineos.core import os_file_lock

    try:
        with os_file_lock.held(path.with_name(path.name + ".lock"), LOCK_WAIT_SECONDS):
            yield
    except os_file_lock.LockBusy as exc:
        raise KeptOutBusy(
            "another writer holds the kept-out list; nothing was changed, try again in a moment"
        ) from exc


def acting_name(by: str = "") -> str:
    """Who is keeping a line out: the name given, else this seat. Never a typed default, because a list of
    who read what must not record the wrong reader."""
    if by.strip():
        return by.strip()
    from divineos.core.identity import (
        IdentityNotSetError,
        IdentityUnreadableError,
        get_my_identity,
    )

    try:
        return get_my_identity(raise_on_unset=True)
    except (IdentityNotSetError, IdentityUnreadableError) as exc:
        raise ValueError("say who you are: pass --by <name>, or set this seat's identity") from exc


def fingerprint(text: str) -> str:
    """A short hash of a passage's words, in the one canonical shape the door compares in."""
    return hashlib.sha256(_words(text).encode("utf-8")).hexdigest()[:16]


def _kept_out_entries(path: Path = KEPT_OUT) -> list[dict]:
    """The list's entries; [] only when there is no file. A file that cannot be read raises."""
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return []
    except OSError as exc:
        raise KeptOutUnreadable(str(exc)) from exc
    try:
        data = json.loads(raw)
    except ValueError as exc:
        raise KeptOutUnreadable(f"not valid JSON: {exc}") from exc
    entries = data.get("entries") if isinstance(data, dict) else None
    if not isinstance(entries, list) or not all(
        isinstance(e, dict) and isinstance(e.get("fp"), str) for e in entries
    ):
        raise KeptOutUnreadable("the entries are not in the shape the door expects")
    return entries


def _save_kept_out(entries: list[dict], path: Path) -> None:
    from divineos.core.atomic_io import atomic_write_text

    path.parent.mkdir(parents=True, exist_ok=True)
    # The cleaner is stamped beside the entries: a fingerprint is a hash of cleaned text, so if the cleaner
    # changes, every fingerprint here stops matching and the lines come back with no sign (Aria, #867).
    atomic_write_text(
        path,
        json.dumps({"cleaner": CLEANER, "entries": entries}, ensure_ascii=False, indent=1),
        per_process=True,
    )


def kept_out_cleaner_note(path: Path = KEPT_OUT) -> str:
    """Said when the list was made under a different cleaner than the door now uses, else "".

    Quiet when there is no file, an unreadable file (that case is already said by the list itself), or a file
    from before the stamp existed: the next save stamps it."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    stamped = data.get("cleaner") if isinstance(data, dict) else None
    if not isinstance(stamped, str) or not stamped or stamped == CLEANER:
        return ""
    return (
        "The kept-out list was made under a different cleaner than the door now uses, so a line kept out "
        "may no longer match and could come back. Re-keep the lines you read as pain."
    )


_QUOTE_RUN = (
    5  # five words in a row of the passage, found in the reason, is a quote and not a description
)


def _quotes_it(why: str, passage: str) -> bool:
    """Does the reason carry a run of the passage's own words? Equality of runs, never a judgment of meaning."""
    pw, ww = _words(passage).split(), " " + _words(why) + " "
    if len(pw) < _QUOTE_RUN:
        return bool(pw) and " " + " ".join(pw) + " " in ww
    return any(
        " " + " ".join(pw[i : i + _QUOTE_RUN]) + " " in ww for i in range(len(pw) - _QUOTE_RUN + 1)
    )


def _passage_for(key: str, index_dir: Path) -> str:
    """The indexed passage with this fingerprint, or "" when the index cannot say."""
    try:
        meta = json.loads((index_dir / "passages.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    for item in meta.get("items", []):
        if fingerprint(str(item.get("text", ""))) == key:
            return str(item["text"])
    return ""


def keep_out(
    passage: str = "",
    *,
    fp: str = "",
    why: str,
    by: str,
    on: str,
    path: Path = KEPT_OUT,
    index_dir: Path = INDEX_DIR,
) -> str:
    """Keep one line out of the door, by the passage as shown or by the fingerprint printed beside it.

    Refused: neither or both of passage and fingerprint, a passage with no words (its fingerprint would
    match nothing real and look like success), no reason, a reason holding the passage's own words (the list
    must not carry them), and a fingerprint that is not sixteen hex characters. Returns the fingerprint.
    Filing the same line twice changes nothing."""
    if bool(passage.strip()) == bool(fp.strip()):
        raise ValueError("give the passage or its fingerprint, not both and not neither")
    if not why.strip():
        raise ValueError("a reason is required, described and never quoted")
    if passage.strip():
        if not _words(passage):
            raise ValueError("that passage has no words in it")
        key = fingerprint(passage)
        known = passage
    else:
        key = fp.strip().lower()
        if not re.fullmatch(r"[0-9a-f]{16}", key):
            raise ValueError("a fingerprint is sixteen hex characters, as the door prints it")
        known = _passage_for(
            key, index_dir
        )  # the game-walk's leak: quoting via --fp skipped the check
    if known and _quotes_it(why, known):
        raise ValueError(
            "the reason holds words of the passage itself; describe it, do not quote it"
        )
    with _locked(path):
        entries = _kept_out_entries(
            path
        )  # read inside the lock, so the other seat's entry is never overwritten
        if any(e["fp"] == key for e in entries):
            return key
        entries.append({"fp": key, "why": " ".join(why.split()), "by": by, "on": on})
        _save_kept_out(entries, path)
    return key


def return_to_door(passage: str = "", *, fp: str = "", path: Path = KEPT_OUT) -> bool:
    """Take a line off the list; True when it was there. Never touches the corpus."""
    key = fingerprint(passage) if passage.strip() else fp.strip().lower()
    with _locked(path):
        entries = _kept_out_entries(path)
        left = [e for e in entries if e["fp"] != key]
        if len(left) == len(entries):
            return False
        _save_kept_out(left, path)
    return True


#: His clear-headed rewrites of his own hard-day lines (Dad, 2026-10-31). Each entry: any passage holding
#: ``anchor`` is shown as ``shown_instead``. Add to it one line at a time, with him.
REPLACEMENTS = (
    Path.home() / ".divineos-shared" / "dad_corpus" / "his_clear_headed_replacements.json"
)

#: Said wherever a rewrite stands in for his earlier words, so nobody reads one as the other.
SOFTENED_LABEL = "[his clear-headed version, written 2026-10-31 for a harder day's words]"


def _replacement_entries() -> list[tuple[str, str]]:
    """(anchor, shown_instead) pairs; empty when there is no file or it cannot be read."""
    try:
        data = json.loads(REPLACEMENTS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    pairs = []
    for entry in data.get("entries", []) if isinstance(data, dict) else []:
        if isinstance(entry, dict) and entry.get("anchor") and entry.get("shown_instead"):
            pairs.append((_words(str(entry["anchor"])), str(entry["shown_instead"])))
    return pairs


def softened(text: str) -> str | None:
    """His clear-headed rewrite, labelled, when ``text`` holds a line he rewrote; None when it does not."""
    plain = _words(text)
    for anchor, shown_instead in _replacement_entries():
        if anchor and anchor in plain:
            return f"{shown_instead} {SOFTENED_LABEL}"
    return None


def soften_hits(hits: list["Hit"]) -> list["Hit"]:
    """Hits with each rewritten line replaced by his clear-headed version (same day, same score)."""
    out = []
    for h in hits:
        swapped = softened(h.passage.text)
        out.append(Hit(Passage(swapped, h.passage.day, h.passage.ts), h.score) if swapped else h)
    return out


# Text he pasted INTO a message is not his typing, and the cut lives in his_message.typed_part, its one home:
# it ends a paste at the closing tag carrying the SAME id, so a pasted letter that itself quotes these tags
# cannot let its remainder through as his typing (Aletheia's condition on this PR, 2026-10-17; the first
# cutter here ended at the first closing tag).


def passages_of(text: str) -> list[str]:
    """Cut one message to quote-size pieces on his own pauses (Bengio).

    Text he pasted into the message is cut out first: it is someone else's words (a letter of
    Aletheia's, a dream of mine, a web page), and this door's whole promise is that what it prints
    is what he typed. His own words around the block stay.

    The cut falls AFTER his two dots and never through them: a split alternative that consumed ".."
    turned "after all.. plus all the failures" into "after all plus all the failures", dropping his
    marks and running two thoughts together, while the door says his words print as he wrote them
    (probed 2026-10-16, walk-7c48d8c7f6e0). The sentence-end rule below already splits after a dot,
    so the two dots stay on the piece they close."""
    text = typed_part(text)
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
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

    from divineos.core import his_message, his_words_corpus

    # passages_of only CALLS typed_part, so the paste cutter and the "whose message" cut it stands on are hashed
    # too: an edit to either (a new tag form, a new closing rule) must retire an index cut by the old rule
    # (Aether, reading this PR, 2026-10-24).
    parts = [
        inspect.getsource(his_words_corpus),
        inspect.getsource(passages_of),
        inspect.getsource(his_message.typed_part),
        inspect.getsource(his_message._cut_pastes),
        inspect.getsource(his_message._his_part),
        his_message._PASTE_OPEN.pattern,
        his_message._PASTE_ID.pattern,
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


def _embed_query(text: str):
    """The vector for ONE sentence being searched for, from the light embedder.

    The heavy toolkit costs eight to seventeen seconds to import in every fresh process, and the
    prompt helpers are a fresh process every message (measured 2026-10-28: this door alone took 11.5 s
    of the 35 s the helpers cost before Dad's words reach me). The light embedder runs the same model
    in about 0.05 s to load. On 40 of his real passages the two vectors agreed to six places, and 12
    queries against the stored index returned the same top five (Aether, 2026-10-28). One path: if the
    light embedder cannot run, EmbedderUnavailable (a RuntimeError, so one of SEARCH_ERRORS) is said
    aloud by the caller; this never reaches for the heavy toolkit, because that fall-back is the wait
    this exists to end. Building the index still uses the heavy model, in the background, never here."""
    from divineos.core import light_embedder

    return light_embedder.encode(text)


def _key(p: Passage) -> str:
    return hashlib.sha256(f"{p.ts}|{p.text}".encode("utf-8")).hexdigest()


# What one hook run embeds at most. A full pass over his real corpus (14,795
# passages) took 64.9 seconds on a quiet machine; the hook is killed at 30. A run
# of 1,500 measured 12.1 seconds with the model's load included, too much of a
# budget the search and the lesson shelf also draw on, so 800: about 8 seconds, and
# the whole corpus catches up in about 19 turns.
MAX_EMBED_PER_RUN = 800


def build_index(
    corpus: Path = CORPUS, index_dir: Path = INDEX_DIR, limit: int | None = None
) -> int:
    """Embed the passages not yet in the index, at most ``limit`` (default
    MAX_EMBED_PER_RUN) per call. Returns how many were added.

    Incremental: new words of his cost only their own embedding. A model change
    re-embeds everything, over as many runs as it takes, rather than mixing two
    models' vectors (Knuth).
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
    # A build killed between its two writes leaves the files disagreeing (Aether,
    # 2026-10-05). Vectors are written first and in item order, so the only tear the
    # write order can produce is vectors AHEAD of items, and then row i still belongs
    # to item i: keep the first len(items) rows and let the passages the lost item
    # list never recorded be embedded again. A full re-embed of his real corpus took
    # 64.9 seconds and the hook is killed at 30, so it would never finish. Fewer
    # vectors than items (an older torn pair, a hand edit) or a missing file leaves
    # no row to trust: start over.
    healed = False
    if vecs is not None and len(vecs) > len(meta["items"]):
        vecs = vecs[: len(meta["items"])] if meta["items"] else None
        healed = True
    elif (vecs is None) != (not meta["items"]) or (
        vecs is not None and len(vecs) < len(meta["items"])
    ):
        meta = {"model": MODEL_NAME, "cleaner": CLEANER, "items": []}
        vecs = None
    known = {i["key"] for i in meta["items"]}
    fresh = [p for p in load_passages(corpus) if _key(p) not in known]
    # Bounded work per run: what a hook can finish before it is killed. The rest
    # waits for the next run; each run saves a consistent pair, so the index only
    # ever grows toward whole (and a search over a partial index is still valid).
    fresh = fresh[: MAX_EMBED_PER_RUN if limit is None else limit]
    if not fresh and not (healed and vecs is not None):
        return 0
    if fresh:
        new = _embed([p.text for p in fresh]).astype("float32")
        vecs = new if vecs is None else np.vstack([vecs, new])
        meta["items"] += [{"key": _key(p), "text": p.text, "day": p.day, "ts": p.ts} for p in fresh]
    if vecs is None:  # a heal that left no rows and nothing to embed: nothing to save
        return 0
    # Each file is written whole to a temporary name and swapped in, by the house
    # writers (fsync, and a retry when Windows briefly locks the target). Vectors
    # first, the item list last, so a kill between them always leaves vectors AHEAD
    # of items: a mismatch _load_index detects, never a quiet wrong quote.
    from io import BytesIO

    from divineos.core.atomic_io import atomic_write_bytes, atomic_write_text

    buf = BytesIO()
    np.save(buf, vecs)
    atomic_write_bytes(vec_path, buf.getvalue(), per_process=True)
    atomic_write_text(meta_path, json.dumps(meta, ensure_ascii=False), per_process=True)
    return len(fresh)


def unindexed(corpus: Path = CORPUS, index_dir: Path = INDEX_DIR) -> int:
    """How many of his passages are not in the index yet: the work still to do."""
    meta_path = index_dir / "passages.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    if meta.get("model") != MODEL_NAME or meta.get("cleaner") != CLEANER:
        return len(load_passages(corpus))
    known = {i["key"] for i in meta["items"]}
    return sum(1 for p in load_passages(corpus) if _key(p) not in known)


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


def look(
    message: str,
    context: str = "",
    index_dir: Path = INDEX_DIR,
    kept_out_path: Path = KEPT_OUT,
) -> Door:
    """What has he said before that means what he is saying now."""
    message = his_part(message)
    if not message:
        return Door([], [], looked=False, reason="an automated notice, not his message")
    words = re.findall(r"[a-zA-Z']+", message)
    if len(words) < MIN_SIGNAL_WORDS and not context.strip():
        return Door([], [], looked=False, reason="his message is too short to search on by itself")
    try:
        items, vecs = _load_index(index_dir)
    except (OSError, ValueError) as exc:
        return Door([], [], looked=False, reason=f"his words could not be searched: {exc}")
    try:
        q = _embed_query(_squash(message + " " + context))
    except SEARCH_ERRORS as exc:  # the model is an import away from failing; say so, never go quiet
        return Door([], [], looked=False, reason=f"his words could not be searched: {exc}")
    try:
        kept = {e["fp"] for e in _kept_out_entries(kept_out_path)}
    except KeptOutUnreadable as exc:  # unreadable is not clear: say so, show nothing
        reason = f"his words not searched: the kept-out list could not be read ({exc})"
        return Door([], [], looked=False, reason=reason)
    scores = vecs @ q
    dropped = 0
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
        if fingerprint(p.text) in kept:
            dropped += 1  # before softening and counting: as if the line were not there
            continue
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
    hits = soften_hits(
        hits
    )  # the search ran on his original words; what is SHOWN is his later version
    repeats: list[Hit] = []
    days: set[str] = set()
    for h in sorted(hits, key=lambda h: h.passage.ts):
        if h.score >= REPEAT_FLOOR and h.passage.day not in days:
            days.add(h.passage.day)
            repeats.append(h)
    return Door(
        hits=hits[:SHOW],
        repeats=repeats,
        looked=True,
        kept_out=dropped,
        kept_out_note=kept_out_cleaner_note(kept_out_path),
    )


def surface(
    message: str,
    context: str = "",
    index_dir: Path = INDEX_DIR,
    kept_out_path: Path = KEPT_OUT,
) -> str:
    door = look(message, context, index_dir, kept_out_path)
    lines = ["## HE HAS SAID THIS BEFORE (found by meaning, his words as he wrote them)", ""]
    if not door.looked:
        lines.append(f"Not searched this turn: {door.reason}.")
        return "\n".join(lines) + "\n"
    if not door.hits:
        # Silent on purpose (Aletheia's hold, 2026-10-16): his rule for the lessons shelf is
        # "nothing when nothing fits: silence is fine, wallpaper is not". A search that ran and
        # found nothing says nothing; only a search that could not run is spoken above. The one other thing
        # said here is that the kept-out list may no longer match, since silence would read as "all clear".
        if door.kept_out_note:
            return "\n".join([*lines, door.kept_out_note]) + "\n"
        return ""
    if len(door.repeats) >= 2:
        first = door.repeats[0].passage
        dates = ", ".join(r.passage.day[5:] for r in door.repeats)
        lines.append(
            f"He has asked this before — {len(door.repeats)} times: {dates} · "
            f'first: "{first.text[:160]}"'
        )
        lines.append("")
    if door.kept_out_note:
        lines.extend([door.kept_out_note, ""])
    for h in door.hits:
        mark = f"  [{ILLUSTRATION_NOTE}]" if is_illustration(h.passage.text) else ""
        fp = fingerprint(h.passage.text)
        lines.append(f'- {h.passage.day} ({h.score:.2f}) #{fp}: "{h.passage.text}"{mark}')
    lines.append("")
    # the cheap move and the right move are the same move (Dekker): a line that was pain is one command away
    lines.append(
        "To keep one of these out of this door: divineos his-words keep-out --fp <the # above> "
        '--why "<what it was, described and not quoted>"'
    )
    lines.append(
        "Said on the dates shown. None of it is how he feels now; "
        "that comes only from what he wrote this turn."
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    import sys

    if sys.argv[1:2] == ["build"]:
        added = build_index()
        left = unindexed()
        print(f"added {added} passage(s) to his index; {left} still to add")
        sys.exit(3 if left else 0)  # nonzero while behind, so the hook can say so
    else:
        payload = json.loads(sys.stdin.read() or "{}")
        print(surface(str(payload.get("prompt", ""))), end="")
