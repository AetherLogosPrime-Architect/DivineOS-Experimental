"""What each reminder at Dad's table has actually been doing, from the tally.

For sorting the reminders into his piles (Andrew 2026-10-05): visible because
they rotate and matter, structure, linked by meaning, or removed with his yes.
This prints evidence for that conversation and decides nothing.

Per reminder: turns seen, how often it spoke, how often what it said was NEW
against its own last row in the same session, where it went (in front of me or
the drawer), average size, and problems. Silence is reported as silence: a
reminder can work without speaking, so there is deliberately no removal column.

    python scripts/table_tally_report.py [path-to-tally.jsonl]
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path


def default_tally() -> Path:
    root = Path(__file__).resolve().parents[1]
    return Path.home() / ".divineos" / "table_tally" / f"{root.name}.jsonl"


def read_rows(path: Path) -> tuple[list[dict], int]:
    """(rows, unreadable_lines). A bad line is counted, never fatal."""
    rows, bad = [], 0
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            bad += 1
    return rows, bad


def summarize(rows: list[dict]) -> dict[str, dict]:
    stats: dict[str, dict] = defaultdict(
        lambda: {"seen": 0, "spoke": 0, "new": 0, "chars": 0, "visible": 0, "drawer": 0, "problems": 0}
    )
    last: dict[tuple[str, str], str] = {}
    for row in rows:
        session = row.get("session", "unknown")
        for note in row.get("notes", []):
            s = stats[note["name"]]
            s["seen"] += 1
            if note.get("problem"):
                s["problems"] += 1
            fingerprint = note.get("print", "")
            if not fingerprint:
                continue
            s["spoke"] += 1
            s["chars"] += note.get("chars", 0)
            key = (session, note["name"])
            if last.get(key) != fingerprint:
                s["new"] += 1
            last[key] = fingerprint
            for place in note.get("went", []):
                if place in ("visible", "drawer"):
                    s[place] += 1
    return dict(stats)


def render(stats: dict[str, dict], turns: int, bad: int) -> str:
    lines = [f"{turns} turns tallied" + (f", {bad} unreadable line(s) skipped" if bad else "")]
    lines.append(f"{'reminder':38} {'seen':>5} {'spoke':>6} {'new':>5} {'visible':>8} {'drawer':>7} {'avg':>6} {'probl':>6}")
    for name, s in sorted(stats.items(), key=lambda kv: (-kv[1]["spoke"], kv[0])):
        avg = s["chars"] // s["spoke"] if s["spoke"] else 0
        lines.append(
            f"{name[:38]:38} {s['seen']:>5} {s['spoke']:>6} {s['new']:>5} "
            f"{s['visible']:>8} {s['drawer']:>7} {avg:>6} {s['problems']:>6}"
        )
    lines.append("spoke=0 means silent here, not dead: some reminders act without speaking.")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    path = Path(argv[1]) if len(argv) > 1 else default_tally()
    if not path.exists():
        print(f"no tally yet at {path}")
        return 1
    rows, bad = read_rows(path)
    print(render(summarize(rows), len(rows), bad))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
