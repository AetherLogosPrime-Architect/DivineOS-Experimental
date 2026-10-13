"""How much of the paid half of the map is already bought?

Structural extraction is deterministic and free. The semantic pass costs
money, and graphify caches it by content hash. So before any rebuild the
answerable question is not "is the cache big" but "how many of the files we
would send today actually hit it".

Andrew 2026-09-07 believed the spend was lost. This is the instrument that
says whether it was, rather than either of us guessing.
"""

from __future__ import annotations

import json
from pathlib import Path

OUT = Path("graphify-out")


def main() -> int:
    # graphify ships no type information, so the checker cannot see inside it.
    from graphify.cache import check_semantic_cache  # type: ignore[import-untyped]

    detect = json.loads((OUT / ".graphify_detect.json").read_text(encoding="utf-8"))
    files = detect.get("files", {})

    # Only non-code goes to the paid pass; code is covered structurally.
    content: list[str] = []
    for kind in ("document", "paper", "image"):
        content.extend(str(p) for p in files.get(kind, []))

    if not content:
        print("no content files in the manifest -- nothing to price")
        return 0

    cached_nodes, cached_edges, _hyper, uncached = check_semantic_cache(content, root=".")
    hits = len(content) - len(uncached)
    print(f"content files in corpus : {len(content)}")
    print(f"already extracted (free): {hits}  ({hits * 100 // len(content)}%)")
    print(f"would need paying for   : {len(uncached)}")
    print(f"nodes recoverable from cache: {len(cached_nodes)}")
    print(f"edges recoverable from cache: {len(cached_edges)}")
    for miss in uncached[:8]:
        print("  uncached:", Path(miss).name)
    return 0


if __name__ == "__main__":  # the spawn guard its siblings need
    raise SystemExit(main())
