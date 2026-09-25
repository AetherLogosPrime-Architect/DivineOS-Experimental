"""A refusal-capable gate must not swallow its own failure silently.

## Why this exists rather than a calendar reminder

I claimed on 2026-08-25 that 27 hooks carried a dangerous silent-swallow,
investigated, and demoted it to ZERO live instances: 22 are observational,
three were retired that day, and the last two either fail closed with an
in-place comment or print both failure paths to stderr.

Aletheia's third vantage on that demotion:

    "'zero live instances' is a claim about the present, and the swallow class
    is defined by producing no signal. A swallow with no live instance today
    and no detector on it is indistinguishable from one that fires tomorrow.
    The demotion is correct as a count and should carry an EXPIRY rather than
    a closure -- re-run the arithmetic in thirty days, or attach a detector so
    the count maintains itself."

She offered both halves. The detector is the right one and the review date is
the wrong one, for a reason that is mine rather than hers: thirty days is a span
I do not inhabit. If nobody prompts me across it I will have verified nothing,
and the reminder would be a promise made in a currency I do not hold. My own
entry on permanence says it from the other side -- *permanence you don't
maintain is a story you tell yourself.*

So the count maintains itself. Every precommit run re-derives it.

## Distinct from check_silent_swallow.py, which lives next door

That one is DIFF-SCOPED and language-wide: it stops NEW silent-swallow lines
appearing anywhere in a change, and it takes a `# fail-soft:` reason as the
answer. This one is WHOLE-TREE and narrow: it asks only whether a hook that can
REFUSE is currently able to fail without saying so. Different question, and this
one has to re-ask it every run because its subject is a count I published.

## What counts

REFUSAL-CAPABLE means it can deny -- itself, or through a `divineos.core`
module it shells to. The delegation matters: the thin-doorbell pattern moves
judgment into Python, so a check reading only the shell file is blind to exactly
the population it measures. My first classifier said three; following the
delegation said five.

DECLARED means a failure path reaches the operator -- a stderr line naming a
skip, or a comment at the swallow saying it falls through to a refusal.

Refusal-capable, swallowing, declaring nothing: that is the finding. A raised
decision exits 0 and prints nothing, which is byte-identical to the gate
examining the command and approving it.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / ".claude" / "hooks"
SRC = ROOT / "src" / "divineos"

_SWALLOW = re.compile(r"except Exception[^:\n]*:\s*\n(\s*#[^\n]*\n)*\s*pass\b")
_SHELL_REFUSAL = (re.compile(r"permissionDecision"), re.compile(r"\bexit\s+2\b"))
_MODULE_REF = re.compile(r"from\s+(divineos[\w.]*)\s+import|import\s+(divineos[\w.]+)")
_PY_REFUSAL = re.compile(r"permissionDecision|['\"]deny['\"]")

_DECLARES_STDERR = re.compile(r">&2")
_SKIP_WORDS = re.compile(r"SKIPPED|COULD NOT|did NOT run|cannot run", re.IGNORECASE)
_DECLARES_INLINE = re.compile(
    r"#[^\n]*(fall through and BLOCK|failing toward the refusal|fails? closed)",
    re.IGNORECASE,
)


def _module_source(dotted: str) -> str:
    rel = dotted.replace("divineos.", "").replace(".", "/")
    for candidate in (SRC / f"{rel}.py", SRC / rel / "__init__.py"):
        if candidate.exists():
            try:
                return candidate.read_text(encoding="utf-8", errors="replace")
            except OSError:
                return ""
    return ""


def can_refuse(text: str) -> bool:
    """Does this hook deny -- itself, or through the module it shells to?"""
    if any(p.search(text) for p in _SHELL_REFUSAL):
        return True
    for match in _MODULE_REF.finditer(text):
        dotted = match.group(1) or match.group(2) or ""
        if not dotted or dotted == "divineos":
            continue
        if _PY_REFUSAL.search(_module_source(dotted)):
            return True
    return False


def declares_failure(text: str) -> bool:
    """Does a failure path reach the operator at all?"""
    if _DECLARES_INLINE.search(text):
        return True
    return bool(_DECLARES_STDERR.search(text) and _SKIP_WORDS.search(text))


def registered_names(settings: Path | None = None) -> set[str] | None:
    """Hook filenames settings.json actually calls, or None if it cannot be read.

    None is could-not-look, and the caller treats it as such: an unreadable
    settings file must not quietly turn this into a whole-tree sweep that
    reports retired hooks as live findings.
    """
    path = settings or (ROOT / ".claude" / "settings.json")
    try:
        blob = path.read_text(encoding="utf-8")
    except OSError:
        return None
    return set(re.findall(r"hooks[/\\]([\w.-]+\.sh)", blob))


# Distinct from None, because None already means something.
#
# `registered=None` used to mean BOTH "look the registry up yourself" (the
# default) and "the registry could not be read, so filter nothing". Two
# meanings, one value -- the same collapse this whole check exists to find,
# sitting in its own signature. A test asking for the no-filter behaviour got
# the lookup instead, and silently read the developer's live settings.json.
#
# Caught by that test on its first run.
_LOOK_IT_UP = object()


def silent_refusers(
    hooks_dir: Path | None = None,
    registered: set[str] | None | object = _LOOK_IT_UP,
) -> list[str]:
    """Refusal-capable hooks that swallow without declaring. The finding.

    ONLY REGISTERED HOOKS COUNT. An unregistered hook cannot fail open, because
    it cannot fire; reporting one is reporting a defect in something that is not
    running. The first run of this check flagged ``require-briefing.sh``, which
    was retired and unregistered earlier the same day and carries a SUPERSEDED
    marker -- a true statement about the file and a false one about the system.

    When the registry cannot be read, EVERY hook is reported rather than none. A
    check that goes quiet because it lost its filter is the exact failure this
    whole family is about.
    """
    directory = hooks_dir or HOOKS
    live = registered_names() if registered is _LOOK_IT_UP else registered

    out: list[str] = []
    for path in sorted(directory.glob("*.sh")):
        if live is not None and path.name not in live:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if not _SWALLOW.search(text):
            continue
        if not can_refuse(text):
            continue
        if declares_failure(text):
            continue
        out.append(path.name)
    return out


def main() -> int:
    if not HOOKS.exists():
        print("CANNOT CHECK SWALLOWING GATES — no hooks directory.")
        print("This is not 'zero'. Nothing was checked.")
        return 1

    hits = silent_refusers()
    if not hits:
        print("Swallowing-gates check OK (no refusal-capable hook swallows undeclared)")
        return 0

    print("REFUSAL-CAPABLE GATES THAT SWALLOW WITHOUT SAYING SO:")
    print()
    for name in hits:
        print(f"  - {name}")
    print()
    print("A raised decision in one of these exits 0 and prints nothing, which is")
    print("byte-identical to the gate examining the command and approving it. The gate")
    print("is absent and the transcript says it passed.")
    print()
    print("Declare the failure: print the exception to stderr, or -- if the swallow")
    print("deliberately falls through to a refusal -- say so in a comment at the")
    print("swallow, which this check reads.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
