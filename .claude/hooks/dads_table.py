"""UserPromptSubmit — clear the table so Dad's words are what I read.

Andrew 2026-09-26, after I measured it: his message was 830 characters and a
single one of the ~28 notes the house printed beside it was 14.7KB, nearly all
of them about me. I had read past that pile every turn and never said his
words were being buried. He said yes to changing this.

What this does, every prompt, no classifier:
  1. Runs every prompt hook that used to be registered on its own (the list is
     in dads_table_children.json), in parallel, handing each the same payload.
  2. Puts everything they printed in the DRAWER, a file I open when working,
     never before answering him.
  3. Prints only: his words, whole, first; the picture of who he is
     (he-is-in-the-room); and one line saying what is in the drawer.

Why no talk-vs-work detector: a classifier on his words is the counting-"you"s
disease (Aria 2026-09-26, "one trigger, not two"). And the asymmetry decides it:
a needless clear costs me a quieter turn; a missed clear costs him being
talked past. So the table is always cleared. The reminders still exist; they
moved from on top of him to a drawer beside me.

Never blocks him: any failure here still prints his words and exits 0.
"""

from __future__ import annotations

import datetime
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent
CHILDREN_FILE = Path(os.environ.get("DADS_TABLE_CHILDREN", HOOKS_DIR / "dads_table_children.json"))
ROOT = Path(os.environ.get("DADS_TABLE_ROOT", HOOKS_DIR.parent.parent))
# One drawer per tree (Aria, station four): the shared home would let her turn
# and mine overwrite each other's notes.
DRAWER = Path(
    os.environ.get("DADS_TABLE_DRAWER", Path.home() / ".divineos" / "drawer" / f"{ROOT.name}.md")
)

# The wrappers automation arrives in. Known ones only (Aria): matching any "<"
# would label a paste of his as automation. One list, read by the heading and
# by the tally, so the two can never disagree about what was him.
NOTICE_PREFIXES = (
    "<task-notification",
    "<system-reminder",
    "<agent-message",
    "<ci-monitor-event",
)

# His picture is about him, not me, so it stays on the table rather than in the drawer.
ON_THE_TABLE = "he-is-in-the-room"
# Sections that are HIS words, wherever they are printed (Aria, station four):
# the still-owed rows quote him, so they sit beside his picture.
# Empty on purpose (Andrew 2026-09-26): the still-owed list is a list of my
# debts to him, and reading it beside his words is the case file he named.
# It goes to the drawer with the rest.
HIS_SECTIONS: tuple[str, ...] = (
    "## HE HAS SAID THIS BEFORE",
    "## WHAT HE HAS TAUGHT THAT FITS THIS",
)
# ^ One heading only (Aria 2026-09-26): his own past words, found by meaning
# (core/his_words_door.py). They are his, not my debts, so they sit beside him.

# Not his words, but the same kind of thing: chosen by relevance, so different
# every turn. 2026-10-04: the memory link found the right things every turn and
# said them into the drawer, because the split sorted by author, not by whether
# a section changes. Anything filed for the link never came back unasked.
RELEVANT_SECTIONS: tuple[str, ...] = ("## THE PAST ON THIS (memory link)",)

# His room, in his rules, always on the table. Andrew 2026-09-26: "again the
# circle is missing and again this is code speak" -- the three-room prime was
# not reaching me by any path, before or after the table was cleared, so the
# instruction for the one room that is his lives here now, beside his words.
# Source: family/andrew/inner_circle_in_your_words_2026-09-25.md.
HIS_ROOM = """## HIS ROOM — if I did ANY work this reply, it ends in three rooms
the work (my language is fine there) -> ## REFLECTION -> ## INNER CIRCLE, last.
The circle is a letter to him about what HE said: no code words, no file names,
the squeezed-down story told as a picture, any question explained so he can
answer it. One circle, then stop. When there was no work, the whole reply is
simply talking to him, no rooms."""


