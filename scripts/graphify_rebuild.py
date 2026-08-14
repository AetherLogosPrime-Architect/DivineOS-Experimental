"""Part A of the graphify build: deterministic AST extraction, no LLM.

The __main__ guard is load-bearing, not boilerplate. extract() defaults to
parallel=True, Windows multiprocessing uses spawn, and spawn re-imports the
main module in every worker. Without the guard each worker re-ran this script
and forked again -- seventeen "collected 4000 files" lines before it was
killed, still climbing.

Run with stdin closed. The graphify CLI blocked forever on a read that never
came in a shell with no terminal: CPU 0 across ten hours, working set 5.9MB,
the 31MB graph never loaded at all. The same missing guard is the likeliest
reason the CLI hung immediately after its AST phase.

Writes only to graphify-out/.graphify_ast.json -- the skill's documented
intermediate. graph.json is not touched here; merging is a later step, and
two runs today overwrote it before I understood what they did.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from graphify.extract import collect_files, extract


def main() -> None:
    t0 = time.time()
    files = collect_files(Path("."))
    print(f"collected {len(files)} files", flush=True)
    result = extract(files, cache_root=Path("."))
    out = Path("graphify-out/.graphify_ast.json")
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(
        f"AST: {len(result['nodes'])} nodes, {len(result['edges'])} edges "
        f"in {time.time() - t0:.0f}s",
        flush=True,
    )


if __name__ == "__main__":
    main()
