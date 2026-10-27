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

import errno
import json
import sys
from collections.abc import Callable
from pathlib import Path

from divineos.core import his_lessons_shelf as shelf
from divineos.core import his_words_door as door

if sys.platform == "win32":
    import msvcrt
else:
    import fcntl

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
_BUILD_LOCK_NAME = ".build.lock"
_BUSY_ERRNOS = {errno.EACCES, errno.EAGAIN, errno.EDEADLK}


def _try_lock(fh) -> bool:
    """Take the operating system's own lock on the file, without waiting. False if someone holds it.

    The same call suite_slot.py makes, for the same reason (Aletheia's hold on #686 and again on #736,
    2026-10-28): nobody ever judges whether a holder is dead or slow. The system releases the lock the
    instant the holding process ends, however it ends, and a build that is merely slow keeps it. A
    lock file with an age had both defects: a check and then a write with a gap between them, and a
    slow build presumed dead and run twice beside itself."""
    try:
        if sys.platform == "win32":
            fh.seek(0)
            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as exc:
        # Only "someone else holds it" means busy; a read-only folder or a bad handle never clears.
        if exc.errno in _BUSY_ERRNOS:
            return False
        raise
    return True


def _unlock(fh) -> None:
    if sys.platform == "win32":
        fh.seek(0)
        msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


def _step(job: Callable[[], str], when_it_fails: str) -> str:
    """One step, its own try. Any failure is spoken under that step's heading, never swallowed."""
    try:
        return job()
    except Exception:  # noqa: BLE001 -- by design: a step's failure must be said, and must not stop the next step
        return when_it_fails


def _behind_note(count: int, started: bool) -> str:
    """Said aloud, with the number, so a stale index is never mistaken for a search that found nothing."""
    where = (
        "A build is running in the background and will finish without holding this turn up."
        if started
        else "A build is already running in the background, or could not be started."
    )
    return (
        "## HIS WORDS INDEX IS NOT FULLY UP TO DATE THIS TURN\n"
        f"{count} of his passages are not indexed yet, so the search below may miss some of his words. "
        f"{where}\n"
    )


def start_background_build(
    corpus: Path, door_index: Path, verified: Path, reread: Path, shelf_index: Path
) -> bool:
    """Start the index build in a separate process that outlives this one; False if one is running.

    The build embeds many passages at once and needs the heavy embedder (about eight seconds just to
    start; the light one takes 31 ms a passage, one at a time), which is why it never runs inside the
    prompt: Dad 2026-10-28, the wait before I think. Whether one is running is answered by the
    operating system's lock, which the build itself holds for its whole life: this takes it without
    waiting only to ask, and lets it go again before starting the child. Two prompts close together can
    both start a child; the child takes the lock first thing and the second one leaves at once, so
    two builds never run at the same time, and the guard that matters is the child's, not this one.
    The child is handed the same five paths this process was given, so a test world builds a test
    world and never the real index."""
    import subprocess

    door_index.mkdir(parents=True, exist_ok=True)
    with open(door_index / _BUILD_LOCK_NAME, "a+b") as fh:
        if not _try_lock(fh):
            return False
        _unlock(fh)
    flags = 0
    if sys.platform == "win32":
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    paths = [corpus, door_index, verified, reread, shelf_index]
    subprocess.Popen(  # noqa: S603 -- our own module, fixed argument list
        [sys.executable, "-m", "divineos.core.his_words_bundle", "build", *map(str, paths)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=flags,
        close_fds=True,
    )
    return True


def build_everything(
    corpus: Path = door.CORPUS,
    door_index: Path = door.INDEX_DIR,
    verified: Path = shelf.VERIFIED,
    reread: Path = shelf.REREAD,
    shelf_index: Path = shelf.INDEX_DIR,
) -> int:
    """The work the hook used to do: his lessons, then his words until none are left. Returns passages added."""
    shelf.build(verified, reread, shelf_index)
    added = 0
    while True:
        n = door.build_index(corpus, door_index)
        if n == 0:
            return added
        added += n


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
    spawn: Callable[[Path, Path, Path, Path, Path], bool] | None = None,
) -> str:
    words = _step(lambda: door.surface(prompt, index_dir=door_index), NOT_STARTED_DOOR)
    taught = _step(
        lambda: shelf.surface(prompt, me, index_dir=shelf_index, log=log), NOT_STARTED_SHELF
    )

    def caught_up() -> str:
        # Never builds here: building loads the heavy embedder, which is the wait this folds away.
        # What is behind is counted, a background build is started, and the count is spoken aloud.
        count = door.unindexed(corpus, door_index)
        if count == 0 and shelf.is_current(verified, reread, shelf_index):
            return ""
        start = spawn or start_background_build  # looked up now, so a test can replace it
        return _behind_note(count, start(corpus, door_index, verified, reread, shelf_index))

    behind = _step(caught_up, INDEX_BEHIND)
    return behind + words + taught


def _build_main(args: list[str]) -> bool:
    """The background build: takes the lock first thing and keeps it until it ends, however it ends.

    Returns False without building when another build already holds the lock. The lock file is never
    deleted: the system lets go of the lock when this process ends, and deleting a file someone else
    may now hold is the defect the earlier version had."""
    corpus, door_index, verified, reread, shelf_index = (Path(a) for a in args)
    door_index.mkdir(parents=True, exist_ok=True)
    with open(door_index / _BUILD_LOCK_NAME, "a+b") as fh:
        if not _try_lock(fh):
            return False
        build_everything(corpus, door_index, verified, reread, shelf_index)
        return True


if __name__ == "__main__" and sys.argv[1:2] == ["build"]:
    _build_main(sys.argv[2:])
elif __name__ == "__main__":
    payload = json.loads(sys.stdin.read() or "{}")
    # Bytes, not text: Windows defaults stdout to cp1252, which garbles his words.
    said = run(str(payload.get("prompt", "")), shelf.seat(Path.cwd()))
    sys.stdout.buffer.write(said.encode("utf-8"))