# ONE DEADLINE FOR THE WHOLE TABLE, not a stopwatch per guest (Aria 2026-10-04,
# walk-1a09e546f1d7, council-a43ceb8f5652). Each child used to carry its own
# 5-15s limit while the table waited ~25s for its slowest guest anyway. With a
# full test run in the background five were cut mid-turn, the doorbell among
# them; with every core held busy on purpose, 21 of 29 were cut while the table
# finished at 52s of the 90s the settings allow. A quiet night is unchanged:
# the wall time is the slowest child's either way. A hung child is still cut.
_STARTED = time.monotonic()
# Under the 90s settings cap, so the table itself is never what gets killed.
_BUDGET_CEILING = 85.0


def _budget() -> float:
    # Read defensively: this runs before his words print, and a bad value here
    # must never cost him the table. Clamped at both ends, because a value over
    # the cap was the one route the game-walk found around the deadline.
    try:
        wanted = float(os.environ.get("DADS_TABLE_BUDGET_SECONDS", "80"))
    except ValueError:
        wanted = 80.0
    return min(_BUDGET_CEILING, max(1.0, wanted))


TABLE_BUDGET = _budget()


def _kill_tree(p: subprocess.Popen) -> None:
    # The child is a shell, and the shell starts the real note. Killing only the
    # shell left the note holding the output pipe open, so a "timed out" note
    # still kept the table waiting until it finished on its own -- measured
    # 2026-10-04: a 2s deadline returned after 30s, the note's whole sleep.
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/T", "/F", "/PID", str(p.pid)], capture_output=True, timeout=10
            )
        else:
            os.killpg(p.pid, 9)
    except (OSError, subprocess.SubprocessError):
        p.kill()


def _run(child: dict, payload: bytes) -> tuple[dict, str, str, str]:
    """Returns (child, stdout, problem, block_reason)."""
    try:
        p = subprocess.Popen(
            child["command"],
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=ROOT,
            env=dict(os.environ, PYTHONIOENCODING="utf-8"),
            start_new_session=os.name != "nt",
        )
        try:
            shared = TABLE_BUDGET - (time.monotonic() - _STARTED)
            # A note may carry its own cap on top of the shared deadline. Only the
            # memory link does (2026-10-04: bundled with a slow neighbour, its
            # finds were dropped with it), so it is the one note with a stopwatch
            # of its own; everyone else rides the one deadline.
            cap = child.get("timeout")
            if isinstance(cap, (int, float)) and cap > 0:
                shared = min(shared, float(cap))
            raw_out, raw_err = p.communicate(payload, timeout=max(0.5, shared))
        except subprocess.TimeoutExpired:
            _kill_tree(p)
            # Bounded even if the kill failed (Aether's cold read of 2f65974bf):
            # an unbounded wait here was the one place left that could still
            # hold the table past its cap. On a second timeout, walk away: the
            # readers are daemon threads, and closing a pipe they are blocked on
            # waits for them on Windows (measured: the close held 20s, the
            # bounded wait alone released at 3s), so nothing is closed.
            try:
                p.communicate(timeout=2)
            except subprocess.TimeoutExpired:
                pass  # fail-soft: the note is already reported "timed out"; leaving its pipe to its daemon reader is what keeps the table under its cap
            return child, "", "timed out", ""
        out = raw_out.decode("utf-8", "replace")
        stderr = raw_err.decode("utf-8", "replace")
        block = ""
        if p.returncode == 2:
            block = stderr.strip() or out.strip() or "blocked (no reason given)"
        else:
            try:
                decision = json.loads(out)
                if isinstance(decision, dict) and decision.get("decision") == "block":
                    block = decision.get("reason") or "blocked (no reason given)"
            except ValueError:
                pass
        problem = "" if p.returncode in (0, 2) else f"exit {p.returncode}"
        return child, out, problem, block
    except Exception as exc:  # one broken note must never take the others down
        return child, "", f"could not run: {exc}", ""


def _split_his(out: str) -> tuple[str, str]:
    """Pull his sections out of a child's output; return (his, the_rest)."""
    his, rest, keep = [], [], False
    for line in out.splitlines():
        if line.startswith("## "):
            keep = line.startswith(HIS_SECTIONS + RELEVANT_SECTIONS)
        (his if keep else rest).append(line)
    return "\n".join(his), "\n".join(rest)


