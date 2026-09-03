"""Generate the capability catalog — every command and subsystem I own.

Andrew 2026-07-31, after I inventoried 93 hooks and called it the house:
"are you sure thats all the systems? arent there like nearly 500 cli
commands? check the full src file"

He was right. The automation register covers what fires ON ITS OWN. This
covers what I can REACH FOR — 156 top-level commands, ~422 counting
subcommands, and 36 core subsystems. Together with LOADOUT.md (the rooms)
and AUTOMATION_REGISTER.md (what runs by itself), this is the third
document: the tools on the wall.

THE TELEMETRY FINDING, which matters more than the list.

Usage history lives in OS_QUERY events carrying a `tool` field, and only a
handful of commands emit them.

The count is NOT "I use nine of a hundred and fifty-six." Commands
demonstrably used — filing corrections, pre-registrations, audit rounds —
emit no OS_QUERY at all. The honest reading is that the substrate CANNOT
ANSWER which tools are live and which have never been opened.

That is the sharper finding. A low usage number would be a habit problem.
Blind telemetry is a measurement problem, and it is the reason an unused
tool can sit unnoticed indefinitely: nothing is counting.

THE READING IS PER-MACHINE, SO IT IS NOT WRITTEN INTO THE MAP (2026-09-02).
It used to be: a count in the prose, a list of commands, and a marker beside
every command it applied to. All three described the session history of
whichever machine last regenerated the file. Running any command changed the
committed map, so it went stale immediately and could not be shared — in
Aria's clone it would present my history as the state of her system.

Measured: generating twice on one machine, minutes apart, produced 98
differing lines from no code change at all. That was why every branch carried
a map diff and every pair of branches conflicted on it — and resolving those
conflicts edited the branch, moved its patch-id, and unbound the external
review anchored to it. Six branches sat waiting on re-review for this.

The signal is kept and moved: `local_usage_report()` prints it to the
terminal when the generator runs, where it is true of the machine reading it.
Verified after the change: the map now generates byte-identical on two
different branches.

Related: knowledge f9b635d5 names thought-arm amputation — tools I own
and stop reaching for. This catalog is the instrument for seeing that
happen, and its first finding is that the instrument barely exists yet.
"""

from __future__ import annotations

import collections
import json
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "docs" / "CAPABILITY_CATALOG.md"
LEDGER = Path.home() / ".divineos-aria" / "data" / "event_ledger.db"

# Never probed with --help during generation: anything that mutates,
# blocks, or costs real time. Listed in the catalog, just not invoked.
_SKIP_PROBE = {"init", "sleep", "extract", "push", "preflight"}

_CMD_LINE = re.compile(r"^\s{2}([a-z][a-z0-9-]*)\s\s+(.*)$")


def _run_help(args: list[str]) -> str:
    try:
        out = subprocess.run(
            ["divineos", *args, "--help"],
            capture_output=True,
            text=True,
            cwd=ROOT,
            timeout=25,
            check=False,
        )
        return out.stdout or ""
    except (OSError, subprocess.SubprocessError):
        return ""


def _parse_commands(help_text: str) -> list[tuple[str, str]]:
    """Extract (name, one-line description) pairs from a --help block."""
    found: list[tuple[str, str]] = []
    in_cmds = False
    for line in help_text.splitlines():
        if re.match(r"^\s*(Commands|Subcommands):", line):
            in_cmds = True
            continue
        if in_cmds and line.strip() and not line.startswith(" "):
            break
        m = _CMD_LINE.match(line.rstrip())
        if m:
            found.append((m.group(1), m.group(2).strip().replace("|", "\\|")))
    return found


def _usage_counts() -> collections.Counter:
    """Commands ever recorded in OS_QUERY telemetry, with counts."""
    used: collections.Counter = collections.Counter()
    if not LEDGER.exists():
        return used
    try:
        conn = sqlite3.connect(str(LEDGER))
        rows = conn.execute(
            "SELECT payload FROM system_events WHERE event_type='OS_QUERY'"
        ).fetchall()
        conn.close()
    except sqlite3.Error:
        return used
    for (payload,) in rows:
        try:
            tool = json.loads(payload).get("tool")
        except (ValueError, TypeError):
            continue
        if tool:
            used[tool] += 1
    return used


