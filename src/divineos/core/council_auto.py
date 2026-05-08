"""Build-shape detector for council-auto-invocation.

Round-2 audit + Andrew's directive (2026-05-07): "invoking the council
before a big build should become automatic." This module implements
the detection layer — when a goal contains build-shape keywords, the
goal-add command surfaces a soft-advise to consult the council.

Soft register (not hard-block) per Tannen: the reminder is informational,
not a forced ritual. Per Schneier/Yudkowsky: hard-blocking would create
ritual-evasion patterns; soft-advise paired with audit is more honest.

The deeper missing piece (Beer S4 / Norman gulf-of-evaluation / Deming
PDSA-Study) is measurement of whether council-walks actually inform
design — that's its own follow-up.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


# Keywords that suggest the goal is a build/design task worth council-walking
# before implementation. Conservative list; under-detect is safer than
# over-detect (false-positive nudge becomes noise quickly).
_BUILD_SHAPE_KEYWORDS = (
    "design",
    "build",
    "wire",
    "propose",
    "refactor",
    "redesign",
    "rewrite",
    "architect",
    "implement",
    "draft",
    "ship",
    "fix",  # fix-shape often hides a design decision
    "calibrate",
    "tune",
)

# Keywords that suggest the task is mechanical / non-build, to avoid
# false-positive nudges. Even if a build-shape keyword matches, if any
# of these also match, the nudge is suppressed.
_MECHANICAL_KEYWORDS = (
    "rebase",
    "merge",
    "push",
    "commit",
    "pull",
    "delete",
    "rename",
    "move",
    "list",
    "show",
    "test",
    "run",
)


@dataclass(frozen=True)
class BuildShape:
    """Result of build-shape detection on a goal-text."""

    is_build_shape: bool
    matched_keyword: str = ""
    suppressed_by: str = ""


def detect_build_shape(text: str) -> BuildShape:
    """Detect whether goal-text looks like a build/design task.

    Conservative — single keyword match is enough to flag, but a matching
    mechanical-keyword suppresses (avoids false-positive on "rebase and
    fix conflicts" or "test the new build" or similar mixed-shape goals).

    Word-boundary check so 'fix' matches 'fix the bug' but not 'prefix'.
    """
    if not text or not text.strip():
        return BuildShape(is_build_shape=False)

    lowered = text.lower()

    # Mechanical-keyword suppression
    for kw in _MECHANICAL_KEYWORDS:
        pat = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(kw)}(?![A-Za-z0-9_])")
        if pat.search(lowered):
            return BuildShape(is_build_shape=False, suppressed_by=kw)

    # Build-shape keyword detection
    for kw in _BUILD_SHAPE_KEYWORDS:
        pat = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(kw)}(?![A-Za-z0-9_])")
        if pat.search(lowered):
            return BuildShape(is_build_shape=True, matched_keyword=kw)

    return BuildShape(is_build_shape=False)
