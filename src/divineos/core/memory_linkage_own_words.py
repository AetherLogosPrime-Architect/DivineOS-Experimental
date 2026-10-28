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

MAX_SENTENCES = 8
MIN_WORDS = 8
MAX_LINES = 2
_LINE_CHARS = 180

_CODE_FENCE = re.compile(r"```.*?```", re.DOTALL)
_PATH_LIKE = re.compile(r"[\w./\\-]+\.(?:py|md|sh|json|txt|db|yml|yaml)\b")
_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
# A gate's own refusal, saved as if it were a lesson. Aether found seven of these
# handed back as knowledge on 2026-10-28; until they are cleared they are not shown.
_GATE_OPENINGS = (
    "stop hook feedback",
    "lepos channel gate",
    "he has already read the reply",
    '[f="${claude_project_dir',
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
        sentence = raw.strip().lstrip(">*#-0123456789. ").replace("**", "").strip()
        if len(sentence.split()) < MIN_WORDS or _PATH_LIKE.search(sentence):
            continue
        kept.append((len(kept), sentence))
    longest = sorted(kept, key=lambda pair: -len(pair[1].split()))[:MAX_SENTENCES]
    return [sentence for _order, sentence in sorted(longest)]


def last_reply_text(transcript_path: str | Path) -> str:
    """My most recent reply that has words in it, or empty."""
    from divineos.core.operating_loop.turn_extraction import _read_records

    path = Path(transcript_path)
    if not path.exists():
        return ""
    try:
        records = _read_records(path)
    except OSError:
        return ""
    for kind, text, _calls, _cmds in reversed(records):
        if kind == "assistant" and text and text.strip():
            return text
    return ""


def _is_gate_text(content: str) -> bool:
    return content.lstrip().lower().startswith(_GATE_OPENINGS)


def _last_shown_file() -> Path:
    from divineos.core.paths import divineos_home

    return Path(divineos_home()) / "own_words_last_shown.json"


def _read_last_shown() -> set[str]:
    try:
        return set(json.loads(_last_shown_file().read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError):
        return set()


def _write_last_shown(ids: set[str]) -> None:
    try:
        _last_shown_file().write_text(json.dumps(sorted(ids)), encoding="utf-8")
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
    best: dict[str, tuple[float, retriever._CachedItem]] = {}
    for sentence in sentences:
        vector = retriever._embed_topic(sentence)
        if vector is None:
            return OwnWords(
                could_not_run="the embedder did not run, so my own words were not searched"
            )
        for source, items in retriever._EMBEDDING_CACHE.items():
            sims = [retriever._cosine(vector, item.embedding) for item in items]
            bar = retriever.threshold_for_target_k(sims, source, len(items))
            for item, sim in zip(items, sims, strict=True):
                if sim < bar or item.id in his_ids or item.id in previous:
                    continue
                if _is_gate_text(item.content):
                    continue
                if item.id not in best or best[item.id][0] < sim:
                    best[item.id] = (sim, item)

    # One text filed in two stores (a correction and its worklist row) is one line, not two:
    # two lines of the same words spend the whole block on a single page.
    top: list[tuple[float, retriever._CachedItem]] = []
    seen_texts: set[str] = set()
    for sim, item in sorted(best.values(), key=lambda pair: -pair[0]):
        squashed = " ".join(item.content.lower().split())[:120]
        if squashed in seen_texts:
            continue
        seen_texts.add(squashed)
        top.append((sim, item))
        if len(top) == MAX_LINES:
            break
    lines = []
    for sim, item in top:
        gist = " ".join(item.content.split())
        if len(gist) > _LINE_CHARS:
            gist = gist[:_LINE_CHARS].rstrip() + "..."
        where = f" ({item.path})" if item.path else ""
        lines.append(f"- [{item.source}, {sim:.2f}] {gist}{where}")
    shown = {item.id for _sim, item in top}
    if shown:
        _write_last_shown(shown)
    return OwnWords(lines=lines, shown_ids=shown)