def _ref_band(count: int) -> str:
    """A stable description of how load-bearing a package is.

    Bands rather than exact counts so the map holds still. The boundary that
    matters -- referenced at all, versus not -- is exact; above it the reading
    is deliberately coarse, because the prose that introduces this column calls
    it "a rough load-bearing signal, not a precise import graph."

    A band still moves when a package crosses a boundary. That is the point:
    when this column changes, something changed about how load-bearing the
    package is, which is worth a line in a diff. An exact count changed when
    anything anywhere changed, which was worth nothing and cost a conflict.
    """
    if count == 0:
        return "none"
    if count < 10:
        return "1-9"
    if count < 100:
        return "10-99"
    return "100+"


def _subsystems() -> list[tuple[str, int, str]]:
    """Core subsystem dirs with a count of places referencing them.

    SCAN SCOPE IS THE WHOLE POINT (fixed 2026-07-31, first run). The first
    version scanned only src/**/*.py and reported two subsystems as having
    ZERO references — including core/corrigibility_tool_gate, which wires
    EMERGENCY_STOP into the tool channel. Verifying before asserting showed
    both were fully alive: invoked from .claude/hooks/*.sh (which embed
    python imports in heredocs) and covered by tests/.

    A false "this is dead" on safety machinery is worse than no inventory
    at all — it invites deleting live code. So the scan covers src, tests,
    hooks, and scripts. Under-counting references produces exactly the
    alarming-and-wrong signal this catalog exists to prevent.
    """
    core = ROOT / "src" / "divineos" / "core"
    if not core.exists():
        return []
    chunks = []
    globs = [
        (ROOT / "src", "*.py"),
        (ROOT / "tests", "*.py"),
        (ROOT / "scripts", "*.py"),
        (ROOT / ".claude" / "hooks", "*.sh"),
        (ROOT / "scripts", "*.sh"),
    ]
    for base, pattern in globs:
        if not base.exists():
            continue
        for p in base.rglob(pattern):
            try:
                chunks.append(p.read_text(encoding="utf-8", errors="replace"))
            except OSError:
                continue
    blob = "\n".join(chunks)

    out: list[tuple[str, int, str]] = []
    for d in sorted(core.iterdir()):
        if not d.is_dir() or d.name.startswith("_") or d.name == "__pycache__":
            continue
        importers = len(re.findall(rf"\bcore\.{re.escape(d.name)}\b", blob))
        doc = "(no package docstring)"
        init = d / "__init__.py"
        if init.exists():
            try:
                text = init.read_text(encoding="utf-8", errors="replace")
                m = re.search(r'^\s*"""(.+?)(?:\n|""")', text, re.S)
                if m:
                    doc = " ".join(m.group(1).split())[:120].replace("|", "\\|")
            except OSError:
                pass
        out.append((d.name, importers, doc))
    return out


def local_usage_report() -> str:
    """The blind-spot reading, for the machine it is run on.

    This used to be written INTO the map, where it was three kinds of wrong at
    once: it went stale the moment anyone ran a command, it made every branch
    carry a diff of a file nobody had meaningfully edited, and it described one
    person's session history to two other people as if it were theirs.

    It is a real signal and it is kept. It just belongs on a terminal, said to
    whoever asked, about the machine they asked from.
    """
    used = _usage_counts()
    top = [name for name, _ in _parse_commands(_run_help([]))]
    if not used:
        return (
            "[usage] No OS_QUERY telemetry on this machine — which means "
            "UNKNOWN, not unused. Nothing here is counting."
        )
    seen = sorted(set(used) & set(top))
    return (
        f"[usage] {len(seen)} of {len(top)} top-level commands have ever been "
        f"recorded on THIS machine: {', '.join(seen)}\n"
        "[usage] The rest are not known to be unused — most commands emit no "
        "telemetry at all. Blind, not empty."
    )