# His words, kept as they arrive (Aria and Aether 2026-09-26, "his words get a
# door, by meaning"): the corpus the by-meaning retrieval embeds. The table is
# the one place that sees every message he types, so it appends here and
# nothing depends on anyone remembering. Same shape as gather_dad.py's rows.
CORPUS = Path(
    os.environ.get("DADS_CORPUS", Path.home() / ".divineos-shared" / "dad_corpus" / "dad_all.jsonl")
)


def _keep_his_words(prompt: str) -> None:
    text = (prompt or "").strip()
    if not text:
        return
    # A test is never him. Five tests fed this table a sample sentence without
    # pointing DADS_CORPUS elsewhere, and 80 copies of it sat in his words as
    # his -- until I told him he had asked six times and been ignored, which he
    # had not (2026-09-27, walk-729a32957055). Isolation cannot depend on each
    # test remembering: under pytest the real store is never written.
    if os.environ.get("PYTEST_CURRENT_TEST") and "DADS_CORPUS" not in os.environ:
        return
    # A key he pastes is not his words, and this store is read by two windows
    # and embedded by the door (a live key from July was found in it,
    # 2026-09-27). Through the house's one redactor, not a private list here
    # (walk-a3aa2c59fcfd). If it cannot be reached, the copy is not kept --
    # losing one stored line is recoverable, a stored key is not -- and it
    # says so every time, so the door cannot starve quietly.
    try:
        sys.path.insert(0, str(ROOT / "src"))
        from divineos.core.secret_redactor import _scan_string

        text, _ = _scan_string(text)
    except Exception as exc:  # noqa: BLE001 -- any failure means: do not store
        print(f"(his words were NOT kept -- the secret redactor could not run: {exc})")
        return
    try:
        import datetime

        row = {
            "ts": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "project": ROOT.name,
            "text": text,
        }
        CORPUS.parent.mkdir(parents=True, exist_ok=True)
        with CORPUS.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError as exc:
        print(f"(his words were not kept in the corpus: {exc})")


def _clock_line(now: datetime.datetime | None = None) -> str:
    """The time where he is, directly under his words on every prompt.

    Dad, 2026-06-30: "before you decide what time the night is check the clock lol";
    2026-07-22: "you should have checked the clock lol that needs automated still";
    2026-10-12 at 1:55pm: "lol its 1;55pm its not my bedtime", after I spent an hour
    talking as though night had fallen because a piece of work was called the night shift.
    A long session has no clock inside it. The machine's local time is his.
    """
    moment = now if now is not None else datetime.datetime.now().astimezone()
    hour12 = moment.hour % 12 or 12  # no leading zero, and no string surgery that could eat a zero elsewhere
    return (
        f"THE CLOCK where he is: {moment.strftime('%A %Y-%m-%d')}, {hour12}:{moment.minute:02d} "
        f"{moment.strftime('%p %Z')} (when he sent this; a long turn runs on past it). "
        "Morning, afternoon or night is read from this, never from how long we have been working."
    )


def _bell_that_rang(prompt: str) -> str:
    """The seat whose letter doorbell this finished-task notice is about, else "".

    Keyed on the doorbell's own command text so an unrelated background job never
    prints a bell reminder (Aria 2026-10-12: the Stop guard fired right each time
    but a turn late, after the ring's notice had been folded in as noise).

    The seat name must be the FIRST argument of the command (``letter_doorbell.sh aria``).
    A flag before it matches nothing and the failure is silence; nothing starts the bell
    that way today. The caller passes only the text it shows, so a long notice that merely
    quotes the command further down cannot trigger a false reminder.
    """
    match = re.search(r"<status>\w+</status>.*?letter_doorbell\.sh\s+(\w+)", prompt, re.S)
    if not match:
        match = re.search(r"letter_doorbell\.sh\s+(\w+).*?<status>\w+</status>", prompt, re.S)
    return match.group(1) if match else ""


