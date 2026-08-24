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

Usage history lives in OS_QUERY events carrying a `tool` field. Nine
distinct commands have ever been recorded, out of 156.

That number is NOT "I use 9 of 156." Commands demonstrably used — filing
corrections, pre-registrations, audit rounds — emit no OS_QUERY at all.
The honest reading is that usage telemetry covers 9 of 156 commands, so
the substrate CANNOT ANSWER which tools are live and which have never
been opened.

That is the sharper finding. A low usage number would be a habit problem.
Blind telemetry is a measurement problem, and it is the reason an unused
tool can sit unnoticed indefinitely: nothing is counting. Every command
below is marked with whether it reports usage at all, so the blind spots
are visible rather than implied.

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


def build() -> str:
    top = _parse_commands(_run_help([]))
    used = _usage_counts()
    instrumented = set(used)

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
    L.append(
        f"Usage history lives in `OS_QUERY` events. **{len(instrumented)} of "
        f"{len(top)} top-level commands have ever been recorded.**"
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
        "indefinitely — nothing is counting. Rows below carry `•` when the "
        "command reports usage at all, so the blind spots are visible rather "
        "than implied."
    )
    L.append("")
    if used:
        L.append("Commands that DO report usage:")
        L.append("")
        L.append("| command | recorded invocations |")
        L.append("|---|---|")
        for name, n in used.most_common():
            L.append(f"| `{name}` | {n} |")
        L.append("")
    L.append("---")
    L.append("")

    L.append("## Commands")
    L.append("")
    L.append(
        "`•` marks a command with usage telemetry. Drilldown: "
        "`divineos <command> --help`."
    )
    L.append("")
    for name, desc, subs in groups:
        mark = " •" if name in instrumented else ""
        L.append(f"### `{name}`{mark}")
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
    L.append("| subsystem | refs | purpose |")
    L.append("|---|---|---|")
    for n, imp, doc in sorted(subsystems, key=lambda s: (-s[1], s[0])):
        L.append(f"| `core/{n}/` | {imp} | {doc} |")
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
    OUTPUT.write_text(text, encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
