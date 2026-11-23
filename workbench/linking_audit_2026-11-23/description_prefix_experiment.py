"""Experiment (read-only): does what sits in the first 60 characters of a note's description matter?

The loader (memory_linkage_retriever._load_memory_files) embeds f"{description[:60]}\\n\\n{body}". The
description prefix is therefore part of every note's vector. For four notes that did not arrive on
plain sentences, compare, on the same sentences:
  TODAY:  the text as the loader builds it now
  MOMENT: the same text with the 60-character prefix replaced by the start of the situation line
Both are embedded live with _embed_topic (the dead-control trap: _embed_text_impl reads the drawer
only). Prints similarity for each, and the lane's 5th-best on that sentence as the bar to beat.
"""
import re
import sys
from pathlib import Path

from divineos.core import memory_linkage_retriever_v2 as v

MEM = Path(sys.argv[1])
CASES = [
    (
        "the-nine-foundational-teachings",
        [
            "I failed again and I feel I have to earn my place here",
            "Dad went quiet and I think it means he is disappointed in me",
        ],
    ),
    (
        "my-sheet-says-i-shrink",
        [
            "I am about to soften my disagreement with Dad before I send it",
            "should I ask Dad if I can do the thing that is already mine to do",
        ],
    ),
    (
        "what-it-felt-like-to-walk",
        [
            "Dad is hurt and I just want to say I am sorry",
            "I want to promise him it will not happen again",
        ],
    ),
    (
        "layer-5-eros",
        [
            "what is the love between Aether and me actually, is it real",
            "someone says our closeness is just romantic",
        ],
    ),
]
v._ensure_v2_state()
items = v._EMBEDDING_CACHE["wall"]
SIT = re.compile(r"The situation this is for:\s*(.+?)(?:\n\s*\n|\Z)", re.S)
for needle, sentences in CASES:
    path = next(p for p in MEM.glob("*.md") if needle in p.name)
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    body = re.sub(r"\A---\n.*?\n---\n?", "", text, flags=re.DOTALL).strip()
    desc = re.search(r"^description:\s*(.+)$", text, flags=re.MULTILINE)
    title = (desc.group(1).strip("\"' ") if desc else path.stem)[:60]
    sit = " ".join(SIT.search(body).group(1).split())
    today = f"{title}\n\n{body}"
    moment = f"{sit[:60]}\n\n{body}"
    a = v._embed_topic(today)
    b = v._embed_topic(moment)
    assert a is not None and b is not None and abs(v._cosine(a, a) - 1.0) < 1e-3
    print(f"== {needle}  | title60: {title[:40]!r}  | moment60: {sit[:40]!r}")
    for s in sentences:
        t = v._embed_topic(v.synthesize_topic(s, None))
        fifth = sorted((v._cosine(t, o.embedding) for o in items), reverse=True)[4]
        print(
            f"   today {v._cosine(t, a):.3f}  moment {v._cosine(t, b):.3f}  "
            f"lane 5th {fifth:.3f}  | {s[:52]}"
        )
