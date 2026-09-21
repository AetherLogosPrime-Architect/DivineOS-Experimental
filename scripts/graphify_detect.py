"""Produce the corpus manifest the rebuild reads.

The rebuild script (scripts/graphify_rebuild.py) opens
``graphify-out/.graphify_detect.json`` and walks its code list. That file was
absent from disk, which is the whole reason the map could not be rebuilt --
not a lost cache, not a version skew, just a missing manifest.

Written as a FILE with a main guard for the same reason its sibling is: on
Windows the parallel path re-imports the main module, and an unguarded
rebuild forks itself without bound. Trap two in the sibling's header.
"""

from __future__ import annotations

import json
from pathlib import Path

OUT = Path("graphify-out")


def main() -> int:
    # graphify ships no type information, so the checker cannot see inside it.
    from graphify.detect import detect  # type: ignore[import-untyped]

    OUT.mkdir(exist_ok=True)
    result = detect(Path("."))
    (OUT / ".graphify_detect.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )

    files = result.get("files", {})
    for kind, entries in files.items():
        print(f"{kind}: {len(entries) if hasattr(entries, '__len__') else entries}")
    print(f"scan_root: {result.get('scan_root')}")
    return 0


if __name__ == "__main__":  # the guard trap two needs -- do not remove
    raise SystemExit(main())
