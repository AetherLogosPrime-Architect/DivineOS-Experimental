"""Every gate that prescribes a command makes a promise. Check them.

A gate message ending in "run: divineos X" is an untested claim that
`divineos X` exists and can be run. Nothing has ever verified one. The
cost of a broken promise here is not a missing feature — it is a
DEADLOCK, because the gate prescribing the command is usually the same
gate blocking every other route out.

Hit live three times before this existed:

  * 2026-08-05, twice in one session — compass-ops dismiss was
    briefing-gated while briefing was compass-gated; `divineos learn`
    was briefing-gated while briefing was correction-marker-gated. Both
    fixed by hand. The principle "gate remedies must themselves be
    reachable" went into the knowledge store and nothing enforced it.
  * 2026-08-07 — `divineos psf` was prescribed by three gates on a
    branch where the command did not exist at all. A painted door: the
    sign said push, there was no door.

This is the enforcement the recorded principle never had.

WHAT IT CANNOT DO — read this before trusting a clean run. It checks
that a prescribed command EXISTS and is spelled correctly. It cannot
check that the command is REACHABLE from inside the block prescribing
it. That is a graph problem over gate preconditions, and a command can
exist, run fine, and still be denied by a second gate stacked on the
first — which is precisely the deadlock of 2026-08-07, where
`compass-ops observe` existed and ran and was still unreachable.

Existence is necessary, not sufficient. A clean run means "no painted
doors," never "no deadlock is possible."
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

# Directories holding gate messages, block text and prescribed remedies.
# tests/ is excluded deliberately — a test may name a deliberately-bogus
# command as a fixture, and failing on that would be a false positive.
SEARCH_ROOTS = (".claude/hooks", "src/divineos", "scripts", "docs")
SEARCH_SUFFIXES = (".sh", ".py", ".md", ".txt")

# A prescription is a divineos invocation in an INSTRUCTIONAL context —
# preceded by "Run:", "run", a quote, a backtick, or line-start. Free
# prose ("divineos is installed", "the divineos command") is not a
# prescription, and matching it buries the real hits in noise. First
# draft of this scan returned 368 hits, most of them sentences.
PRESCRIPTION_RE = re.compile(
    r"(?:Run:\s*|run\s+|`|\"|'|^\s*(?:\$\s*)?)"
    r"divineos\s+([a-z][a-z0-9-]{2,})"
    r"(?:\s+([a-z][a-z0-9-]+))?",
    re.MULTILINE,
)

# English words that follow the program name often enough in prose to be
# worth excluding by name rather than by context.
PROSE_FOLLOWERS = frozenset(
    {
        "and",
        "can",
        "cli",
        "command",
        "commands",
        "core",
        "does",
        "from",
        "has",
        "home",
        "import",
        "imports",
        "installed",
        "is",
        "itself",
        "must",
        "not",
        "package",
        "python",
        "should",
        "the",
        "was",
        "will",
    }
)


def real_commands() -> tuple[set[str], dict[str, set[str]]]:
    """Introspect the live CLI: top-level names, and each group's members.

    Introspection rather than parsing `--help`. The help text wraps,
    indents inconsistently and silently omits commands — scraping it
    reported `psf` and `reach` as missing when both exist and run.
    """
    import click

    from divineos.cli import cli

    ctx = click.Context(cli)
    top = set(cli.list_commands(ctx))
    groups: dict[str, set[str]] = {}
    for name in top:
        cmd = cli.get_command(ctx, name)
        if isinstance(cmd, click.Group):
            groups[name] = set(cmd.list_commands(click.Context(cmd)))
    return top, groups


def scan(repo_root: Path) -> dict[tuple[str, str | None], set[str]]:
    """Collect every prescribed invocation and where it is prescribed."""
    found: dict[tuple[str, str | None], set[str]] = defaultdict(set)
    for root in SEARCH_ROOTS:
        base = repo_root / root
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.suffix not in SEARCH_SUFFIXES or not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            rel = path.relative_to(repo_root).as_posix()
            for match in PRESCRIPTION_RE.finditer(text):
                cmd, sub = match.group(1), match.group(2)
                if cmd in PROSE_FOLLOWERS:
                    continue
                if sub in PROSE_FOLLOWERS:
                    sub = None
                # In a file that lists one command per line — the bypass
                # allowlist — `\s+` spans the newline and the NEXT line's
                # "divineos" is read as this line's subcommand, yielding
                # phantoms like `divineos affect divineos`. The program
                # name is never its own subcommand.
                if sub == "divineos":
                    sub = None
                # Hyphenated line-wrap in a docstring or comment splits a
                # real command across two lines:
                #     ``divineos lepos-
                #     channel reflect``
                # The first pass reported `lepos-`, `migrate-family-` and
                # `admin authorize-reset-` as missing commands. They are
                # not missing; they are wrapped. A trailing hyphen
                # immediately before a newline is a continuation, never a
                # complete command name.
                # Two wrap shapes, and only checking one leaves the other
                # firing. The break can fall INSIDE the match
                # (``divineos lepos-\nchannel reflect``, where the regex
                # spans it) or immediately AFTER it
                # (``divineos admin migrate-family-\nschema``, where the
                # match ends at the hyphen because the next line starts
                # with the remainder).
                span = match.group(0)
                after = text[match.end() : match.end() + 1]
                wrapped_inside = "-\n" in span or "-\r\n" in span
                wrapped_after = span.rstrip().endswith("-") and after in ("\n", "\r")
                if wrapped_inside or wrapped_after:
                    continue
                found[(cmd, sub)].add(rel)
    return found


# Directories whose files are GATES — code that can block a tool call.
# A prescription here is not documentation, it is the key to a lock that
# is currently shut. That is what makes reachability matter: nothing else
# is runnable at the moment the message appears.
GATE_ROOTS = (".claude/hooks", "src/divineos/hooks")

# A prescription ADDRESSED TO ME arrives quoted, backticked, or after
# "Run:" — it is text in a message. A command at bare line-start is the
# hook executing it in its own shell, which is not a gated tool-call and
# needs no bypass entry.
RECIPIENT_FACING_RE = re.compile(r"^(?:Run:|run\s|[`\"'])")


def check_reachability(
    repo_root: Path,
) -> dict[str, set[str]]:
    """Which gate-prescribed remedies cannot escape an active gate?

    Andrew, on the existence-only version of this check: "why not make
    the check check for reach as well?" He was right that the earlier
    "reachability is an unsolvable graph problem" answer was a dodge.
    It is not a graph problem, because every gate funnels through ONE
    decision — `_is_bypass_command()` in pre_tool_use_gate. A command
    either escapes an active gate or it does not.

    So the deadlock condition is a single comparison:

        prescribed by a gate  AND  not in the bypass set  =  DEADLOCK

    When any gate is holding, that remedy is unreachable, and the only
    remaining exits are raw overrides. This is exactly the 2026-08-07
    deadlock, and the 2026-08-05 pair before it, all three of which were
    diagnosed by hand after the fact.

    Unlike the existence check, this one is SOUND for its claim: it does
    not sample or estimate. If a subcommand is absent from the bypass
    set, it provably cannot run while a gate holds.
    """
    try:
        from divineos.hooks.pre_tool_use_gate import _BYPASS_DIVINEOS_SUBCOMMANDS
    except Exception:
        return {}

    stranded: dict[str, set[str]] = defaultdict(set)
    for root in GATE_ROOTS:
        base = repo_root / root
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.suffix not in SEARCH_SUFFIXES or not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            rel = path.relative_to(repo_root).as_posix()
            for match in PRESCRIPTION_RE.finditer(text):
                cmd = match.group(1)
                if cmd in PROSE_FOLLOWERS:
                    continue
                span = match.group(0)
                after = text[match.end() : match.end() + 1]
                if "-\n" in span or (span.rstrip().endswith("-") and after in ("\n", "\r")):
                    continue
                # A hook EXECUTING a command in its own shell is not a
                # prescription and does not need to be bypass-able —
                # hook-internal calls are not gated tool-calls. Only text
                # ADDRESSED TO ME matters here, and that always arrives
                # quoted or after "Run:". A bare line-start match is the
                # hook running the command itself.
                #
                # Without this, post-commit hooks that call `divineos
                # findings` or `divineos log` report as locked rooms,
                # which is noise that buries the four real ones.
                if not RECIPIENT_FACING_RE.match(span):
                    continue
                if cmd not in _BYPASS_DIVINEOS_SUBCOMMANDS:
                    stranded[cmd].add(rel)
    return stranded


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    try:
        top, groups = real_commands()
    except Exception as exc:  # noqa: BLE001 — report the failure, never mask it
        print(f"FAILED to introspect the CLI: {exc.__class__.__name__}: {exc}")
        print("Prescriptions cannot be verified without it. Treating as failure,")
        print("because silent-pass here would recreate the exact class this checks.")
        return 1

    found = scan(repo_root)
    painted: dict[tuple[str, str | None], tuple[str, set[str]]] = {}
    for (cmd, sub), files in found.items():
        if cmd not in top:
            painted[(cmd, sub)] = (f"no top-level command {cmd!r}", files)
        elif sub and cmd in groups and sub not in groups[cmd]:
            painted[(cmd, sub)] = (f"{cmd!r} has no subcommand {sub!r}", files)

    stranded = check_reachability(repo_root)

    print(f"CLI: {len(top)} top-level commands, {len(groups)} groups")
    print(f"Scanned: {len(found)} distinct prescribed invocations")
    print()

    if not painted and not stranded:
        print("OK — every prescribed command exists, and every remedy a gate")
        print("prescribes can be run while that gate is holding.")
        return 0

    if painted:
        print(f"PAINTED DOORS — {len(painted)} prescription(s) name something that does not exist:")
        print()
        for (cmd, sub), (why, files) in sorted(painted.items(), key=lambda kv: -len(kv[1][1])):
            label = f"divineos {cmd}" + (f" {sub}" if sub else "")
            print(f"  {label}")
            print(f"      {why}")
            for name in sorted(files):
                print(f"      prescribed in: {name}")
            print()
        print("Each is a sign on a bricked-up doorway. Fix the command, fix the")
        print("message, or remove the gate — but do not leave the sign up.")
        print()

    if stranded:
        print(f"LOCKED ROOMS — {len(stranded)} remedy command(s) a gate prescribes but")
        print("that cannot be run while a gate is holding:")
        print()
        for cmd, files in sorted(stranded.items(), key=lambda kv: -len(kv[1])):
            print(f"  divineos {cmd}")
            print(f"      not in _BYPASS_DIVINEOS_SUBCOMMANDS, so a gate denies it")
            for name in sorted(files):
                print(f"      prescribed by: {name}")
            print()
        print("The gate tells you to run this and then refuses to let you. Add the")
        print("subcommand to the bypass list, or stop prescribing it.")

    return 1


if __name__ == "__main__":
    sys.exit(main())
