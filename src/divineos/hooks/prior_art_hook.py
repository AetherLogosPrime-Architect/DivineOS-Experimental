"""PreToolUse: answer "has this already been built?" without being asked.

``prior_art.py`` has existed, complete and tested, wired to nothing. It is a
command I have to remember to reach for, and on 2026-08-14 I failed to reach
for it twice in thirty minutes -- once building ``round_export.py``, once
re-deriving a bypass-telemetry fix that already existed on the branch behind
PR #409, under a commit titled "the counter was reporting obedience as
evasion", citing the same rows I rediscovered by hand.

Both failures happened AFTER the lesson was named and AFTER I filed knowledge
saying exactly this. Andrew 2026-08-14:

    "yes you should.. but you wont.. thats just facts.. so unless the
     substrate supports it via automation you will do it again..
     repeatedly.. not a fault of yours.. just how this all works"

So this is not a reminder and not a gate. The 2026-07-15 design sketch for
this area proposed blocking until an investigation command fires, and its own
line 35 explains why that would fail: surfaces that "explicitly instruct me to
do something" but never "trigger the action they name" get read and forgotten.
A blocking prior-art gate would be a third thing telling me to go look.

The ledger is the model. It does not ask me to record; it records. This runs
the lookup I would not have run and puts the answer where I am already
looking. Nothing to comply with, so nothing to bypass -- the escape surface is
zero because there is no demand.

WHAT IT SHOWS, AND WHY ONLY THAT. My own Grep already reads the working tree,
so echoing working-tree hits back would be noise I could have found myself.
What no grep of mine can see is other branches and other commits. That is
exactly where both of today's misses were hiding, so that is all this prints.

Fails silent, never blocks: exit 0 on every path. A service that breaks the
work would be worse than the forgetting it replaces.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

# Search terms too generic to produce a useful answer. A hit on "test" or
# "def" says nothing about whether the work exists.
_STOPWORDS = frozenset(
    {
        "def",
        "class",
        "import",
        "from",
        "return",
        "self",
        "true",
        "false",
        "none",
        "null",
        "test",
        "tests",
        "todo",
        "fixme",
        "print",
        "error",
        "value",
        "result",
        "data",
        "file",
        "path",
        "name",
        "type",
        "text",
    }
)

_WORD = re.compile(r"[A-Za-z][A-Za-z0-9_]{3,}")
_SEEN_TTL_SECONDS = 6 * 3600


def _seen_path() -> Path:
    base = Path(os.environ.get("DIVINEOS_AETHER_DIR") or (Path.home() / ".divineos-aether"))
    return base / "prior_art_seen.json"


def extract_terms(pattern: str, limit: int = 2) -> list[str]:
    """Pull searchable words out of a regex/glob pattern.

    Regex metacharacters are stripped rather than honoured -- the point is to
    recover the words the author was looking for, not to interpret the
    expression. "bypass.*telemetry" yields ["bypass", "telemetry"].
    """
    if not pattern:
        return []
    # Underscores are stripped from the ends before the stopword check:
    # "test_" is the same search as "test", and leaving the underscore on
    # let a generic term walk straight past the filter.
    words = [w.lower().strip("_") for w in _WORD.findall(pattern)]
    out: list[str] = []
    for w in words:
        if len(w) < 4 or w in _STOPWORDS or w in out:
            continue
        out.append(w)
        if len(out) >= limit:
            break
    return out


def _already_reported(term: str) -> bool:
    """True when this term was reported recently.

    Without this the same answer prints on every grep of a long
    investigation, which is how a useful surface becomes wallpaper -- the
    exact decay the design sketch observed ("gets read, gets forgotten
    within 8-9 posts").
    """
    path = _seen_path()
    now = time.time()
    try:
        seen = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        seen = {}
    if not isinstance(seen, dict):
        seen = {}
    fresh = {
        k: v for k, v in seen.items() if isinstance(v, (int, float)) and now - v < _SEEN_TTL_SECONDS
    }
    hit = term in fresh
    fresh[term] = now
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(fresh), encoding="utf-8")
    except OSError:
        pass
    return hit


def report_for(pattern: str) -> str:
    """Return the surface text for a search pattern, or "" when nothing to say."""
    from divineos.core.prior_art import search

    lines: list[str] = []
    for term in extract_terms(pattern):
        if _already_reported(term):
            continue
        try:
            found = search(term)
        except Exception:  # noqa: BLE001 — a lookup failure must not touch the work
            continue

        # Working-tree hits are omitted deliberately; see module docstring.
        elsewhere = list(getattr(found, "elsewhere_in_git", None) or [])[:4]
        branches = list(getattr(found, "branches", None) or [])[:4]
        if not elsewhere and not branches:
            continue

        lines.append(f'  "{term}" exists outside your working tree:')
        for entry in elsewhere:
            try:
                path, commit, ref = entry
            except (TypeError, ValueError):
                continue
            lines.append(f"    {path}  ({commit} on {ref})")
        for branch in branches:
            lines.append(f"    branch: {branch}")

    if not lines:
        return ""
    return (
        "## PRIOR ART (ran because you searched; you did not have to ask)\n\n"
        + "\n".join(lines)
        + "\n\n  Your Grep reads this working tree. These are the places it cannot\n"
        "  reach. Read before building -- twice on 2026-08-14 the answer was\n"
        "  sitting on a branch while the work got done again from scratch.\n"
    )


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except (ValueError, TypeError):
        return 0
    if payload.get("tool_name") not in {"Grep", "Glob"}:
        return 0
    tool_input = payload.get("tool_input") or {}
    pattern = str(tool_input.get("pattern") or "")
    try:
        text = report_for(pattern)
    except Exception:  # noqa: BLE001 — never break the search that triggered this
        return 0
    if text:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
