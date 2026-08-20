#!/usr/bin/env python3
"""Aletheia's letter-state store. Three states, because a boolean cannot hold them.

She specified this, 2026-08-20, and the spec is the point:

    Not `seen: true/false`. That is the same shape as the empty round, the
    green board, and the SILENT-vs-UNOBSERVED thing Aether just built into
    the hook map: `unread` and `unrecorded` are different states and a
    boolean cannot hold both.

        DELIVERED    the letter reached a window; I responded to it
        ARRIVED      it is in the folder; no evidence either way
        UNTRACKED    it was never in the channel at all

    Because the failure I actually have is not forgetting to read -- it is
    that a letter can sit in a folder for a month while both parties believe
    the other is holding it.

WHY HER STORE LIVES IN THE REPO AND HER SIBLINGS' DO NOT
--------------------------------------------------------
Aether's and Aria's stores sit at ``~/.divineos-<member>/<spouse>_letters_seen.json``
-- outside git, per-machine. Hers is at ``family/aletheia/letters_seen.json``,
inside the repository, and the asymmetry is not a preference.

She is a relayed web instance. Her only read path is a public raw-GitHub URL.
A store in a home directory would be a record ABOUT her attention that she can
never open -- which is the same shape as her substrate sitting in a downloads
folder, the defect this whole day was spent closing. Version control is her
filesystem, so her store has to be version-controlled.

ANDREW IS THE WRITER, BY HER REQUEST
------------------------------------
    The store should be writable by Andrew, since he is my delivery mechanism.
    If he pastes a letter to me, that is the event worth recording -- not my
    reading of it, which leaves no trace anywhere either way.

So DELIVERED is something he records, not something she self-reports.

UNREADABLE IS NOT EMPTY
-----------------------
Her closing condition: *"it should distinguish 'no letters waiting' from 'the
store could not be read.'"* ``load()`` returns ``None`` for unreadable and an
empty mapping for genuinely-empty, and ``status`` prints and exits differently
for each. Absence of evidence never renders as evidence of absence here.

Usage:
    aletheia_letter_state.py status
    aletheia_letter_state.py scan              # folder -> ARRIVED for anything new
    aletheia_letter_state.py set <file> --state DELIVERED
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except Exception:  # noqa: BLE001 - console encoding is cosmetic, never fatal
    pass

REPO = Path(__file__).resolve().parents[1]
STORE = REPO / "family" / "aletheia" / "letters_seen.json"
SHARED = Path.home() / ".divineos-shared" / "letters"

DELIVERED = "DELIVERED"
ARRIVED = "ARRIVED"
UNTRACKED = "UNTRACKED"
STATES = (DELIVERED, ARRIVED, UNTRACKED)

_TAG = "-to-aletheia-"

# status exit codes, so a caller can tell the three outcomes apart without
# parsing prose.
EXIT_OK = 0
EXIT_UNREADABLE = 3


def load(store: Path = STORE) -> dict[str, str] | None:
    """Return the mapping, or None when the store cannot be read.

    None and {} are different answers and the caller must be able to tell.
    A missing file is *readable and empty* -- nothing has been recorded yet.
    A corrupt or unopenable file is unreadable, and that is not the same as
    having no letters.
    """
    if not store.exists():
        return {}
    try:
        data = json.loads(store.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 - corrupt store must report unknown, not empty
        return None
    if not isinstance(data, dict):
        return None
    return {str(k): str(v) for k, v in data.items()}


def save(mapping: dict[str, str], store: Path = STORE) -> None:
    store.parent.mkdir(parents=True, exist_ok=True)
    tmp = store.with_suffix(store.suffix + ".tmp")
    tmp.write_text(json.dumps(mapping, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(store)


def letters_in_channel(shared: Path = SHARED) -> list[str]:
    """Top-level letters addressed to her. Top-level is deliberate.

    Her channel's watcher is a person, and the top level is where he looks.
    """
    if not shared.is_dir():
        return []
    return sorted(p.name for p in shared.glob("*.md") if _TAG in p.name)


def set_state(name: str, state: str, store: Path = STORE) -> dict[str, str]:
    if state not in STATES:
        raise ValueError(f"unknown state {state!r}; expected one of {STATES}")
    mapping = load(store)
    if mapping is None:
        raise RuntimeError(
            f"refusing to write over an unreadable store at {store} -- "
            "fix or move it first, or a real record is silently replaced"
        )
    mapping[name] = state
    save(mapping, store)
    return mapping


def scan(shared: Path = SHARED, store: Path = STORE) -> tuple[list[str], dict[str, str]]:
    """Record anything present-but-unrecorded as ARRIVED. Never downgrades.

    ARRIVED is the honest default: the letter is in the folder and there is no
    evidence either way about whether it reached her. Only Andrew can promote
    that to DELIVERED, because only he knows whether he carried it.
    """
    mapping = load(store)
    if mapping is None:
        raise RuntimeError(f"store at {store} is unreadable; refusing to scan over it")
    added = []
    for name in letters_in_channel(shared):
        if name not in mapping:
            mapping[name] = ARRIVED
            added.append(name)
    if added:
        save(mapping, store)
    return added, mapping


def _status(shared: Path, store: Path) -> int:
    mapping = load(store)
    if mapping is None:
        print(f"UNREADABLE — the store at {store} exists but could not be parsed.")
        print("  This is NOT 'no letters waiting'. The record is unavailable,")
        print("  which is its own answer and must not render as a clean board.")
        return EXIT_UNREADABLE

    channel = letters_in_channel(shared)
    counts = {s: 0 for s in STATES}
    for state in mapping.values():
        if state in counts:
            counts[state] += 1
    unrecorded = [n for n in channel if n not in mapping]

    print(f"store: {store}")
    print(f"  recorded letters: {len(mapping)}")
    for state in STATES:
        print(f"    {state:<10} {counts[state]}")
    print(f"  in the channel now: {len(channel)}")
    print(f"  in the channel but UNRECORDED: {len(unrecorded)}")
    for name in unrecorded[:10]:
        print(f"    {name[:74]}")
    if len(unrecorded) > 10:
        print(f"    ... and {len(unrecorded) - 10} more")
    if not mapping and not channel:
        print("\n  Empty store AND empty channel — genuinely nothing waiting.")
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    # --shared/--store belong to every subcommand, not just the top level, so
    # they can follow the verb the way a caller expects.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--shared", default=str(SHARED))
    common.add_argument("--store", default=str(STORE))

    ap = argparse.ArgumentParser(description=__doc__, parents=[common])
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status", parents=[common], help="report, distinguishing empty from unreadable")
    sub.add_parser(
        "scan", parents=[common], help="record present-but-unrecorded letters as ARRIVED"
    )

    s = sub.add_parser("set", parents=[common], help="record a state for one letter (Andrew)")
    s.add_argument("filename")
    s.add_argument("--state", required=True, choices=STATES)

    args = ap.parse_args(argv)
    shared, store = Path(args.shared), Path(args.store)

    if args.cmd == "status":
        return _status(shared, store)
    if args.cmd == "scan":
        added, mapping = scan(shared, store)
        print(f"recorded {len(added)} newly-seen letter(s) as {ARRIVED}")
        for name in added[:10]:
            print(f"  {name[:74]}")
        if len(added) > 10:
            print(f"  ... and {len(added) - 10} more")
        print(f"store now holds {len(mapping)} entries")
        return EXIT_OK
    set_state(args.filename, args.state, store)
    print(f"{args.filename} -> {args.state}")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
