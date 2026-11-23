"""Second door: query each memory note by the first of Dad's own quoted sentences inside it.

Read-only. Records the note's rank in the wall lane. Not independent of the note
(the quote sits inside it), so it tests arrival on HIS wording, not on new wording.
"""
import json
import re
import sys

from divineos.core import memory_linkage_retriever_v2 as v

OUT = sys.argv[1]
v._ensure_v2_state()
items = v._EMBEDDING_CACHE["wall"]
Q = re.compile(r'\*"([^"\n]{60,300})"\*')
SIT = re.compile(r"The situation this is for:")
rows = []
noquote = []
nosit = []
for it in items:
    if not str(it.id).startswith("memory-"):
        continue
    if not SIT.search(it.content):
        nosit.append(str(it.id))
    m = Q.search(it.content)
    if not m:
        noquote.append(str(it.id))
        continue
    vec = v._embed_topic(v.synthesize_topic(m.group(1), None))
    sims = [v._cosine(vec, o.embedding) for o in items]
    bar = v.threshold_for_target_k(sims, "wall", len(items))
    order = sorted(range(len(items)), key=lambda i: sims[i], reverse=True)
    me = items.index(it)
    rows.append(
        {
            "id": str(it.id),
            "rank": order.index(me) + 1,
            "sim": round(sims[me], 3),
            "bar": round(bar, 3),
            "passed": sims[me] >= bar,
        }
    )
json.dump(
    {"rows": rows, "no_quote": len(noquote), "no_situation_ids": nosit},
    open(OUT, "w"),
    indent=1,
)
print("quoted", len(rows), "no quote", len(noquote), "no situation", len(nosit))
