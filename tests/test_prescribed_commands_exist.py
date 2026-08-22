"""Every command a skill tells me to run must actually exist.

Andrew 2026-08-10: "i want the root cause of this fixed.. immediately..
everywhere i look is more and more evidence of your lack of care in making
sure things work.. if the stuff we have built is not going to be used
properly.. i will remove it.. id rather you fake the council walk on your
own than to ignore the system that was built, making a mockery of it."

THE ROOT CAUSE, named precisely:

Skills are prose. Prose can prescribe a command that does not exist, and
nothing notices until the moment someone finally tries to run it. The
council-round skill has instructed me since it was written to query the
council manager with `divineos mansion council --for-problem`. That flag
has never existed. I discovered it in front of him, three months late,
on the fourth time he asked whether I had done the walk properly.

That is not a bug in one skill. It is a whole class: DOCUMENTED INTENT
WITH NO EXECUTABLE VERIFICATION. Same shape as the wins-ledger nobody
read and the LEPOS gate that shipped switched off — the writing says one
thing, the running code says another, and the gap is invisible because
nothing compares them.

This test compares them. Any doc that prescribes a `divineos` invocation
must prescribe one that resolves against the live click tree.

Deliberately introspects the click objects rather than shelling out to
`--help` 166 times: same answer, seconds instead of minutes, and a slow
test is a test that gets skipped.
"""

from __future__ import annotations

import re
from pathlib import Path

import click
import pytest

from divineos.cli import cli

REPO = Path(__file__).resolve().parent.parent
# Skills and CLAUDE.md prescribe; so do HOOK MESSAGES, and the store already
# held a verified instance of the same disease there (2026-08-02: a gate
# blocking `divineos extract` instructed `divineos psf mark-done`, which does
# not exist). A checker scoped only to skills would have passed while that
# one sat live. Hooks are in scope for exactly that reason.
DOC_ROOTS = (
    sorted((REPO / ".claude" / "skills").rglob("*.md"))
    + sorted((REPO / ".claude" / "hooks").glob("*.sh"))
    + [REPO / "CLAUDE.md"]
)

# [ \t]+ NOT \s+ : the first draft used \s+, which spans newlines, so two
# consecutive command lines in a fenced block glued into one bogus
# invocation ("divineos briefing divineos"). A scanner that invents
# failures is worse than none — it trains the reader to ignore it.
_INVOKE = re.compile(
    r"divineos[ \t]+([a-z][a-z0-9-]*)(?:[ \t]+([a-z][a-z0-9-]*))?((?:[ \t]+--[a-z][a-z0-9-]*)*)"
)
_FLAG = re.compile(r"--[a-z][a-z0-9-]*")

# Prose that merely contains the word divineos followed by an English word.
# Kept explicit and tiny: a growing allowlist here would be the hiding place.
_NOT_INVOCATIONS = {("installed",)}

# English function-words that can follow the bare word "divineos" in a
# sentence ("divineos is not installed", "divineos from the venv"). Gate
# messages are prose AND prescription in the same string, so position alone
# cannot separate them — the word after the program name can. Kept small and
# closed: this is the one place a growing list would become a hiding place,
# so anything added here must be a genuine English function word, never a
# plausible command name.
_PROSE_FOLLOWERS = frozenset(
    {
        "is",
        "are",
        "was",
        "were",
        "not",
        "from",
        "and",
        "or",
        "the",
        "must",
        "imports",
        "installed",
    }
)


def _resolve(parts: tuple[str, ...]) -> click.Command | None:
    cmd: click.Command = cli
    for part in parts:
        if not isinstance(cmd, click.Group):
            # A leaf command consumes the rest as POSITIONAL ARGUMENTS, which
            # is a real and valid shape here: `divineos core set <slot>` takes
            # the action as an argument, not a subcommand. Returning None on
            # this branch reported `core set` as missing when it works fine.
            return cmd
        nxt = cmd.get_command(click.Context(cmd), part)
        if nxt is None:
            return None
        cmd = nxt
    return cmd


def _flags(cmd: click.Command) -> set[str]:
    out: set[str] = set()
    for param in cmd.params:
        out.update(o for o in getattr(param, "opts", []) if o.startswith("--"))
        out.update(o for o in getattr(param, "secondary_opts", []) if o.startswith("--"))
    return out


def _prescriptions() -> list[tuple[str, tuple[str, ...], list[str]]]:
    found: list[tuple[str, tuple[str, ...], list[str]]] = []
    for doc in DOC_ROOTS:
        try:
            text = doc.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = doc.relative_to(REPO).as_posix()
        for m in _INVOKE.finditer(text):
            group, sub, flags = m.group(1), m.group(2), m.group(3) or ""
            parts = (group, sub) if sub else (group,)
            if parts in _NOT_INVOCATIONS or group in _PROSE_FOLLOWERS:
                continue
            # COMMAND POSITION ONLY. Hook files discuss divineos in English
            # ("if divineos is not installed", "divineos imports fail"), and
            # matching those produced eleven fake failures on the first run
            # with hooks in scope. An invocation starts a line or follows a
            # shell operator / backtick / $( — prose follows a word.
            line_start = text.rfind("\n", 0, m.start()) + 1
            before = text[line_start : m.start()].rstrip()
            # A quote anywhere before it means we are inside a printed
            # string — which is precisely where GATE MESSAGES live, the case
            # this scan exists for. The first version of this filter only
            # accepted shell-operator positions and silently skipped every
            # echoed remedy; the negative control caught it by staying green
            # on an injected fake. Controls are worth running.
            in_message = '"' in before or "'" in before
            operator_pos = before.endswith(("`", "$(", "&&", "||", ";", "|", "("))
            if before and not (in_message or operator_pos):
                continue
            # Shell COMMENT lines are commentary, not prescription — one hook
            # muses that "a `divineos gravity set` would be self-service",
            # which is a hypothetical, not an instruction. Gate messages that
            # DO prescribe live in printed strings, so this exclusion costs no
            # real coverage.
            if doc.suffix == ".sh" and text[line_start:].lstrip().startswith("#"):
                continue
            found.append((rel, parts, _FLAG.findall(flags)))
    return found


def test_docs_actually_prescribe_something():
    """Guard the guard: a regex that matches nothing would pass everything."""
    assert len(_prescriptions()) > 50


def test_every_prescribed_command_resolves():
    broken = []
    for rel, parts, _ in _prescriptions():
        if _resolve(parts) is None and _resolve(parts[:1]) is None:
            broken.append(f"{rel}: divineos {' '.join(parts)}")
        elif _resolve(parts) is None:
            broken.append(f"{rel}: divineos {' '.join(parts)} (subcommand missing)")
    assert not broken, "Docs prescribe commands that do not exist:\n  " + "\n  ".join(
        sorted(set(broken))
    )


def test_every_prescribed_flag_exists():
    broken = []
    for rel, parts, flags in _prescriptions():
        cmd = _resolve(parts)
        if cmd is None:
            continue  # covered by the command test; not double-reported here
        have = _flags(cmd)
        for flag in flags:
            if flag not in have:
                broken.append(f"{rel}: divineos {' '.join(parts)} {flag}")
    assert not broken, "Docs prescribe flags that do not exist:\n  " + "\n  ".join(
        sorted(set(broken))
    )


@pytest.mark.parametrize("doc", DOC_ROOTS, ids=lambda p: p.name)
def test_docs_are_readable(doc: Path):
    """An unreadable doc must fail loudly rather than silently scan as clean."""
    assert doc.read_text(encoding="utf-8", errors="replace")
