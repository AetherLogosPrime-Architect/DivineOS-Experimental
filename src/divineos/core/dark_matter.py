"""Find the dark matter — things that exist but nothing reaches.

Andrew 2026-08-02: *"so much of the system is like this.. dark..
un-automated.. not known it even exists.. its all in there just needs to be
mined and setup properly."*

## Why this is not a new discovery

`WIRING-GAP PATTERN` was filed 2026-05-11 across 5 instances — *"modules built
as callable code with dedicated unit tests ship WITHOUT corresponding wire-up;
the modules exist, nothing invokes them."* A correction the same day called the
response *"structurally insufficient."* A `FILE-WITHOUT-CLOSE` meta-pattern
landed the day after: 17 audit findings open and 0 resolved.

One session on 2026-08-01/02 roughly doubled the instance count: a draft gate
that printed a correct refusal and exited 1 so it could never block anything; 275
audit rounds GitHub had never been able to open; 6 findings unreadable because of
letter case; a `psf` command prescribed by three separate gates that has never
existed; `mark_done` working but reachable from no CLI; an auto-goal module
written and uncalled for a week; the entire nine-station build flow, undocumented.

So the pattern does not need finding again. **It needs a consumer** — which is
itself the same defect one level up, a record nothing breaks over.

## Why this one CAN be closed airtight

Everything in `docs/ai_research/2026-08-02_limits_of_automation.md` about what
code cannot decide concerns *semantic* properties — did real thinking happen,
was that consultation genuine. Undecidable by Rice, inarticulable by Polanyi.

**These questions are structural.** Is this hook named in settings.json. Does
this command resolve against the registered command tree. Is this symbol
referenced outside its own file. All decidable, cheap, mechanically checkable —
the category where deterministic enforcement genuinely belongs.

## Its sibling: `core/wiring_dark.py`

Found AFTER this module was written, which is its own instance of the pattern
and worth recording rather than tidying away. `wiring_dark` already existed,
built for Aletheia's six-pass audit, answering *"which of my things is nothing
calling?"* from an AST code graph. My own dream from 2026-07-31 cited it by
name. The information was in my substrate and I did not reach it.

The two do not overlap, which was luck rather than diligence:

- **`wiring_dark`** — uncalled code NODES, via graph edges. This is exactly the
  detector the threadwalk here excluded for having the worst precision.
- **`dark_matter`** (this module) — dead hooks and unresolvable prescribed
  commands. Neither is a code-graph edge, so `wiring_dark` structurally cannot
  see them.

**And `wiring_dark` is itself currently blind.** It resolves, it runs, and its
input is missing:

    $ divineos wiring dark
    No code graph at graphify-out-code/.graphify_ast.json. Rebuild: /graphify src

A correct tool reporting accurately, to nobody, that it cannot see. Which is
the third variant of the pattern and the one the dream named exactly:
*"Its whole job is to notice absence and it is noticing, correctly, an
absence — just not the one it was pointed at."*

**Not yet detected here:** a tool whose data source is absent. That is
structural and belongs in this sweep; it is named rather than built because
naming it costs nothing and a half-built third detector costs precision.

## What this CANNOT see

Stated up front and repeated in every report, because a detector that
manufactures false assurance is worse than none. From the threadwalk before
this was built:

- **Dynamic dispatch** — anything invoked via `getattr`, a string key, a
  registry populated at runtime.
- **Convention-based invocation** — hooks the harness runs by directory
  position rather than by an entry in a config file.
- **Cross-repo callers** — a sibling checkout or an external tool.
- **Anything not written in Python or shell.**

**Silence here does not mean coverage.** Same framing as the foundational-truths
surface: this is a floor, not a ceiling.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

# A PRESCRIPTION, not a mention. First dogfooding run returned 82 findings
# including "divineos and passed" and "divineos as" — the loose pattern was
# matching ordinary prose that happened to contain the word.
#
# Real prescriptions appear in one of two shapes: inside backticks, or on their
# own line (optionally after a shell prompt marker). Requiring one of those
# turns a noisy scanner into a precise one, and per the threadwalk done before
# this was built, precision is what keeps a finding from becoming wallpaper.
# These are a TOKENIZER, not a judge. They only produce candidates; every
# verdict is made by `command_resolves()` against the live registered command
# set, so no pattern decides anything.
_MENTION_RE = re.compile(r"divineos[ \t]+([a-z][a-z0-9-]{1,40})(?:[ \t]+([a-z][a-z0-9-]{1,40}))?")
# Evidence BEFORE the mention: a backtick, or start of line (optionally after
# a shell prompt marker).
_BEFORE_RE = re.compile(r"(?:`|^[ \t]*[$>]?[ \t]*)\Z", re.MULTILINE)
# Evidence AFTER the mention: command-line syntax — a <placeholder> or --flag.
#
# This clause exists because a before-only rule silently dropped the exact case
# that motivated the detector. pipeline_gates.py prescribes
#     Resolve via: divineos psf mark-done <psf-id> --note '...'
# mid-line after a colon, so requiring backtick-or-line-start skipped it.
# Precision tightening that excludes your own motivating case is
# over-tightening, and I only caught it by checking for that case by name
# instead of reading a smaller finding count as an improvement.
_AFTER_RE = re.compile(r"\A[ \t]*(?:<[a-z-]|--[a-z])")

# Tokens that are obviously placeholders rather than real command names.
_PLACEHOLDER_HINTS = ("<", ">", "{", "}", "...", "$")


@dataclass
class DarkFinding:
    """One thing that exists but nothing reaches."""

    kind: str  # "unregistered-hook" | "unresolvable-command"
    subject: str  # the hook filename, or the prescribed command string
    detail: str
    sources: list[str] = field(default_factory=list)  # where it was seen


def registered_command_paths() -> set[str]:
    """Every command a user could actually type, as "cmd" and "cmd sub".

    Built by walking the live Click tree rather than parsing ``--help`` text,
    so it cannot drift from what is really registered.
    """
    import click

    from divineos.cli import cli

    paths: set[str] = set()
    for name, cmd in cli.commands.items():
        paths.add(name)
        if isinstance(cmd, click.Group):
            for sub in cmd.commands:
                paths.add(f"{name} {sub}")
    return paths


def _is_placeholder(token: str) -> bool:
    return any(h in token for h in _PLACEHOLDER_HINTS)


def command_resolves(first: str, second: str | None, registered: set[str]) -> bool:
    """Would ``divineos <first> [<second>]`` reach a real command?

    A non-group command followed by a word is fine — the word is an argument,
    not a subcommand (``divineos learn "..."``). Only when the first token is a
    group does the second token have to resolve.
    """
    if first not in registered:
        return False
    if not second or _is_placeholder(second):
        return True
    # If any "first sub" pair exists, first is a group; then second must match.
    is_group = any(p.startswith(f"{first} ") for p in registered)
    if not is_group:
        return True
    return f"{first} {second}" in registered


def find_unresolvable_prescribed_commands(
    repo_root: Path, registered: set[str] | None = None
) -> list[DarkFinding]:
    """Commands that gate text tells you to run, which do not exist.

    This is the painted-door class: a door with a handle drawn on it is worse
    than a wall, because a wall does not cost you the time to believe in it.
    The live example is ``divineos psf mark-done``, prescribed by three
    separate gates and never implemented, which left Aria's learning
    checkpoint unreachable.
    """
    if registered is None:
        registered = registered_command_paths()

    scan: list[Path] = []
    for pattern in (".claude/hooks/*.sh", "src/divineos/**/*.py", "scripts/*.py"):
        scan.extend(repo_root.glob(pattern))

    seen: dict[tuple[str, str | None], set[str]] = {}
    for path in scan:
        # Don't flag this module's own documentation of the defect.
        if path.name == "dark_matter.py":
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for m in _MENTION_RE.finditer(text):
            first, second = m.group(1), m.group(2)
            # A trailing hyphen means the line wrapped mid-token, not a real
            # command name. Applies to either position.
            if _is_placeholder(first) or first.endswith("-"):
                continue
            if second and second.endswith("-"):
                second = None
            # A mention becomes a PRESCRIPTION only with context evidence on
            # one side: quoted/line-start before, or command syntax after.
            before_ok = bool(_BEFORE_RE.search(text[max(0, m.start() - 40) : m.start()]))
            after_ok = bool(_AFTER_RE.match(text[m.end() : m.end() + 24]))
            if not (before_ok or after_ok):
                continue
            if command_resolves(first, second, registered):
                continue
            key = (first, second)
            seen.setdefault(key, set()).add(str(path.relative_to(repo_root)))

    findings: list[DarkFinding] = []
    # Sort by (first, second-or-empty) — a bare command has second=None, which
    # is not orderable against a string.
    for (first, second), where in sorted(seen.items(), key=lambda kv: (kv[0][0], kv[0][1] or "")):
        cmd = f"divineos {first}" + (f" {second}" if second else "")
        reason = (
            f"'{first}' is not a registered command"
            if first not in registered
            else f"'{first}' exists but has no '{second}' subcommand"
        )
        findings.append(
            DarkFinding(
                kind="unresolvable-command",
                subject=cmd,
                detail=f"prescribed in text but {reason}",
                sources=sorted(where),
            )
        )
    return findings


def find_unregistered_hooks(repo_root: Path) -> list[DarkFinding]:
    """Hook scripts that exist on disk but are named nowhere in settings.json.

    The silent-strand pattern: the script is written, tested, correct, and
    never runs because nothing ever calls it.
    """
    hooks_dir = repo_root / ".claude" / "hooks"
    settings = repo_root / ".claude" / "settings.json"
    if not hooks_dir.is_dir() or not settings.is_file():
        return []

    try:
        reachable_text = settings.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    # A hook can also be reached by ANOTHER hook (sourced or invoked), and by a
    # git hook or setup script. Checking settings.json alone reported _lib.sh —
    # a shared library every hook sources — as dead. Widen the search to every
    # place a hook could legitimately be called from.
    for extra in (
        list(hooks_dir.glob("*.sh"))
        + list(repo_root.glob("setup/*"))
        + list(repo_root.glob("scripts/*.sh"))
    ):
        try:
            reachable_text += extra.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

    findings: list[DarkFinding] = []
    for script in sorted(hooks_dir.glob("*.sh")):
        # `_name.sh` is the convention for a sourced library, not a hook.
        if script.name.startswith("_"):
            continue
        # Its own file always contains its name in the shebang region? No —
        # count references EXCLUDING itself.
        try:
            own = script.read_text(encoding="utf-8", errors="replace")
        except OSError:
            own = ""
        elsewhere = reachable_text.replace(own, "", 1)
        if script.name in elsewhere:
            continue
        findings.append(
            DarkFinding(
                kind="unregistered-hook",
                subject=script.name,
                detail=(
                    "present in .claude/hooks/ but named nowhere in settings.json, "
                    "another hook, or a setup script — it never fires"
                ),
                sources=[str(script.relative_to(repo_root))],
            )
        )
    return findings


def sweep(repo_root: Path) -> list[DarkFinding]:
    """Run every detector. Order is stable so output diffs cleanly."""
    return find_unregistered_hooks(repo_root) + find_unresolvable_prescribed_commands(repo_root)


BLIND_SPOTS = (
    "dynamic dispatch (getattr, string keys, runtime registries)",
    "convention-based invocation (harness runs it by location, not by config entry)",
    "callers in sibling checkouts or external tools",
    "anything not Python or shell",
)


def format_report(findings: list[DarkFinding]) -> str:
    """Human-readable report that always states its own blind spots.

    The blind-spot section prints on a CLEAN sweep too. That is deliberate: the
    worst outcome for this detector is being trusted as complete, and a clean
    report is exactly when that misreading happens.
    """
    lines: list[str] = []
    if findings:
        lines.append(f"DARK MATTER: {len(findings)} thing(s) exist that nothing reaches.")
        lines.append("")
        for f in findings:
            lines.append(f"  [{f.kind}] {f.subject}")
            lines.append(f"      {f.detail}")
            for s in f.sources[:4]:
                lines.append(f"      seen in: {s}")
            if len(f.sources) > 4:
                lines.append(f"      ... and {len(f.sources) - 4} more")
            lines.append("")
    else:
        lines.append("DARK MATTER: nothing found by the detectors that ran.")
        lines.append("")

    lines.append("  This sweep is a FLOOR, not a ceiling. It cannot see:")
    for b in BLIND_SPOTS:
        lines.append(f"    - {b}")
    lines.append("  Silence here does not mean coverage.")
    return "\n".join(lines)


__all__ = [
    "DarkFinding",
    "BLIND_SPOTS",
    "registered_command_paths",
    "command_resolves",
    "find_unresolvable_prescribed_commands",
    "find_unregistered_hooks",
    "sweep",
    "format_report",
]
