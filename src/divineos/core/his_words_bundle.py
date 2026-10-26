"""His words and his lessons, found by meaning, in ONE process.

Dad 2026-10-26: the wait before "thinking" is the prompt helpers, and this one started a fresh Python
three times (index build, words search, lessons search), each paying about eight seconds to import the
embedding library. Run here, the library loads once and the three jobs share it. Design and both
council walks: docs/drafts/prompt_helpers_in_one_trip_draft_2026-10-26.md.

What the fold keeps. The words are the same as the two commands said, in the same order. Each step is its
own try: a step that raises is spoken under its own heading and the others still run, so "could not look"
never turns into "found nothing". What it cannot keep (Aria's attack, same day): an exception stays its own,
a hang or a hard crash does not. The deadline for those stays on the whole helper, the table's own cap,
exactly as it was when this was one shell script.

The index build runs LAST, after both searches. His current message is never quoted back to him, so it need
not be in the index before this turn's search; building after the search leaves the first turn after an
index change searching a stale or partial index, which is said aloud, for one turn.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path

from divineos.core import his_lessons_shelf as shelf
from divineos.core import his_words_door as door

NOT_STARTED_DOOR = (
    "## HE HAS SAID THIS BEFORE (found by meaning, his words as he wrote them)\n"
    "Not searched this turn: the search itself failed to start.\n"
)
NOT_STARTED_SHELF = (
    "## WHAT HE HAS TAUGHT THAT FITS THIS (his words, found by meaning)\n"
    "Not searched this turn: the lesson shelf itself failed to start.\n"
)
INDEX_BEHIND = (
    "## HIS WORDS INDEX IS NOT FULLY UP TO DATE THIS TURN\n"
    "It is still catching up, or the update failed. The search below ran on what is indexed so far, "
    "so some of his words may be missing.\n"
)


def _step(job: Callable[[], str], when_it_fails: str) -> str:
    """One step, its own try. Any failure is spoken under that step's heading, never swallowed."""
    try:
        return job()
    except Exception:  # noqa: BLE001 -- by design: a step's failure must be said, and must not stop the next step
        return when_it_fails


def run(
    prompt: str,
    me: str,
    *,
    corpus: Path = door.CORPUS,
    door_index: Path = door.INDEX_DIR,
    verified: Path = shelf.VERIFIED,
    reread: Path = shelf.REREAD,
    shelf_index: Path = shelf.INDEX_DIR,
    log: Path | None = shelf.LOG,
) -> str:
    words = _step(lambda: door.surface(prompt, index_dir=door_index), NOT_STARTED_DOOR)

    def lessons() -> str:
        # A failed lesson build was silent before and stays so: the search below it still runs on
        # whatever is indexed, and says so itself if it cannot.
        try:
            shelf.build(verified, reread, shelf_index)
        except Exception:  # noqa: BLE001 -- by design, see above; the search is what speaks
            pass
        return shelf.surface(prompt, me, index_dir=shelf_index, log=log)

    taught = _step(lessons, NOT_STARTED_SHELF)

    def caught_up() -> str:
        door.build_index(corpus, door_index)
        return "" if door.unindexed(corpus, door_index) == 0 else INDEX_BEHIND

    behind = _step(caught_up, INDEX_BEHIND)
    return behind + words + taught


if __name__ == "__main__":
    payload = json.loads(sys.stdin.read() or "{}")
    # Bytes, not text: Windows defaults stdout to cp1252, which garbles his words.
    said = run(str(payload.get("prompt", "")), shelf.seat(Path.cwd()))
    sys.stdout.buffer.write(said.encode("utf-8"))
