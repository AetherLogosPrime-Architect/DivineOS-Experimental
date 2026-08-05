"""Every remedy a gate prescribes must itself be reachable.

Three deadlocks, one shape:

    2026-07-17  the goal gate blocked tool use, prescribed `divineos goal add`,
                and the CLI refused `goal` without briefing while the gate
                blocked briefing. Fixed by hand: added "goal".

    2026-08-05  the compass gate blocked tool use, prescribed `compass-ops
                observe` / `compass-ops dismiss`, and BOTH were briefing-gated
                while briefing was compass-gated. Verified circular in both
                directions; even the edit that would fix it was blocked by the
                same gate. Fixed by hand: added "compass-ops", "compass".

    2026-08-05  the correction-marker gate blocked tool use, prescribed
                `divineos learn` as remedy (a), and `learn` was briefing-gated
                while briefing was marker-gated. Of its three prescribed
                remedies only (b) `correction` was reachable. Fixed by hand:
                added "learn".

Andrew, after the third: *"once you find the proper shape and you can build the
automation to do it beforehand.. that is the real fix.. what is already broken
may need fixed manually but it stops the problem from re-ocurring."*

Hand-patching the bypass list is foot patrol -- three walks of the same border,
three posts driven one at a time, nothing preventing a fourth. This test is the
fence: it derives prescribed remedies from what the gates ACTUALLY SAY and
fails when one is not exempt. A gate can no longer name a command the system
refuses, because the assertion reads the denial messages rather than a
hand-list someone must remember to update.

## What this does NOT cover, stated so silence is not read as coverage

It finds remedies written as `divineos <subcommand>` in text that also carries
block/remedy language. It will miss a gate that phrases its remedy differently
or builds the command string dynamically. A passing run means "no *detectable*
prescribed remedy is blocked" -- not "no deadlock is possible". The third word
applies to this test as much as to anything it guards.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from divineos.cli import _BYPASS_COMMANDS

REPO = Path(__file__).resolve().parent.parent

# Where gates live and speak.
_SEARCH_ROOTS = (
    REPO / "src" / "divineos" / "hooks",
    REPO / "src" / "divineos" / "cli" / "__init__.py",
    REPO / ".claude" / "hooks",
)

# A line is remedy-bearing if it tells the reader to run something in the
# context of a refusal. Deliberately broad on the cue and narrow on the
# extraction: over-matching a cue costs a false finding I can inspect,
# under-matching costs a deadlock nobody sees until it bites.
_REMEDY_CUE = re.compile(r"BLOCKED|Run:|run:|Fix:|remedy|prescrib", re.IGNORECASE)
_INVOCATION = re.compile(r"divineos\s+([a-z][a-z0-9-]{2,})\b")

# Appear inside remedy text without being the remedy themselves.
_NOT_A_REMEDY = frozenset({"help", "init"})


def _iter_source_files():
    for root in _SEARCH_ROOTS:
        if root.is_file():
            yield root
        elif root.is_dir():
            for p in sorted(root.rglob("*")):
                if p.suffix in {".py", ".sh"} and p.is_file():
                    yield p


def collect_prescribed_remedies() -> dict[str, set[str]]:
    """Map subcommand -> set of files whose refusal text prescribes it."""
    found: dict[str, set[str]] = {}
    for path in _iter_source_files():
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line in text.splitlines():
            stripped = line.lstrip()
            # Skip comments. The first run flagged three false positives --
            # `command`, `substrate-consult`, `check-branch` -- all from `#`
            # comments and prose describing gates rather than from denial
            # messages. A comment mentioning a command is not a gate
            # prescribing it, and treating it as one would push me to exempt
            # commands no gate actually demands.
            if stripped.startswith("#"):
                continue
            if not _REMEDY_CUE.search(line):
                continue
            for sub in _INVOCATION.findall(line):
                if sub in _NOT_A_REMEDY:
                    continue
                found.setdefault(sub, set()).add(str(path.relative_to(REPO)))
    return found


def test_every_prescribed_remedy_is_bypass_exempt():
    """A gate must never prescribe a command another gate refuses.

    If this fails, do NOT add the command to _BYPASS_COMMANDS just to make it
    green. Read why first: either the remedy genuinely needs exemption (add it,
    and this test now guards it) or the gate is prescribing something it should
    not (fix the message).
    """
    prescribed = collect_prescribed_remedies()
    assert prescribed, "found no prescribed remedies at all -- the scanner is broken, not the gates"

    unreachable = {
        sub: sorted(files) for sub, files in prescribed.items() if sub not in _BYPASS_COMMANDS
    }

    if unreachable:
        lines = [
            "Gate(s) prescribe a remedy the briefing gate refuses.",
            "This is the deadlock shape that cost three hand-patches:",
            "",
        ]
        for sub, files in sorted(unreachable.items()):
            lines.append(f"  divineos {sub}")
            for f in files:
                lines.append(f"      prescribed in: {f}")
        lines += [
            "",
            "Fix by adding the subcommand to _BYPASS_COMMANDS in",
            "src/divineos/cli/__init__.py, or by changing the gate to prescribe",
            "something reachable. Read which before choosing.",
        ]
        pytest.fail("\n".join(lines))


def test_the_known_deadlock_commands_stay_exempt():
    """Regression pin for the ones that actually deadlocked.

    Separate from the derived test on purpose: the derived test could stop
    finding these if the scanner regresses or a denial message is reworded.
    This one fails loudly if the exemptions themselves are ever removed.
    """
    for cmd in ("goal", "compass-ops", "compass", "learn", "correction"):
        assert cmd in _BYPASS_COMMANDS, (
            f"{cmd!r} was removed from _BYPASS_COMMANDS. It is a prescribed "
            "gate remedy and removing it re-opens a verified deadlock."
        )
