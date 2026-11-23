"""A saved memory is made findable by the house, not by me remembering.

MINE, I built it, and why. Dad, 2026-11-10: "you are trying to remember things the house can EASILY do for
you" and "having a note pop up that says go run X, isnt as useful as literally making the check tool do it for
you automatically". The failure this prevents: I write a memory file, the memory link cannot search it until
its vector is computed (`divineos linkage warm`), and only the end-of-day sleep or my typing the command did
that, so a new memory was invisible for hours.

What it does: when a tool writes a markdown file inside this project's Claude memory folder, it starts
`warm()` once, in the background. What decides it is a FACT (the path written to), never words. Several saves
in a row start ONE run that covers them (a second save during a run leaves a pending flag and the run goes
round again). Every start and every finish is logged, and the finish records whether EACH saved file now has a
stored vector, read back from the drawer, so a silent miss reads as a miss.

It opens no window on Dad's screen: the background run uses the no-window creation flag (the house refuses
anything else, because windows over his screen once left him typing blind).

Three states, kept apart: not a memory file (nothing, silently), started or queued, could-not-start (said on
stderr and in the log, never blocking the write).

Walked 2026-11-10 (walk-ac6c21fea147). Known gap, named: a memory written by a shell command rather than the
Write, Edit or MultiEdit tool is never seen by the hook; the sleep warm stays as the floor.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

LOCK_STALE_SECONDS = 30 * 60
MAX_ROUNDS = 3


def state_dir() -> Path:
    """The seat's OWN home (``divineos_home()``), never a folder two seats share.

    Found 2026-11-23: this was ``~/.divineos`` for everyone, so Aria's and Aether's saves went into one queue
    under one lock and one log, while each run verified against the memory folder of whichever seat's process
    happened to be running. A save by one seat queued behind the other's run ended ``verified: false`` with
    ``computed 0``. One home per seat, one queue per home.
    """
    from divineos.core.paths import divineos_home

    return divineos_home()


def _seat() -> str:
    """Whose run this is, as a plain fact for the log: the declared member, else the name of the home."""
    return os.environ.get("DIVINEOS_MEMBER") or state_dir().name


def _paths(base: Path | None = None) -> dict[str, Path]:
    d = base or state_dir()
    return {
        "log": d / "memory_warm_log.jsonl",
        "lock": d / "memory_warm.lock",
        "pending": d / "memory_warm.pending",
        "queue": d / "memory_warm.queue",
        "off": d / "memory_warm.off",
    }


def memory_dir() -> Path:
    from divineos.core.memory_linkage_retriever import _memory_files_dir

    return _memory_files_dir()


def is_memory_file(path: str | Path, directory: Path | None = None) -> bool:
    """True for a markdown file directly inside the memory folder, other than the MEMORY.md index."""
    try:
        p = Path(path).resolve()
        folder = (directory or memory_dir()).resolve()
    except OSError:
        return False
    return p.parent == folder and p.suffix == ".md" and p.name != "MEMORY.md"


def _log(entry: dict, base: Path | None = None) -> None:
    log = _paths(base)["log"]
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"t": time.time(), "seat": _seat(), **entry}) + "\n")


def _lock_is_live(lock: Path) -> bool:
    try:
        return (time.time() - lock.stat().st_mtime) < LOCK_STALE_SECONDS
    except OSError:
        return False


def _runner_python(root: Path | None = None) -> str:
    """This checkout's own sealed Python, never the machine's global one.

    The global install of divineos can point at a different checkout (found 2026-11-10: the first live run
    died with 'No module named divineos.core.memory_saved_warm' and logged 'started'), so the run must use the
    venv that belongs to the tree this file lives in. ``root`` is for tests; it defaults to that tree.
    """
    root = root or Path(__file__).resolve().parents[3]
    for candidate in (root / ".venv" / "Scripts" / "python.exe", root / ".venv" / "bin" / "python"):
        if candidate.is_file():
            return str(candidate)
    return sys.executable


def _spawn_runner(base: Path | None) -> None:
    """Start the run in the background, with no window, so the reply never waits on the embedder loading."""
    env = dict(os.environ)
    if base is not None:
        env["DIVINEOS_WARM_STATE_DIR"] = str(base)
    flags = 0
    if os.name == "nt":
        flags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
    logf = (_paths(base)["log"].parent / "memory_warm_runner.out").open("ab")
    subprocess.Popen(  # noqa: S603 - fixed argument list, our own module
        [_runner_python(), "-m", "divineos.core.memory_saved_warm", "--run"],
        stdout=logf,
        stderr=logf,
        stdin=subprocess.DEVNULL,
        creationflags=flags,
        close_fds=True,
        env=env,
    )


def on_write(
    path: str | Path,
    directory: Path | None = None,
    base: Path | None = None,
    spawn=_spawn_runner,
) -> str:
    """Called after a tool wrote `path`.

    Returns 'not-a-memory-file', 'switched-off', 'started', 'queued' or 'could-not-start'. A file named
    ``memory_warm.off`` in the seat's home switches the warm off without a code or settings change; the row it
    leaves in the log says it was switched off and not that it failed.
    """
    if not is_memory_file(path, directory):
        return "not-a-memory-file"
    p = _paths(base)
    try:
        if p["off"].exists():
            _log({"event": "switched-off", "file": Path(path).name}, base)
            return "switched-off"
    except OSError:
        pass  # an unreadable switch is not a reason to refuse to file a note
    try:
        p["queue"].parent.mkdir(parents=True, exist_ok=True)
        # A queue left behind with no live run means the last run died without finishing (a background child
        # cannot report its own failure). Say so now; the names stay queued and this run picks them up.
        if p["queue"].exists() and p["queue"].stat().st_size > 0 and not _lock_is_live(p["lock"]):
            left = [
                ln.strip()
                for ln in p["queue"].read_text(encoding="utf-8").splitlines()
                if ln.strip()
            ]
            _log({"event": "previous-run-left-the-queue", "files": sorted(set(left))}, base)
        with p["queue"].open("a", encoding="utf-8") as fh:
            fh.write(Path(path).name + "\n")
        if _lock_is_live(p["lock"]):
            p["pending"].write_text("1", encoding="utf-8")
            _log({"event": "queued", "file": Path(path).name}, base)
            return "queued"
        if p["lock"].exists():
            p["lock"].unlink()  # a run that died: the lock is stale, take it over
        spawn(base)
        _log({"event": "started", "file": Path(path).name}, base)
        return "started"
    except Exception as exc:  # noqa: BLE001 - said, never swallowed
        try:
            _log(
                {
                    "event": "could-not-start",
                    "file": Path(path).name,
                    "why": f"{type(exc).__name__}: {exc}",
                },
                base,
            )
        except OSError:
            pass
        print(
            f"  [memory-saved-warm] COULD NOT START: {type(exc).__name__}: {exc}", file=sys.stderr
        )
        return "could-not-start"


def _take_lock(lock: Path) -> bool:
    try:
        fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False
    os.write(fd, str(os.getpid()).encode())
    os.close(fd)
    return True


def _read_and_clear_queue(queue: Path) -> list[str]:
    try:
        names = [ln.strip() for ln in queue.read_text(encoding="utf-8").splitlines() if ln.strip()]
        queue.unlink()
    except OSError:
        return []
    return sorted(set(names))


def _files_with_vectors() -> set[str]:
    """Names of memory files the link can search right now (a file with no stored vector is skipped by the loader)."""
    from divineos.core import memory_linkage_retriever as r

    return {item.path for item in r._load_memory_files()}


def run(base: Path | None = None, warm=None, have_vectors=None) -> None:
    """The background job: take the lock, warm, read back per file, log; go round again if saves came meanwhile."""
    p = _paths(base)
    p["lock"].parent.mkdir(parents=True, exist_ok=True)
    if p["lock"].exists() and not _lock_is_live(p["lock"]):
        p["lock"].unlink()
    if not _take_lock(p["lock"]):
        p["pending"].write_text("1", encoding="utf-8")
        return
    try:
        if warm is None:
            from divineos.core import memory_linkage_retriever as r
            from divineos.core.memory_linkage_retriever_v2 import install

            install()
            warm = r.warm
        have_vectors = have_vectors or _files_with_vectors
        for _round in range(MAX_ROUNDS):
            if p["pending"].exists():
                p["pending"].unlink()
            names = _read_and_clear_queue(p["queue"])
            started = time.perf_counter()
            try:
                out = warm()
                have = have_vectors()
                _log(
                    {
                        "event": "done",
                        "files": names,
                        "computed": (out or {}).get("computed"),
                        "verified": {n: (n in have) for n in names},
                        "seconds": round(time.perf_counter() - started, 1),
                    },
                    base,
                )
            except Exception as exc:  # noqa: BLE001 - logged, the sleep warm stays as the floor
                _log(
                    {"event": "run-error", "files": names, "why": f"{type(exc).__name__}: {exc}"},
                    base,
                )
            if not p["pending"].exists() and not p["queue"].exists():
                break
    finally:
        try:
            p["lock"].unlink()
        except OSError:
            pass


if __name__ == "__main__":
    base_env = os.environ.get("DIVINEOS_WARM_STATE_DIR")
    if "--run" in sys.argv:
        run(Path(base_env) if base_env else None)