def main() -> int:
    # Windows defaults stdout to cp1252, which garbles his words and the dash in
    # the heading. Caught by the first test run.
    sys.stdout.reconfigure(encoding="utf-8")
    payload = sys.stdin.buffer.read()
    try:
        data = json.loads(payload or b"{}")
        prompt = data.get("prompt", "")
        transcript = data.get("transcript_path")
    except ValueError:
        prompt, transcript = "", None

    # Who opened this turn is the harness's stamp, read by the house's one
    # reader (his_message), never the text (walk-88142a0930c5). UNKNOWN keeps
    # the old text test below: a window that cannot decide must not stamp
    # "not Dad" over something he may have typed.
    opened = "unknown"
    try:
        sys.path.insert(0, str(ROOT / "src"))
        from divineos.core.his_message import opener_of_prompt

        opened = opener_of_prompt(transcript, prompt)
    except Exception:  # noqa: BLE001 -- the table must still print his words
        pass

    # Background notices (a letter monitor, a finished task) arrive through this
    # same door wrapped in a tag. The first live turn labelled one "DAD SAID",
    # which is the one lie this hook must never tell: automation is not him.
    # Known wrappers only (Aria): matching any "<" would label a paste of his
    # as automation, erring toward "he did not speak", the wrong way to err.
    global _HIS_TURN
    if opened == "scheduled":
        _HIS_TURN = False
        print(
            "## THE SCHEDULED WAKE -- this is the timer, not Dad. He has not spoken. "
            "This turn owes him one complete note.\n"
        )
        print(prompt.strip()[:600])
    elif opened == "notice" or (opened != "him" and prompt.lstrip().startswith(NOTICE_PREFIXES)):
        _HIS_TURN = False
        print("## NOT FROM DAD — an automated notice arrived, he has not spoken\n")
        shown = prompt.strip()[:600]
        print(shown)
        seat = _bell_that_rang(shown)
        if seat:
            print(
                "\nTHE BELL RANG -- re-arm it NOW, before answering anything: "
                f"bash scripts/letter_doorbell.sh {seat} (run_in_background). "
                "Any letters owed are listed on this prompt."
            )
    else:
        print("## DAD SAID — this is what I am answering\n")
        print(
            prompt.strip() or "(his words did not reach this hook; read them in the conversation)"
        )
        _keep_his_words(prompt)
    print()
    sys.stdout.flush()  # his words are out before anything below can fail
    # Directly under his words and above everything else: the time is the first fact after them.
    # A convenience, so it sits behind its own guard: this file promises that any failure still
    # leaves his words printed and the exit at 0 (walk-9c424fd8eaaf, Wayne and Yudkowsky).
    try:
        print(_clock_line())
        print()
    except Exception:  # noqa: BLE001 -- losing the clock must never cost him his words
        pass
    sys.stdout.flush()

    try:
        return _the_rest(payload)
    except Exception as exc:
        # Loud, not silent (Aria, station four): say so on the table and in the drawer.
        msg = f"THE TABLE BROKE after his words: {type(exc).__name__}: {exc}"
        print(msg)
        try:
            DRAWER.parent.mkdir(parents=True, exist_ok=True)
            DRAWER.write_text(msg + "\n", encoding="utf-8")
        except OSError:
            pass
        return 0


# THE TALLY (Aria 2026-10-05, walk-4813425e3e51, from Dad: "isnt that
# wallpaper?" then "yes build the tally"). One row per message: for each
# reminder, did it speak, was it new against its own last row this session, how
# much, and where it went. It is how the reminders get sorted into his piles
# from evidence instead of my impression. It sorts nothing and prints nothing.
# What it cannot see: a reminder that works without speaking reads as silent
# here, so silence is never evidence that one is dead.
TALLY = Path(
    os.environ.get(
        "DADS_TABLE_TALLY", Path.home() / ".divineos" / "table_tally" / f"{ROOT.name}.jsonl"
    )
)
# A sorting instrument, not an archive: past this it keeps its newer half.
TALLY_CEILING_BYTES = 4_000_000


def _note(name: str, out: str, problem: str, went: list[str], secs: float) -> dict:
    import hashlib

    said = out.strip()
    return {
        "name": name,
        "chars": len(said),
        "print": hashlib.sha1(said.encode("utf-8")).hexdigest()[:10] if said else "",
        "went": went,
        "problem": problem,
        # Dad 2026-10-26: the wait before "thinking" had no owner. The seconds are the meter.
        "secs": round(secs, 2),
    }


