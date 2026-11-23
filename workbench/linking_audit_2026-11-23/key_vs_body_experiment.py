"""Experiment (read-only): match the SITUATION line (the trigger I wrote) or the whole note?

For every memory note that has a situation line and carries one of Dad's italic quotes,
query the wall lane with that quote, twice:
  BODY: every note represented by its whole stored vector (how the link works today).
  KEY:  every memory note that has a situation line represented by the live embedding of
        that line alone; every other wall item unchanged.
Reports, for the quoted note, rank and whether it clears the lane bar, under each.
The quote is a sentence of Dad's that sits inside the note, so it is not independent of
the note, but it is not the situation line either: it asks whether the situation line
captures what Dad's own words call for.
"""
import json
import re
import sys

from divineos.core import memory_linkage_retriever_v2 as v

OUT = sys.argv[1]
v._ensure_v2_state()
items = v._EMBEDDING_CACHE["wall"]
SIT = re.compile(r"The situation this is for:\s*(.+?)(?:\n\s*\n|\Z)", re.S)
Q = re.compile(r'\*"([^"\n]{60,300})"\*')

key_vec = {}
for idx, it in enumerate(items):
    if not str(it.id).startswith("memory-"):
        continue
    m = SIT.search(it.content)
    if m:
        vec = v._embed_topic(" ".join(m.group(1).split()))
        if vec is not None:
            key_vec[idx] = vec

body = [it.embedding for it in items]
key = [key_vec.get(i, it.embedding) for i, it in enumerate(items)]
rows = []
for idx, it in enumerate(items):
    if idx not in key_vec:
        continue
    q = Q.search(it.content)
    if not q:
        continue
    topic = v._embed_topic(v.synthesize_topic(q.group(1), None))
    res = {"id": str(it.id)}
    for name, vecs in (("body", body), ("key", key)):
        sims = [v._cosine(topic, e) for e in vecs]
        bar = v.threshold_for_target_k(sims, "wall", len(items))
        order = sorted(range(len(items)), key=lambda i: sims[i], reverse=True)
        res[name] = {
            "rank": order.index(idx) + 1,
            "sim": round(sims[idx], 3),
            "bar": round(bar, 3),
            "passed": sims[idx] >= bar,
        }
    rows.append(res)

json.dump({"rows": rows}, open(OUT, "w"), indent=1)


def summary(name):
    r = [x[name] for x in rows]
    first = sum(1 for x in r if x["rank"] == 1)
    top5 = sum(1 for x in r if x["rank"] <= 5)
    passed = sum(1 for x in r if x["passed"])
    return f"{name}: n={len(r)} first={first} top5={top5} passed={passed}"


print(summary("body"))
print(summary("key"))
better = sum(1 for x in rows if x["key"]["rank"] < x["body"]["rank"])
worse = sum(1 for x in rows if x["key"]["rank"] > x["body"]["rank"])
print("key ranks the note higher:", better, "lower:", worse, "same:", len(rows) - better - worse)
