"""How much of what arrives on his turns is him, and how much is the house.

For each of his typed prompts in this session: his characters, versus the
characters of hook output attached to that same prompt (records sharing the
prompt's parent chain until the next assistant message).
"""

import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
recs = [json.loads(line) for line in path.open(encoding="utf-8", errors="replace") if line.strip()]

rows = []
i = 0
while i < len(recs):
    r = recs[i]
    m = r.get("message") or {}
    if (
        r.get("type") == "user"
        and not r.get("isMeta")
        and r.get("entrypoint")
        and isinstance(m.get("content"), str)
        and not m["content"].lstrip().startswith("<")
    ):
        his = len(m["content"])
        house = 0
        j = i + 1
        while j < len(recs) and recs[j].get("type") != "assistant":
            s = json.dumps(recs[j], ensure_ascii=False)
            if "hook" in s.lower():
                house += len(s)
            j += 1
        # hook output may also precede the prompt record
        k = i - 1
        while k >= 0 and recs[k].get("type") != "assistant":
            s = json.dumps(recs[k], ensure_ascii=False)
            if "hook" in s.lower():
                house += len(s)
            k -= 1
        rows.append(
            (r.get("timestamp", "")[11:16], his, house, m["content"][:50].replace("\n", " "))
        )
    i += 1

print("probe check - rows found:", len(rows))
for t, h, x, s in rows[-12:]:
    share = h / (h + x) if (h + x) else 0
    print(f"{t}  his={h:>5}  house={x:>7}  his share={share:6.1%}  | {s}")
