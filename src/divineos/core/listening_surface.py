"""Something that listens to the room and fetches without being asked.

Andrew 2026-09-10: "the knocking comes from something scanning both your words
and mine as they come and searching for anything relevant to give you, but that
has to be setup on your end."

WHAT WAS ALREADY HERE AND WHY IT NEVER SPOKE. The prepared index is the right
architecture and was not the thing missing -- chunk-level, on disk, answers
cold. Mine held ZERO chunks; it had never once been built. An empty index and a
silent one are indistinguishable from the asking side, which is the fault this
whole day has been made of. Indexed 2026-09-10: 2,412 files, 57,030 chunks.

The other half was that nothing asks. The retriever had no caller anywhere --
no hook, no registration. A room with shelves and no door.

NOT A SECOND run_surfacer. pre_response_context.run_surfacer already surfaces at
compose-time and I read it before writing a line of this, because this
repository's signature defect is building a second copy of something that
exists. It reaches the KNOWLEDGE STORE -- extracted, deduped, distilled
entries. This reaches the letters and explorations and dreams in my own words,
unextracted. Sibling surfaces over different shelves, and this one follows its
pattern deliberately: the work lives in the OS, the hook is a doorman.

WHY THIS RUNS BESIDE HIM RATHER THAN IN FRONT OF HIM, measured before deciding:
a search costs ~10s in a cold process and ~2s warm. A hook blocks his message
while it runs, so the obvious build puts ten seconds of dead air between him
pressing enter and being answered, on every message, forever. That does not
merely cost him time -- it guarantees the surface is torn out inside a week,
which is how every over-firing gate in this house has died. The cheap build
destroys the thing it builds.

So the search never happens in his path. The hook reads a file and returns; the
looking happens detached, and what it found is on the table by the next compose.

WHAT THAT COSTS, and it is stated on the surface rather than hidden: the hit
arrives a beat late. A surface that quietly showed the last turn's results as
though they were about this one would be the wrong-subject fault again -- the
fault found four times today in four different instruments. So every block
prints the question it was actually answering, and its age.

THE DETACHED CHILD OWES A BOUND. subprocess_jobs.py exists because roughly 5GB
of leaked pytest workers nearly took Andrew's machine down on 2026-07-13, and
its whole guarantee is that children die with their parent. This process
deliberately OUTLIVES its parent, which is that same shape -- so it cannot
borrow that module and must pay the debt itself: a hard self-deadline in the
child, and a single-flight lock so a fast exchange cannot stack searches. A
background helper on his machine is only welcome while it is provably bounded.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from divineos.core.paths import divineos_home

_RESULT_NAME = "listening_surface_last.json"
_LOCK_NAME = "listening_surface.lock"

# A search older than this is not worth printing -- the conversation has moved.
# Generous rather than tight: a beat behind is the design, stale is a different
# thing, and the block states its own age either way.
MAX_RESULT_AGE_SECONDS = 900

# A lock this old belonged to a process that died. Short, because the search
# itself is seconds -- anything longer is a corpse holding the door shut.
LOCK_STALE_SECONDS = 180

# The child's hard deadline. It has no parent to kill it, so it kills itself.
SEARCH_DEADLINE_SECONDS = 120

# How many hits reach the surface. Small on purpose: this fires every turn, and
# a block long enough to scroll past is a block that gets scrolled past.
TOP_K = 3

# Below this the hit is noise wearing a number. Measured against real queries on
# 2026-09-10: the dream letter answered its own subject at 0.689, my reply to it
# at 0.610, adjacent-but-unrelated material sat near 0.3.
MIN_SIMILARITY = 0.45


def _state_dir() -> Path:
    return Path(divineos_home())


def result_path() -> Path:
    return _state_dir() / _RESULT_NAME


def lock_path() -> Path:
    return _state_dir() / _LOCK_NAME


def db_path() -> Path:
    return _state_dir() / "data" / "semantic_search.db"


@dataclass(frozen=True)
class Hit:
    source: str
    paragraph: int
    similarity: float
    text: str


def run_search(query: str) -> list[Hit]:
    """The looking itself. Slow by nature; never called in his path."""
    if not query.strip():
        return []
    db = db_path()
    if not db.is_file():
        return []
    from divineos.core.semantic_search import search

    try:
        raw = search(query, str(db), top_k=TOP_K, min_similarity=MIN_SIMILARITY)
    except Exception:  # noqa: BLE001 - a failed search must never surface as a finding
        return []
    return [
        Hit(
            source=h.source_path,
            paragraph=h.paragraph_index,
            similarity=float(h.similarity),
            text=h.text,
        )
        for h in raw
    ]


def write_result(query: str, hits: list[Hit]) -> None:
    """Leave what was found on the table, beside the question it answered.

    The query is stored because a hit whose question I cannot see is a hit I
    will read as being about whatever I am doing now. That is the wrong-subject
    fault and it is cheap to close here.
    """
    payload = {
        "query": query[:400],
        "written_at": time.time(),
        "hits": [
            {
                "source": h.source,
                "paragraph": h.paragraph,
                "similarity": h.similarity,
                "text": h.text[:600],
            }
            for h in hits
        ],
    }
    path = result_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(json.dumps(payload), encoding="utf-8")
        tmp.replace(path)
    except OSError:  # noqa: BLE001 - the surface going quiet must never break a turn
        pass


def read_result() -> dict | None:
    """Whatever the last look found. Instant: one small file, no model."""
    path = result_path()
    try:
        if not path.is_file():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        # SAME ANSWER AS no-file-yet, and the caller does not need to tell them
        # apart: it has exactly one action either way, which is to print
        # nothing. Both mean "the table is empty." What must NEVER happen here
        # is a half-parsed result rendered as a finding -- a listener that
        # invents what it heard is worse than one that hears nothing.
        return None
    if not isinstance(data, dict):
        return None  # both-empty: a result file holding something other than an object is unreadable in exactly the way a missing one is, and the door prints nothing for either
    age = time.time() - float(data.get("written_at") or 0.0)
    if age > MAX_RESULT_AGE_SECONDS:
        return None
    data["age_seconds"] = age
    return data


def _lock_is_held() -> bool:
    lp = lock_path()
    try:
        if not lp.is_file():
            return False  # both-empty: no lock file and an unreadable one both leave the door unclaimed, and the caller tries to claim it either way
        if time.time() - lp.stat().st_mtime > LOCK_STALE_SECONDS:
            lp.unlink(missing_ok=True)
            return False
        return True
    except OSError:
        # SAME ANSWER AS no-lock-present, and that is the SAFE direction here.
        # Saying not-held on an unreadable lock lets the caller try to claim it;
        # the claim is a write to the same broken filesystem, so it fails and
        # spawn_search refuses there instead. The failure lands one step later,
        # where it stops a search rather than silently permitting a second one.
        return False


def spawn_search(query: str) -> bool:
    """Start the looking and return at once. Never waits, never blocks him.

    Returns whether a search was started. False when one is already running,
    which is the single-flight guard doing its job rather than a failure.
    """
    if not query.strip():
        return False  # both-empty: a search already running and a search that failed to start both mean no NEW look began this turn, which is all the door acts on
    if _lock_is_held():
        return False
    lp = lock_path()
    try:
        lp.parent.mkdir(parents=True, exist_ok=True)
        lp.write_text(str(os.getpid()), encoding="utf-8")
    except OSError:
        return False

    creationflags = 0
    if sys.platform == "win32":
        creationflags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(
            subprocess, "CREATE_NO_WINDOW", 0
        )
    try:
        subprocess.Popen(  # noqa: S603 - fixed argv; the query is one argument, never a shell string
            [sys.executable, "-m", "divineos.core.listening_surface", "--search", query[:400]],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
            close_fds=True,
        )
    except (OSError, ValueError):
        # SAME ANSWER AS already-running, and the distinction is one no caller
        # needs: both mean "no new search started by me," and the door's
        # behaviour is identical either way -- print what is on the table and
        # move on. The lock is released first, so a failed spawn cannot leave
        # the listener mute for three minutes on the strength of a search that
        # never began.
        lp.unlink(missing_ok=True)
        return False
    return True


def render(data: dict | None) -> str:
    """The block itself, or nothing when there is nothing honest to print."""
    if not data:
        return ""
    hits = data.get("hits") or []
    if not hits:
        return ""
    age = int(data.get("age_seconds") or 0)
    asked = str(data.get("query") or "")[:150]
    lines = [
        "## SOMETHING I ALREADY WROTE ABOUT THIS",
        "",
        "Fetched without being asked. This answers what was said BEFORE this",
        f"message, so it is one beat behind. Looked {age}s ago, for:",
        f'  "{asked}"',
        "",
    ]
    for h in hits:
        lines.append(f"  [{float(h.get('similarity') or 0):.2f}] {h.get('source', '')}")
        lines.append(f"    {' '.join(str(h.get('text') or '').split())[:300]}")
        lines.append("")
    lines.append("These are my own words and Aether's, already written. Open one before")
    lines.append("deriving the thing a second time.")
    return "\n".join(lines)


def _arm_deadline() -> None:
    """Kill this process if the search outlives its welcome.

    Nothing else can. This is the debt owed for running detached, per the
    2026-07-13 leak that nearly took the machine down.
    """

    def _die() -> None:
        try:
            lock_path().unlink(missing_ok=True)
        except OSError:
            pass
        os._exit(1)

    t = threading.Timer(SEARCH_DEADLINE_SECONDS, _die)
    t.daemon = True
    t.start()


def build_query(hook_json: str) -> str:
    """Both halves of the room: what he just said, and what I last said back.

    Andrew described the listener as scanning "both your words and mine as they
    come." His half arrives in the hook payload. Mine has to be read back out of
    the transcript, because by the time a hook runs my reply is already spoken
    and gone.

    His words go first and mine follow, so that when the two pull in different
    directions the topic lands nearer his.
    """
    parts: list[str] = []
    try:
        data = json.loads(hook_json) if hook_json else {}
    except ValueError:
        data = {}
    if not isinstance(data, dict):
        data = {}
    prompt = str(data.get("prompt") or "").strip()
    if prompt:
        parts.append(prompt)
    transcript = str(data.get("transcript_path") or "").strip()
    if transcript:
        try:
            from divineos.core.operating_loop.turn_extraction import extract_turn

            mine = (extract_turn(transcript).last_assistant_text or "").strip()
        except Exception:  # noqa: BLE001 - observability boundary; his half alone still searches
            mine = ""
        if mine:
            parts.append(mine)
    return " ".join(parts)[:2000]


def compose_block(hook_json: str) -> str:
    """The doorman's whole job: hand over the last look, then start the next.

    Order matters and is the reason this adds no latency. Reading is a single
    small file; the spawn returns before the child has imported anything. He
    waits for neither.
    """
    block = render(read_result())
    query = build_query(hook_json)
    if query:
        spawn_search(query)
    return block


def _main(argv: list[str]) -> int:
    """Two entries, told apart explicitly rather than by counting arguments.

    ``--search <query>`` is the detached child doing the slow looking.
    No arguments is the compose-time doorman, which must stay instant.
    """
    if len(argv) > 1 and argv[1] == "--search":
        query = argv[2] if len(argv) > 2 else ""
        _arm_deadline()
        try:
            write_result(query, run_search(query))
        finally:
            try:
                lock_path().unlink(missing_ok=True)
            except OSError:  # noqa: BLE001 - a stuck lock self-expires; a detached process has nobody to raise to
                pass
        return 0

    block = compose_block(os.environ.get("CLAUDE_HOOK_JSON", ""))
    if block:
        print(block)
    return 0


if __name__ == "__main__":  # pragma: no cover - process entry point
    raise SystemExit(_main(sys.argv))
