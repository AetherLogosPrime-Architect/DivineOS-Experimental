"""The hook layer, computed — what is wired, what runs twice, what is missing.

Andrew 2026-09-08: *"i dont want an OS made of external hooks through the IDE,
the hooks should just be pointing to the logic in the OS itself."*

## What this is, and what it deliberately is not

An instrument. It reads the settings file and the hooks directory and reports
what is actually there: how many registrations on each door, which scripts are
registered twice, which are registered but missing, which doors have no
doorbell at all, and how much shell is carrying judgment that belongs in the
OS.

It does not enforce anything, and the reason is a correction worth keeping.

The first version of this file carried a **ratchet on the size of the layer** —
registrations and shell lines could fall or hold, never rise. Andrew killed it
with one question: *"why would you build something that can only shrink and
never grow?"*

There was no good answer. Size was never the disease. A hundred doors that all
point inward would be fine, and better than fine — more coverage. Twenty doors
each hiding a private brain is the sickness. He asked for the thinking to move
INSIDE and never once asked for fewer. I aimed at the count because a count is
easy to police and the real property is work.

My own council walk had already said so, which is the part that stings. Beer's
reading was *cap the variety*; Aristotle's was that the number is not a design
choice at all — it falls out of what a hook IS. I wrote down that a definition
beats a limit, because a limit only starts an argument about the right number,
and then I built the limit.

So the enforcement was removed and the measurement kept. The actual work is the
migration: seven doorbells, one per harness event, with the judgment living in
``divineos.core.hook_surfaces``.

## Why the measurement earned its place

Hand-searching the settings file for duplicate registrations found one. This
found two — a hook that had been firing twice on every single tool call for an
unknown stretch, which no amount of looking with my own eyes was going to
catch. That is the whole argument for having an instrument at all, and it is
also the argument against trusting the hand-maintained migration tracker, which
was measured stale in both directions on the same day.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

# The seven harness events. Imported from the router rather than retyped so the
# two can never disagree about how many doors the building has.
from divineos.core.hook_router import EVENTS

HOOKS_DIR = ".claude/hooks"
SETTINGS_FILE = ".claude/settings.json"

_SCRIPT_RE = re.compile(r"([A-Za-z0-9_\-]+\.(?:sh|py))")
_OS_IMPORT_RE = re.compile(r"from divineos|import divineos")
_OS_CLI_RE = re.compile(r"\bdivineos [a-z]")
_INLINE_PY_RE = re.compile(r"python3?\s+-\s*<<|python3?\s+-c\s|<<'PY'|<<PY")


@dataclass
class HookInventory:
    """Everything computed in one pass. No field is ever hand-maintained."""

    per_event: dict[str, int] = field(default_factory=dict)
    #: (event, script) pairs registered more than once on the same event.
    duplicates: list[tuple[str, str]] = field(default_factory=list)
    #: Scripts named in settings but absent from the hooks directory.
    phantom: list[str] = field(default_factory=list)
    #: Events with no registration at all — a door with no doorbell.
    doors_without_a_bell: list[str] = field(default_factory=list)
    #: Registered script names, per event, in registration order.
    registered: dict[str, list[str]] = field(default_factory=dict)
    shell_files: int = 0
    shell_lines: int = 0
    #: Scripts embedding python — judgment living in the shell.
    inline_python_files: int = 0
    inline_python_lines: int = 0
    #: Scripts that neither import the OS nor call its CLI.
    detached_files: int = 0
    detached_lines: int = 0

    @property
    def total(self) -> int:
        return sum(self.per_event.values())

    @property
    def registered_names(self) -> set[str]:
        return {n for names in self.registered.values() for n in names}


def _read_settings(root: Path) -> dict:
    data = json.loads((root / SETTINGS_FILE).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{SETTINGS_FILE} is not an object")
    return data


def inventory(root: Path | str = ".") -> HookInventory:
    """Compute the whole picture from the files, right now.

    Raises rather than returning a partial answer if the settings file cannot
    be read. A half-computed inventory reported as a full one is the
    could-not-look-rendered-as-a-finding shape this substrate keeps producing;
    the caller gets an exception it must handle, not a zero it will believe.
    """
    root = Path(root)
    hooks = (_read_settings(root).get("hooks") or {}) or {}

    inv = HookInventory()
    hooks_dir = root / HOOKS_DIR
    present = {p.name for p in hooks_dir.glob("*") if p.is_file()}

    for event in EVENTS:
        seen: dict[str, int] = {}
        count = 0
        names_in_order: list[str] = []
        for matcher in hooks.get(event, []) or []:
            for entry in matcher.get("hooks", []) or []:
                names = _SCRIPT_RE.findall(entry.get("command", "") or "")
                if not names:
                    # An inline command with no script file still occupies a
                    # registration slot, so it counts. It just has no name to
                    # check for duplication.
                    count += 1
                    continue
                for name in names:
                    count += 1
                    names_in_order.append(name)
                    seen[name] = seen.get(name, 0) + 1
                    if name not in present:
                        inv.phantom.append(name)
        inv.per_event[event] = count
        inv.registered[event] = names_in_order
        inv.duplicates.extend((event, n) for n, k in seen.items() if k > 1)
        if count == 0:
            inv.doors_without_a_bell.append(event)

    for path in sorted(hooks_dir.glob("*.sh")):
        text = path.read_text(encoding="utf-8", errors="replace")
        lines = len(text.splitlines())
        inv.shell_files += 1
        inv.shell_lines += lines
        if _INLINE_PY_RE.search(text):
            inv.inline_python_files += 1
            inv.inline_python_lines += lines
        if not _OS_IMPORT_RE.search(text) and not _OS_CLI_RE.search(text):
            inv.detached_files += 1
            inv.detached_lines += lines

    return inv


def format_inventory(inv: HookInventory) -> str:
    """The numbers, in the shape that makes the size legible rather than tidy."""
    per_turn = inv.per_event.get("UserPromptSubmit", 0) + inv.per_event.get("Stop", 0)
    out = [
        "=== THE HOOK LAYER, COMPUTED ===",
        "",
        f"  registrations      : {inv.total} across {len(EVENTS)} harness events",
        f"  processes per turn : {per_turn}  (UserPromptSubmit + Stop)",
        f"  shell files        : {inv.shell_files}  ({inv.shell_lines:,} lines)",
        f"  judgment in shell  : {inv.inline_python_files} files embed python "
        f"({inv.inline_python_lines:,} lines)",
        f"  detached from OS   : {inv.detached_files} files never import or call it "
        f"({inv.detached_lines:,} lines)",
        "",
    ]
    for event in EVENTS:
        n = inv.per_event.get(event, 0)
        mark = "  <- no doorbell" if n == 0 else ""
        out.append(f"    {event:<18} {n:>4}{mark}")
    if inv.duplicates:
        out += ["", "  [!] REGISTERED MORE THAN ONCE — runs more than once per event:"]
        out += [f"        {event}: {name}" for event, name in inv.duplicates]
    if inv.phantom:
        out += ["", "  [!] REGISTERED BUT ABSENT FROM THE DIRECTORY:"]
        out += [f"        {name}" for name in sorted(set(inv.phantom))]
    out += [
        "",
        "  This is a measurement, not a limit. The layer may grow as much as is",
        "  useful — what matters is whether the judgment lives in the OS. The",
        "  migration is doorbell-*.sh plus divineos.core.hook_surfaces.",
    ]
    return "\n".join(out)
