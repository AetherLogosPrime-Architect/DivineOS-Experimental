#!/usr/bin/env python3
"""Pipe: stdin payload -> the decision in core -> stdout. No logic here.

The decision lives in ``divineos.core.unmeasured_quantity`` so tests can reach
it. This file exists only because a hook is spawned with a JSON payload on
stdin and has to put the repository on the path before it can import anything.

Pre-registration: prereg-34b60b20bf36.
Draft: docs/drafts/unmeasured_quantity_gate_draft_2026-09-11.md.

Every failure path here prints COULD NOT CHECK rather than staying quiet. A
silent hook and a clean reply look identical from the outside, and that
equivalence is the fault this whole build exists to remove.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

_BLIND = "  This reply is UNCHECKED rather than clean. Silence here is not a pass."


def main() -> int:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw or "{}")
    except (ValueError, TypeError):
        print("[unmeasured-quantity] COULD NOT CHECK -- the hook payload was not readable JSON.")
        print(_BLIND)
        return 0

    try:
        from divineos.core.unmeasured_quantity import check_payload, render
    except ImportError as exc:
        print(f"[unmeasured-quantity] COULD NOT CHECK -- the checker did not import: {exc}")
        print(_BLIND)
        return 0

    out = render(check_payload(payload))
    if out:
        print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
