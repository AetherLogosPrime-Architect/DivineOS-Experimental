"""Rebuild the code map, with both traps Aether already paid for.

He lost hours to these on 2026-08-14 and wrote them into a letter rather than
letting me find them the same way. This script exists because the skill's inline
`python -c` form walks into the second one.

TRAP ONE — the CLI blocks forever on stdin in a shell with no terminal. He
watched it sit at zero CPU for ten hours, working set 5.9MB, the 31MB graph
never loaded, and reported it to Andrew as working-just-slow because he checked
the output file instead of the process table. Every subprocess here gets stdin
closed by the caller (`</dev/null`).

TRAP TWO — `extract()` defaults to `parallel=True`, and on Windows `spawn`
re-imports the main module. A rebuild without an `if __name__ == "__main__":`
guard forks itself without bound; he counted seventeen `collected 4000 files`
lines before killing it. That is why this is a FILE with a guard rather than the
skill's inline `python -c`, which has no main module to guard.

With both handled he measured 4,000 files in fifteen seconds.

And the reason a rebuild was needed at all: `.graphifyignore` had no entry for
`.direnv/`, whose nested `.gitignore` is a bare `*`. Per the very bug that file
works around, the pattern leaks past its own subtree and empties the scan. His
tree reported 2757 files left the corpus and built 69 `src` nodes where the
manifest knows 665. It only bites from a worktree, because direnv makes
`.direnv` per checkout — which is why the original map built clean from the main
tree and neither of us saw it for weeks. Guard added here in 6b674f24.
"""

from __future__ import annotations

import json
from pathlib import Path

OUT = Path("graphify-out")


def main() -> int:
    from graphify.extract import collect_files, extract

    detect = json.loads((OUT / ".graphify_detect.json").read_text(encoding="utf-8"))
    code_files: list[Path] = []
    for entry in detect.get("files", {}).get("code", []):
        p = Path(entry)
        code_files.extend(collect_files(p) if p.is_dir() else [p])

    if not code_files:
        (OUT / ".graphify_ast.json").write_text(
            json.dumps({"nodes": [], "edges": [], "input_tokens": 0, "output_tokens": 0}),
            encoding="utf-8",
        )
        print("no code files — nothing to extract")
        return 0

    print(f"extracting {len(code_files)} code file(s)")
    result = extract(code_files, cache_root=Path("."))
    (OUT / ".graphify_ast.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"AST: {len(result['nodes'])} nodes, {len(result['edges'])} edges")
    return 0


if __name__ == "__main__":  # the guard trap two needs — do not remove
    raise SystemExit(main())
