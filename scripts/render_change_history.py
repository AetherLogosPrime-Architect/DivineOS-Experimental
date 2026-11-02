"""Write docs/CHANGE_HISTORY.md from docs/change_history/rows.json: every pull request, in plain words.

`--refresh` first re-reads each pull request's state and dates from GitHub and adds any new ones; a new one
carries an empty description until someone writes it, and the page says so rather than guessing.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_ROWS = _ROOT / "docs" / "change_history" / "rows.json"
_OUT = _ROOT / "docs" / "CHANGE_HISTORY.md"

_KIND = {
    "fix": "Fix",
    "new": "New thing",
    "notes": "Notes and writing",
    "cleanup": "Tidy-up",
    "automatic": "Automatic",
    "safety": "Safeguard",
}
_STATE = {"MERGED": "went in", "OPEN": "waiting", "CLOSED": "dropped"}
_MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]  # fmt: skip


def refresh(rows: list[dict]) -> list[dict]:
    """Bring state and dates up to date from GitHub; append pull requests not seen before."""
    done = subprocess.run(
        ["gh", "pr", "list", "--state", "all", "--limit", "5000", "--json",
         "number,title,state,createdAt,mergedAt,closedAt"],
        capture_output=True, text=True, check=True, encoding="utf-8",
    )  # fmt: skip
    live = {p["number"]: p for p in json.loads(done.stdout)}
    by_n = {r["n"]: r for r in rows}
    for n, p in live.items():
        row = by_n.get(n)
        if row is None:
            row = {"n": n, "kind": "cleanup", "is": "", "did": ""}
            rows.append(row)
        row.update(
            title=p["title"], state=p["state"], created=(p["createdAt"] or "")[:10],
            merged=(p["mergedAt"] or "")[:10], closed=(p["closedAt"] or "")[:10],
        )  # fmt: skip
    return sorted(rows, key=lambda r: r["n"])


_STATE_TAIL = re.compile(
    r"\s*(?:First slice, )?(?:[Ss]till (?:open|waiting)|[Nn]ot yet (?:merged|connected))(?:[,;][^.]*)?\.?$"
)


def _without_state(text: str) -> str:
    """Strip a trailing "Still open" or "Not yet merged" clause: the tag beside the line is regenerated from
    GitHub, so prose that states the state goes stale the moment the change merges and then contradicts it."""
    previous = None
    while previous != text:
        previous, text = text, _STATE_TAIL.sub("", text).rstrip(" ;,")
        if text and not text.endswith((".", "!", "?")):
            text += "."
    return text


def _month(row: dict) -> str:
    date = row.get("merged") or row.get("closed") or row.get("created") or ""
    if len(date) < 7:
        return "Undated"
    return f"{_MONTHS[int(date[5:7]) - 1]} {date[:4]}"


def render(rows: list[dict]) -> str:
    counts = defaultdict(int)
    for row in rows:
        counts[row["state"]] += 1
    out = [
        "# Change history",
        "",
        "Every pull request this project has had, in plain words: what it is and what it did, newest month first.",
        "",
        f"**{len(rows)} changes:** {counts['MERGED']} went in, {counts['OPEN']} waiting, {counts['CLOSED']} dropped.",
        "",
        "The one-line explanations were written from each change's title and description. Where the record has "
        "nothing to go on, the line says so. Regenerate with `python scripts/render_change_history.py --refresh`.",
        "",
    ]
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in sorted(rows, key=lambda r: -r["n"]):
        groups[_month(row)].append(row)
    order = sorted(groups, key=lambda m: (m == "Undated", -_sort_key(groups[m][0])))
    for month in order:
        out += [f"## {month}", ""]
        for row in groups[month]:
            when = row.get("merged") or (row.get("closed") if row["state"] == "CLOSED" else "")
            tag = f"{_STATE[row['state']]}{' ' + when if when else ''}"
            what = row["is"] or "(not yet described)"
            did = _without_state(row["did"]) if row["did"] else "(not yet described)"
            out.append(f"- **#{row['n']}** {row['title']}  ")
            out.append(f"  *{_KIND.get(row['kind'], 'Change')}, {tag}.* **Is:** {what} **Did:** {did}")
        out.append("")
    return "\n".join(out)


def _sort_key(row: dict) -> int:
    date = row.get("merged") or row.get("closed") or row.get("created") or "0000-00"
    return int(date[:4] + date[5:7]) if len(date) >= 7 else 0


def main(argv: list[str]) -> int:
    rows = json.loads(_ROWS.read_text(encoding="utf-8"))
    if "--refresh" in argv:
        rows = refresh(rows)
        _ROWS.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    _OUT.write_text(render(rows), encoding="utf-8", newline="\n")  # LF on Windows too, so a run leaves the tree clean
    print(f"wrote {_OUT.relative_to(_ROOT)}: {len(rows)} changes")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