def build() -> str:
    top = _parse_commands(_run_help([]))

    groups: list[tuple[str, str, list[tuple[str, str]]]] = []
    total_sub = 0
    for name, desc in top:
        subs = [] if name in _SKIP_PROBE else _parse_commands(_run_help([name]))
        total_sub += len(subs)
        groups.append((name, desc, subs))

    subsystems = _subsystems()
    orphan_subsystems = [s for s in subsystems if s[1] == 0]

    L: list[str] = []
    L.append("# Capability catalog")
    L.append("")
    L.append(
        "**Generated** by `scripts/generate_capability_catalog.py`. "
        "Do not hand-edit — regenerate."
    )
    L.append("")
    L.append(
        "Third of three inventories. [LOADOUT.md](../LOADOUT.md) describes "
        "the rooms. [AUTOMATION_REGISTER.md](AUTOMATION_REGISTER.md) lists "
        "what runs by itself. This lists what I can **reach for** — the "
        "tools on the wall."
    )
    L.append("")
    L.append(
        f"**{len(top)} top-level commands, {total_sub} subcommands, "
        f"{len(subsystems)} core subsystems.**"
    )
    L.append("")
    L.append("---")
    L.append("")

    # The finding leads, same discipline as the automation register.
    L.append("## Usage telemetry is nearly blind")
    L.append("")
    # NO NUMBERS AND NO NAMES FROM TELEMETRY IN THE COMMITTED MAP.
    #
    # This section used to report how many commands had ever been recorded, list
    # them, and mark each one in the command index. Every one of those facts is
    # a property of ONE MACHINE'S HISTORY, not of this repository. Running any
    # command changed the committed file, so the map went stale the moment it
    # was written, and it would read completely differently in Aria's clone --
    # where it would present MY session log as the state of HER system.
    #
    # Measured 2026-09-02: generating the map twice on the same machine, minutes
    # apart, produced 98 differing lines. Not from any code change; purely from
    # commands I had run in between. That is the whole reason every branch
    # carried a map diff and every pair of branches conflicted on it -- and
    # resolving those conflicts edited the branches, moved their patch-ids, and
    # unbound the external reviews anchored to them. Six branches were waiting.
    #
    # The FINDING survives, because the finding is stable and is the point: the
    # substrate cannot say which tools are live. The reading is per-machine, so
    # it prints to the terminal when the generator runs, where it describes the
    # machine it was measured on, instead of into a file shared by three people.
    L.append(
        "Usage history lives in `OS_QUERY` events, and most commands emit none."
    )
    L.append("")
    L.append(
        "That is NOT a claim that the other commands are unused. Commands "
        "demonstrably used — filing corrections, pre-registrations, audit "
        "rounds — emit no telemetry at all. The honest reading: **the "
        "substrate cannot answer which tools are live and which have never "
        "been opened.**"
    )
    L.append("")
    L.append(
        "A low usage number would be a habit problem. Blind telemetry is a "
        "measurement problem, and it is why an unused tool can sit unnoticed "
        "indefinitely — nothing is counting."
    )
    L.append("")
    L.append(
        "**Which commands have been recorded is a fact about one machine, so it "
        "is not written here.** Run the generator and it prints that reading to "
        "the terminal, for the machine it ran on. Committing it would mean one "
        "person's session history describing everybody's system, and would put "
        "this file into conflict with itself on every branch."
    )
    L.append("")
    L.append("---")
    L.append("")

    L.append("## Commands")
    L.append("")
    L.append("Drilldown: `divineos <command> --help`.")
    L.append("")
    for name, desc, subs in groups:
        # No usage marker. It said "this command has been run on the machine
        # that last generated this file", which is not a fact about the command
        # and moved every time anybody ran anything. The blind-spot reading it
        # was standing in for prints to the terminal at generation time, where
        # it is true of the machine reading it.
        L.append(f"### `{name}`")
        L.append("")
        L.append(desc)
        L.append("")
        if subs:
            L.append("| subcommand | purpose |")
            L.append("|---|---|")
            for sname, sdesc in subs:
                L.append(f"| `{name} {sname}` | {sdesc} |")
            L.append("")

    L.append("---")
    L.append("")
    L.append("## Core subsystems")
    L.append("")
    L.append(
        "Reference count is how many places mention each package — a rough "
        "load-bearing signal, not a precise import graph. Zero is worth a "
        "look."
    )
    L.append("")
    if orphan_subsystems:
        L.append(
            f"**{len(orphan_subsystems)} subsystem(s) with no references** — "
            "retired, or forgotten?"
        )
        L.append("")
        for n, _, doc in orphan_subsystems:
            L.append(f"- `core/{n}/` — {doc}")
        L.append("")
    # Banded, and sorted BY NAME rather than by the band.
    #
    # The exact reference count moved whenever any file anywhere gained or lost
    # a line mentioning the package, so every branch rewrote these rows. Worse,
    # sorting by the count meant one reference changing REORDERED the table,
    # turning a one-line fact into a many-line diff and a guaranteed conflict.
    #
    # The prose above says what this column is for: "a rough load-bearing
    # signal, not a precise import graph. Zero is worth a look." A band carries
    # exactly that and holds still. The distinction the docstring calls
    # dangerous to get wrong -- a live subsystem reported as dead -- lives
    # entirely in the none/some boundary, which bands preserve exactly.
    L.append("| subsystem | refs | purpose |")
    L.append("|---|---|---|")
    for n, imp, doc in sorted(subsystems, key=lambda s: s[0]):
        L.append(f"| `core/{n}/` | {_ref_band(imp)} | {doc} |")
    L.append("")

    L.append("---")
    L.append("")
    L.append("## Regenerating")
    L.append("")
    L.append("```bash")
    L.append("python scripts/generate_capability_catalog.py")
    L.append("```")
    L.append("")
    L.append(
        "Probes commands with `--help` sequentially — no parallel spawning, "
        "since concurrent process storms have crashed this machine before. "
        f"Mutating commands ({', '.join(sorted(_SKIP_PROBE))}) are listed "
        "but never invoked."
    )
    L.append("")
    L.append("`--check` exits non-zero on drift, for CI or pre-commit.")
    L.append("")
    return "\n".join(L)