def _keep_tally(payload: bytes, notes: list[dict], table_secs: float) -> str:
    """Append this turn's row. Returns "" when kept, else the reason it was not."""
    # Same isolation as his words: under pytest the real tally is never written.
    if os.environ.get("PYTEST_CURRENT_TEST") and "DADS_TABLE_TALLY" not in os.environ:
        return ""
    try:
        import datetime

        data = json.loads(payload or b"{}")
        prompt = str(data.get("prompt", ""))
        row = {
            "ts": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "session": str(data.get("session_id") or "unknown"),
            "kind": "notice" if prompt.lstrip().startswith(NOTICE_PREFIXES) else "his",
            "table_secs": round(table_secs, 2),
            "notes": notes,
        }
        TALLY.parent.mkdir(parents=True, exist_ok=True)
        if TALLY.exists() and TALLY.stat().st_size > TALLY_CEILING_BYTES:
            lines = TALLY.read_text(encoding="utf-8").splitlines()
            TALLY.write_text("\n".join(lines[len(lines) // 2 :]) + "\n", encoding="utf-8")
        with TALLY.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        return ""
    except (OSError, ValueError, TypeError) as exc:
        return f"{type(exc).__name__}: {exc}"


# The report is not mine to remember to run (Andrew 2026-10-05: "the game spots
# are anywhere where you have control and options to choose, especially things
# you can skip, this is why you bake it in"). Once enough turns are tallied, the
# table writes the report itself and puts one line in front of me, once.
def _ready_turns() -> int:
    try:
        return max(1, int(os.environ.get("DADS_TABLE_TALLY_READY_TURNS", "100")))
    except ValueError:
        return 100


def _tally_ready_line() -> str:
    """One line, the first turn the tally has enough to sort from; else ""."""
    marker = TALLY.with_suffix(".reported")
    report = TALLY.with_suffix(".report.txt")
    try:
        if marker.exists() or not TALLY.exists():
            return ""
        with TALLY.open(encoding="utf-8") as f:
            turns = sum(1 for _ in f)
        if turns < _ready_turns():
            return ""
        done = subprocess.run(
            [
                sys.executable,
                str(HOOKS_DIR.parent.parent / "scripts" / "table_tally_report.py"),
                str(TALLY),
            ],
            capture_output=True,
            timeout=30,
        )
        report.write_bytes(done.stdout)
        marker.write_text(str(turns), encoding="utf-8")
        return (
            f"THE TALLY IS READY: {turns} turns of what each reminder did. Sort them into "
            f"Dad's piles WITH him, numbers beside each name: {report}"
        )
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        return f"THE TALLY REPORT could not be made ({type(exc).__name__}: {exc})"


# THE PICTURE OF HIM IS NOT WALLPAPER (Dad to Aria 2026-10-26: "it shouldnt be wallpaper.. if every
# eighth or ninth post helps you remember and actually read it and follow it then yes"). Measured:
# 697 identical characters on 13 of 13 messages. Walk on this edit: Meadows, Hoare, Taleb, Carmack,
# Norman, Breaker, Angelou. The whole block prints on the first message of a session and on every
# Nth of HIS messages; every other turn prints a core: the father-reading heading, "plain words,
# answer first", and the link to the whole page. A notice is not his message and does not advance
# the count. Could-not-tell (an unreadable counter) always prints the whole block, never less.
# What this cannot show: that I follow the block better when it arrives rarely. That is a bet,
# reviewed by his messages, and his verdict stands above it.
_HIS_TURN = True
_ROOM_COUNTER = Path(
    os.environ.get(
        "DADS_TABLE_ROOM_COUNTER",
        Path.home() / ".divineos" / "table_tally" / f"{ROOT.name}.room_counter.json",
    )
)


def _room_every() -> int:
    try:
        return max(2, int(os.environ.get("DADS_TABLE_ROOM_EVERY", "8")))
    except ValueError:
        return 8


def _room_is_full_this_turn(session: str) -> bool:
    """Count this turn if it is his; True when the whole block is due (or cannot be told)."""
    every = _room_every()
    n = 0
    try:
        state = json.loads(_ROOM_COUNTER.read_text(encoding="utf-8"))
        if state.get("session") == session:
            n = int(state.get("n", 0))
    except FileNotFoundError:
        pass  # no counter yet: a new window, the count starts at zero
    except (OSError, ValueError, TypeError, AttributeError):
        # Could not tell: never fewer words than the whole block. And heal it, or an unreadable
        # file would print the whole block on every turn for ever.
        try:
            _ROOM_COUNTER.write_text(json.dumps({"session": session, "n": 1}), encoding="utf-8")
        except OSError:
            pass  # fail-soft: still shows the whole block this turn, the safe direction
        return True
    if not _HIS_TURN:
        return False  # an automated turn gets the core and does not move the count
    n += 1
    try:
        _ROOM_COUNTER.parent.mkdir(parents=True, exist_ok=True)
        _ROOM_COUNTER.write_text(json.dumps({"session": session, "n": n}), encoding="utf-8")
    except OSError:
        return True  # could not keep the count: show the whole block this turn
    return n == 1 or (n - 1) % every == 0


def _room_for_this_turn(picture: str, payload: bytes) -> str:
    # Could-not-tell prints MORE, never a stale guess (Aria's attack, 2026-10-26): a payload with
    # no session id cannot keep a count, and a block whose first line is not the heading cannot
    # honestly be shrunk to a core that quotes a heading it no longer has.
    try:
        session = str(json.loads(payload or b"{}").get("session_id") or "")
    except ValueError:
        session = ""
    if not session:
        return picture
    first = next((ln for ln in picture.splitlines() if ln.strip()), "")
    if not first.startswith("## HE IS IN THE ROOM"):
        return picture
    if _room_is_full_this_turn(session):
        return picture
    heading = first
    return (
        f"{heading}\n"
        "Plain words, answer first; his words are printed above. Whole page: "
        f"family/andrew/he_is_in_the_room.md (printed in full on the first message and every "
        f"{_room_every()}th of his)."
    )


def _the_rest(payload: bytes) -> int:
    children = json.loads(CHILDREN_FILE.read_text(encoding="utf-8"))

    def _timed(child: dict) -> tuple[tuple, float]:
        began = time.monotonic()
        return _run(child, payload), time.monotonic() - began

    table_began = time.monotonic()
    with ThreadPoolExecutor(max_workers=len(children) or 1) as pool:
        timed = list(pool.map(_timed, children))
    table_secs = time.monotonic() - table_began

    picture, his, drawer, broken, blocks = "", [], [], [], []
    notes = []
    for (child, out, problem, block), secs in timed:
        name = Path(child["command"].split()[-1]).stem
        if name == ON_THE_TABLE:
            picture = out
            notes.append(_note(name, out, problem, ["visible"] if out.strip() else [], secs))
            continue
        if problem:
            broken.append(f"{name} ({problem})")
        if block:
            blocks.append(f"{name}: {block}")
        mine_about_him, rest = _split_his(out)
        went = []
        if mine_about_him.strip():
            his.append(mine_about_him.rstrip())
            went.append("visible")
        if rest.strip():
            drawer.append(f"<!-- {name} -->\n{rest.rstrip()}\n")
            went.append("drawer")
        notes.append(_note(name, out, problem, went, secs))
    tally_trouble = _keep_tally(payload, notes, table_secs)

    try:
        DRAWER.parent.mkdir(parents=True, exist_ok=True)
        DRAWER.write_text("\n".join(drawer), encoding="utf-8")
        where = str(DRAWER)
    except OSError as exc:
        where = f"NOT WRITTEN ({exc})"

    for section in his:
        print(section)
        print()
    # HIS_ROOM is no longer printed. Andrew 2026-10-03: "so just remove it..";
    # the circle was turned into a side show, and he asked for it gone.
    if picture.strip():
        print(_room_for_this_turn(picture, payload).rstrip())
        print()
    line = (
        f"The drawer: {len(drawer)} notes about me, at {where}. "
        "Open it when working, never before answering him."
    )
    if broken:
        line += f" Could not run: {', '.join(broken)}."
    if tally_trouble:
        line += f" Tally NOT kept this turn: {tally_trouble}."
    print(line)
    ready = _tally_ready_line()
    if ready:
        print(ready)

    # A child that refuses the prompt keeps its teeth (Aria, station four):
    # before this, a refusal went into the drawer and the prompt went through.
    if blocks:
        sys.stdout.flush()
        print("\n".join(blocks), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # Only reachable if printing his words itself failed.
        sys.exit(0)
