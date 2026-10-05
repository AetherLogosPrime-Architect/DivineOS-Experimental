"""The state shown before a substrate change, as a glance instead of a wall.

Andrew 2026-10-05: "for wallpaper like that that is needed but is too large you
compress it with a link to the rest so it can be seen and looked at deeper when
needed but doesnt clog you up or waste tokens." The full reports printed on
every substrate change, about thirty times in one night, and the corrections
numbers never moved once. Now: one line per report, marked CHANGED when it
differs from the last time it was shown, with the whole text one link away.

Pure on purpose (Dijkstra, walk-abf55981f852): the hook does the reading and
writing; this decides what the glance says, so it can be tested.

Known edge (Schneier, same walk): a report that embeds a ticking clock would be
marked CHANGED every time, and the flag would become wallpaper again.
"""

from __future__ import annotations

import hashlib

FIRST_LINE_CHARS = 160


def _title_and_first(block: str) -> tuple[str, str]:
    lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
    title = lines[0].lstrip("# ").strip() if lines else "(untitled)"
    first = next((ln for ln in lines[1:] if not ln.startswith(("#", "("))), "")
    return title, first[:FIRST_LINE_CHARS]


NEW_LINES_SHOWN = 3


def glance(blocks: list[str], seen: dict) -> tuple[list[str], dict]:
    """(one line per report, the updated last-seen record).

    A report is CHANGED when its text differs from the last time it was shown,
    or when it has never been shown -- first sight is news. A changed report
    also shows up to three of its NEW lines, because the first line can be a
    total ticking up by one while the news is the row underneath: a fresh
    correction of his, in his words, must not hide behind an old first line
    (the embarrassing reading of prereg-e1f0ea9f7175).
    """
    lines, now = [], dict(seen)
    for block in blocks:
        title, first = _title_and_first(block)
        digest = hashlib.sha1(block.encode("utf-8")).hexdigest()[:12]
        body = [ln.strip() for ln in block.splitlines() if ln.strip()]
        changed = seen.get(title) != digest
        lines.append(f"- {title}{' [CHANGED]' if changed else ''}: {first}")
        before = seen.get(f"{title}::lines")
        if changed and isinstance(before, list):
            fresh = [ln for ln in body if ln not in set(before) and ln != first]
            lines += [f"    + {ln[:FIRST_LINE_CHARS]}" for ln in fresh[:NEW_LINES_SHOWN]]
        now[title] = digest
        now[f"{title}::lines"] = body
    return lines, now
