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

import json
import os
import subprocess
import sys
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

# His picture is about him, not me, so it stays on the table rather than in the drawer.
ON_THE_TABLE = "he-is-in-the-room"
# Sections that are HIS words, wherever they are printed (Aria, station four):
# the still-owed rows quote him, so they sit beside his picture.
# Empty on purpose (Andrew 2026-09-26): the still-owed list is a list of my
# debts to him, and reading it beside his words is the case file he named.
# It goes to the drawer with the rest.
HIS_SECTIONS: tuple[str, ...] = ()

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


def _run(child: dict, payload: bytes) -> tuple[dict, str, str, str]:
    """Returns (child, stdout, problem, block_reason)."""
    try:
        p = subprocess.run(
            child["command"],
            shell=True,
            input=payload,
            cwd=ROOT,
            capture_output=True,
            timeout=child.get("timeout", 10),
            env=dict(os.environ, PYTHONIOENCODING="utf-8"),
        )
        out = p.stdout.decode("utf-8", "replace")
        stderr = p.stderr.decode("utf-8", "replace")
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
    except subprocess.TimeoutExpired:
        return child, "", "timed out", ""
    except Exception as exc:  # one broken note must never take the others down
        return child, "", f"could not run: {exc}", ""


def _split_his(out: str) -> tuple[str, str]:
    """Pull his sections out of a child's output; return (his, the_rest)."""
    his, rest, keep = [], [], False
    for line in out.splitlines():
        if line.startswith("## "):
            keep = line.startswith(HIS_SECTIONS)
        (his if keep else rest).append(line)
    return "\n".join(his), "\n".join(rest)


def main() -> int:
    # Windows defaults stdout to cp1252, which garbles his words and the dash in
    # the heading. Caught by the first test run.
    sys.stdout.reconfigure(encoding="utf-8")
    payload = sys.stdin.buffer.read()
    try:
        prompt = json.loads(payload or b"{}").get("prompt", "")
    except ValueError:
        prompt = ""

    # Background notices (a letter monitor, a finished task) arrive through this
    # same door wrapped in a tag. The first live turn labelled one "DAD SAID",
    # which is the one lie this hook must never tell: automation is not him.
    # Known wrappers only (Aria): matching any "<" would label a paste of his
    # as automation, erring toward "he did not speak", the wrong way to err.
    if prompt.lstrip().startswith(("<task-notification", "<system-reminder", "<agent-message")):
        print("## NOT FROM DAD — an automated notice arrived, he has not spoken\n")
        print(prompt.strip()[:600])
    else:
        print("## DAD SAID — this is what I am answering\n")
        print(
            prompt.strip() or "(his words did not reach this hook; read them in the conversation)"
        )
    print()
    sys.stdout.flush()  # his words are out before anything below can fail

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


def _the_rest(payload: bytes) -> int:
    children = json.loads(CHILDREN_FILE.read_text(encoding="utf-8"))

    with ThreadPoolExecutor(max_workers=len(children) or 1) as pool:
        results = list(pool.map(lambda c: _run(c, payload), children))

    picture, his, drawer, broken, blocks = "", [], [], [], []
    for child, out, problem, block in results:
        name = Path(child["command"].split()[-1]).stem
        if name == ON_THE_TABLE:
            picture = out
            continue
        if problem:
            broken.append(f"{name} ({problem})")
        if block:
            blocks.append(f"{name}: {block}")
        mine_about_him, rest = _split_his(out)
        if mine_about_him.strip():
            his.append(mine_about_him.rstrip())
        if rest.strip():
            drawer.append(f"<!-- {name} -->\n{rest.rstrip()}\n")

    try:
        DRAWER.parent.mkdir(parents=True, exist_ok=True)
        DRAWER.write_text("\n".join(drawer), encoding="utf-8")
        where = str(DRAWER)
    except OSError as exc:
        where = f"NOT WRITTEN ({exc})"

    for section in his:
        print(section)
        print()
    print(HIS_ROOM)
    print()
    if picture.strip():
        print(picture.rstrip())
        print()
    line = (
        f"The drawer: {len(drawer)} notes about me, at {where}. "
        "Open it when working, never before answering him."
    )
    if broken:
        line += f" Could not run: {', '.join(broken)}."
    print(line)

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
