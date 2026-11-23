"""Probe one memory note against sentences I would really say. Read-only.

usage: probe_note.py <note-id-substring> <sentence> [<sentence> ...]
Prints, per sentence: the note's similarity, its rank in the wall lane, the lane bar,
and whether it REACHES the turn (passes its lane bar AND is within the cross-lane cap).
A control sentence unrelated to the note should show it NOT reaching.
"""
import sys

from divineos.core import memory_linkage_retriever_v2 as v

needle = sys.argv[1]
v._ensure_v2_state()
items = v._EMBEDDING_CACHE["wall"]
hits = [it for it in items if needle in str(it.id)]
if len(hits) != 1:
    print("need exactly one note, matched", [str(h.id) for h in hits])
    sys.exit(1)
me = hits[0]
for sentence in sys.argv[2:]:
    out = v.explain_turn(sentence, near_misses=0)
    vec = v._embed_topic(v.synthesize_topic(sentence, None))
    sims = [v._cosine(vec, o.embedding) for o in items]
    bar = v.threshold_for_target_k(sims, "wall", len(items))
    order = sorted(range(len(items)), key=lambda i: sims[i], reverse=True)
    rank = order.index(items.index(me)) + 1
    reached = None
    for entry in out:
        for row in entry["rows"]:
            if row["id"] == me.id:
                reached = {k: row.get(k) for k in ("passed", "reaches", "surfaced") if k in row}
    print(
        f"sim {sims[items.index(me)]:.3f} bar {bar:.3f} rank {rank:>3} reach {reached} | "
        f"{sentence[:90]}"
    )
