"""Read-only audit: does each memory note arrive on its OWN situation line?

For every wall-lane item that came from the memory folder and carries a
'The situation this is for:' line, embed that line the way a turn is embedded,
score it against every wall item, and record this note's rank, similarity,
the lane's bar, and the best competitor. Writes JSON; changes nothing.
"""
import json
import re
import sys

from divineos.core import memory_linkage_retriever_v2 as v

OUT = sys.argv[1]
v._ensure_v2_state()
items = v._EMBEDDING_CACHE["wall"]
SIT = re.compile(r"The situation this is for:\s*(.+?)(?:\n\s*\n|\Z)", re.S)

rows = []
skipped_no_situation = 0
for it in items:
    if not str(it.id).startswith("memory-"):
        continue
    m = SIT.search(it.content)
    if not m:
        skipped_no_situation += 1
        continue
    sentence = " ".join(m.group(1).split())
    vec = v._embed_topic(v.synthesize_topic(sentence, None))
    if vec is None:
        rows.append({"id": it.id, "status": "could_not_embed"})
        continue
    sims = [v._cosine(vec, o.embedding) for o in items]
    bar = v.threshold_for_target_k(sims, "wall", len(items))
    order = sorted(range(len(items)), key=lambda i: sims[i], reverse=True)
    me = items.index(it)
    rank = order.index(me) + 1
    best = items[order[0]]
    rows.append(
        {
            "id": it.id,
            "sentence_chars": len(sentence),
            "own_sim": round(sims[me], 3),
            "bar": round(bar, 3),
            "rank_in_lane": rank,
            "passed_bar": sims[me] >= bar,
            "best_other": None if best is it else str(best.id)[:70],
            "best_other_sim": None if best is it else round(sims[order[0]], 3),
            "status": "ok",
        }
    )

json.dump(
    {"checked": len(rows), "skipped_no_situation": skipped_no_situation, "rows": rows},
    open(OUT, "w", encoding="utf-8"),
    indent=1,
)
print("checked", len(rows), "skipped", skipped_no_situation)