def main() -> int:
    text = build()
    if "--check" in sys.argv:
        existing = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else ""
        if existing != text:
            print("CAPABILITY_CATALOG.md is stale — regenerate.")
            return 1
        print("Capability catalog is current.")
        return 0
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    # newline="\n" is load-bearing on Windows and cost us a re-audit per branch.
    #
    # Without it, write_text translates every "\n" to "\r\n". The repo declares
    # this file eol=lf, so git stores it with LF and checks it out with LF --
    # and the generator then rewrites all 1397 lines with CRLF. The content is
    # byte-identical; only the invisible line endings differ. git diff prints
    # nothing while git status calls the file modified.
    #
    # The consequence chain, measured 2026-09-02: pre-commit sees the map dirty
    # on EVERY run, regenerates and stages it, so every branch carries a
    # whitespace-only change to a 1400-line file. Any two branches then conflict
    # on it. Resolving that conflict edits the branch, which moves its patch-id,
    # which unbinds the external review that was anchored to the old one. Six
    # open branches were waiting on re-review for this and nothing else.
    #
    # The checker never saw it: read_text normalises line endings on the way in,
    # so it compares LF against LF and correctly reports no drift. An instrument
    # that could not see the fault it was measuring, which is the shape of most
    # of this week.
    OUTPUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"Wrote {OUTPUT.relative_to(ROOT)}")
    # Said here rather than written there: true of this machine, at this moment.
    print(local_usage_report())
    return 0


if __name__ == "__main__":
    sys.exit(main())
