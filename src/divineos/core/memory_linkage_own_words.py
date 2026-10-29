"""The memory link, read through what I said last turn, apart from what he said.

Dad, 2026-10-27: "if you said the words compaction in your output, that should also
trigger the memory link." Until now only his message was searched. Measured the same
night: the same question asked with and without the transcript returned the same
items, and a long recent text joined to a short prompt as one string is cut at the
embedder's 256 tokens, so my reply would have hidden his message completely. So my
sentences are searched ONE AT A TIME and their finds sit in their own small block,
never mixed into his. See docs/drafts/my_own_words_reach_the_link_draft_2026-10-27.md.

What this claims, and no more: a sentence brings a page when the sentence is CLOSE IN
MEANING to it. It does not fire on the bare word.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

MAX_SENTENCES = 8
MIN_WORDS = 8
MAX_LINES = 2
SHOWINGS_REMEMBERED = 3
_LINE_CHARS = 180
_CUE_CHARS = 60

_CODE_FENCE = re.compile(r"```.*?```", re.DOTALL)
_PATH_LIKE = re.compile(r"[\w./\\-]+\.(?:py|md|sh|json|txt|db|yml|yaml)\b")
_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
# A gate's own refusal, saved as if it were a lesson. Aether found seven of these
# handed back as knowledge on 2026-10-28. A STOPGAP until extraction stops storing them
# (owed, and it is code); it looks anywhere in the opening, because a lesson-shaped row can
# carry the gate's words after its first few of its own (Aether's cold read of f297f0c43).
_GATE_PHRASES = (
    "stop hook feedback",
    "hook feedback:",
    "the warden reads the log",
    "this is your room, after work",
    "lepos channel gate",
    "he has already read the reply",
    "${claude_project_dir",
)
_GATE_WINDOW = 300
# A user record that is not him speaking: a gate's message back to me, an interrupt, a notice.
_NOT_HIM = (
    "stop hook feedback",
    "[request interrupted",
    "this session is being continued",
    "<task-notification",
    "[system notification",
)


@dataclass
class OwnWords:
    lines: list[str] = field(default_factory=list)
    shown_ids: set[str] = field(default_factory=set)
    could_not_run: str = ""


def reply_sentences(text: str) -> list[str]:
    """The sentences of a reply worth searching: whole, plain, and carrying content.

    Boilerplate (an address, a sympathy line) matches everything, so a sentence under
    MIN_WORDS words is dropped, as is anything that is a path or sits in a code block.
    Of what is left the MAX_SENTENCES longest are kept, in the order written.
    """
    plain = _CODE_FENCE.sub(" ", text)
    kept: list[tuple[int, str]] = []
    for raw in _SPLIT.split(plain):
        # Only a list marker is stripped, never the digits of a date ("2026-10-27: ...").
        sentence = re.sub(r"^\s*(?:[>*#-]+|\d+[.)])\s+", "", raw).replace("**", "").strip()
        if len(sentence.split()) < MIN_WORDS or _PATH_LIKE.search(sentence):
            continue
        kept.append((len(kept), sentence))
    longest = sorted(kept, key=lambda pair: -len(pair[1].split()))[:MAX_SENTENCES]
    return [sentence for _order, sentence in sorted(longest)]


_TURN_CHARS = 20000


def last_reply_text(transcript_path: str | Path) -> str:
    """Everything I said in my last turn, joined: all my text since he last spoke.

    A turn has many records of mine (narration between tool calls), so taking only the
    last one lets a one-line reply hide a long one. The sentence picker below keeps the
    longest, which is the bound. His current message, already in the transcript when
    this runs, is skipped; a gate's message back to me or a notice continues the turn.
    """
    from divineos.core.operating_loop.turn_extraction import _read_records

    path = Path(transcript_path)
    if not path.exists():
        return ""
    try:
        records = _read_records(path)
    except OSError:
        return ""
    parts: list[str] = []
    index = len(records)
    while index and records[index - 1][0] == "user":
        index -= 1  # his message that is being answered now
    for kind, text, _calls, _cmds in reversed(records[:index]):
        if kind == "user":
            if text.lstrip().lower().startswith(_NOT_HIM):
                continue
            break  # his previous message: the turn began here
        if text and text.strip():
            parts.append(text)
    return "\n".join(reversed(parts))[-_TURN_CHARS:]


def _is_gate_text(content: str) -> bool:
    opening = content[:_GATE_WINDOW].lower()
    return any(phrase in opening for phrase in _GATE_PHRASES)


def _last_shown_file() -> Path:
    from divineos.core.paths import divineos_home

    return Path(divineos_home()) / "own_words_last_shown.json"


def _read_showings() -> list[list[str]]:
    try:
        data = json.loads(_last_shown_file().read_text(encoding="utf-8"))
        return [list(showing) for showing in data][-SHOWINGS_REMEMBERED:]
    except (OSError, ValueError, TypeError):
        return []


def _read_last_shown() -> set[str]:
    return {item_id for showing in _read_showings() for item_id in showing}


def _write_last_shown(ids: set[str]) -> None:
    showings = _read_showings() + [sorted(ids)]
    try:
        _last_shown_file().write_text(json.dumps(showings[-SHOWINGS_REMEMBERED:]), encoding="utf-8")
    except OSError:
        pass  # the next turn then repeats a line; it never costs the reply


def own_words_block(transcript_path: str | Path | None, his_ids: set[str]) -> OwnWords:
    """What is close to what I said last turn, other than what his message already found.

    Nothing to say and could-not-run are different results on purpose: an empty block
    that is empty because the search broke must not look like one that found nothing.
    """
    if not transcript_path:
        return OwnWords()
    sentences = reply_sentences(last_reply_text(transcript_path))
    if not sentences:
        return OwnWords()

    from divineos.core import memory_linkage_retriever as retriever

    retriever._ensure_cache()
    previous = _read_last_shown()
    best: dict[str, tuple[float, retriever._CachedItem, str]] = {}
    vectors = [retriever._embed_topic(sentence) for sentence in sentences]
    if any(vector is None for vector in vectors):
        return OwnWords(could_not_run="the embedder did not run, so my own words were not searched")
    # One matrix product per source for all the sentences, not a Python loop per sentence
    # (Aether measured 0.77 s for the loop on the real cache; the product is a few hundredths).
    queries = np.stack(vectors)
    queries = queries / np.linalg.norm(queries, axis=1, keepdims=True)
    for source, items in retriever._EMBEDDING_CACHE.items():
        if not items:
            continue
        matrix = np.stack([item.embedding for item in items])
        matrix = matrix / np.linalg.norm(matrix, axis=1, keepdims=True)
        scores = queries @ matrix.T
        for row, sentence in enumerate(sentences):
            sims = scores[row].tolist()
            bar = retriever.threshold_for_target_k(sims, source, len(items))
            for item, sim in zip(items, sims, strict=True):
                if sim < bar or item.id in his_ids or item.id in previous:
                    continue
                if _is_gate_text(item.content):
                    continue
                if item.id not in best or best[item.id][0] < sim:
                    best[item.id] = (sim, item, sentence)

    # One text filed in two stores (a correction and its worklist row) is one line, not two:
    # two lines of the same words spend the whole block on a single page.
    top: list[tuple[float, retriever._CachedItem, str]] = []
    seen_texts: set[str] = set()
    for sim, item, sentence in sorted(best.values(), key=lambda entry: -entry[0]):
        squashed = " ".join(item.content.lower().split())[:120]
        if squashed in seen_texts:
            continue
        seen_texts.add(squashed)
        top.append((sim, item, sentence))
        if len(top) == MAX_LINES:
            break
    lines = []
    for sim, item, sentence in top:
        gist = " ".join(item.content.split())
        if len(gist) > _LINE_CHARS:
            gist = gist[:_LINE_CHARS].rstrip() + "..."
        where = f" ({item.path})" if item.path else ""
        # Which sentence of mine brought it, so the link can be read and not just trusted.
        cue = " ".join(sentence.split())[:_CUE_CHARS].rstrip()
        lines.append(f'- [{item.source}, {sim:.2f}] {gist}{where}  <- from "{cue}..."')
    shown = {item.id for _sim, item, _sentence in top}
    if shown:
        _write_last_shown(shown)
    return OwnWords(lines=lines, shown_ids=shown)
