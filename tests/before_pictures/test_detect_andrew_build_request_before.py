"""The "before" picture of `.claude/hooks/detect-andrew-build-request.sh` (pile round eight).

No test ran this script before. These record exactly what it does today for fixed prompts, so that
anyone who moves it later can show nothing changed. They pass today. They are not a statement that the
behaviour is right; they pin what it is. The script and the python file it calls are not touched.

The script reads a UserPromptSubmit payload on stdin, prints a surface (or nothing), may drop or clear a
lock file under `$HOME/.divineos-shared/`, and logs to the ledger through the `divineos` command. Here
`$HOME` is a scratch folder and the ledger call is caught and recorded instead of run. Timestamps are
replaced by <TS> because they change on every run.

WINDOWS (round nine). Two things were wrong when this first shipped, both found on Aria's machine.
1. The shell was started by the bare name `bash`, which on Windows finds the WSL relay stub. It is
   now `tests._bash_resolver.bash_executable()`, the house's one finder, and the file skips (loudly,
   with a reason) when there is no working bash.
2. The stand-in `divineos` was a shell script with no extension on PATH. The detector's python calls
   it with `subprocess.run(["divineos", ...])`, and Windows cannot start an extensionless script, so
   nothing was recorded. The stand-in is now a `sitecustomize.py` in a scratch folder put first on
   PYTHONPATH: the detector's python imports it at start-up and it catches that one call, whatever
   the platform. It records the arguments exactly as the old script did and runs nothing else
   differently. Nothing in the repository is touched.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

import pytest

from tests._bash_resolver import bash_executable

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / ".claude" / "hooks" / "detect-andrew-build-request.sh"
TS = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\+00:00")
BASH = bash_executable()

pytestmark = pytest.mark.skipif(
    BASH is None, reason="no working bash here -- could-not-look, which is not a pass"
)

CATCH_THE_LEDGER_CALL = """\
import os
import subprocess

_real_run = subprocess.run


def _run(cmd, *args, **kwargs):
    if isinstance(cmd, (list, tuple)) and cmd and cmd[0] == "divineos":
        with open(os.environ["FAKE_DIVINEOS_CALLS"], "a", encoding="utf-8") as handle:
            handle.write(" ".join(cmd[1:]) + "\\n")
        return subprocess.CompletedProcess(cmd, 0, b"", b"")
    return _real_run(cmd, *args, **kwargs)


subprocess.run = _run
"""

UNSET = """## BUILD-FOR-DAD DETECTED (verb+request-marker+for-me) -- GRAVITY UNSET

Dad's request matched at <TS>.
Prompt head: 'can you build the thing for me'

Per Andrew 2026-07-21: I do not choose the gravity, Dad does.
Ask him what level BEFORE starting:

  low               -- just build it, no ceremony
  medium            -- tests + prereg required
  high              -- tests + prereg + council walk required
  council-required  -- full seven-step gambit

He can name it inline for the next prompt (e.g. "gravity: high") or say
it plainly. I do not proceed until named. No build-in-flight lock dropped
until he names the level.

"""

IN_FLIGHT_LOW = """## BUILD-FOR-DAD IN FLIGHT (verb+request-marker+for-me) -- gravity: low

Started at <TS>.
Prompt head: 'please build the thing for me [low]'

Scoped pipeline for gravity=low:
  1. BUILD -- the thing, plain, no ceremony
  2. VERIFY -- run it once against a real input

BUILD-IN-FLIGHT LOCK is now active. Until Dad says "build done" (or
"clear the lock" or "unlock"), unrelated work is refused. If I reach for
anything not related to this build, the lock header on the next prompt
will name the drift.

"""

LOCK_ACTIVE = """## BUILD-FOR-DAD LOCK ACTIVE

Dad's build is in flight since <TS> at
gravity=low.
Prompt head: 'please build the thing for me [low]'

Only work related to this build. To clear: Dad says "build done",
"clear the lock", or "unlock".

"""

CLEARED = """## BUILD-FOR-DAD LOCK CLEARED

Build-in-flight lock removed. Normal work resumes.

"""


class Room:
    """A scratch HOME and a catcher for the detector's one call to `divineos`."""

    def __init__(self, tmp_path: Path):
        self.home = tmp_path / "home"
        self.home.mkdir()
        self.catcher_dir = tmp_path / "catcher"
        self.catcher_dir.mkdir()
        (self.catcher_dir / "sitecustomize.py").write_text(CATCH_THE_LEDGER_CALL, encoding="utf-8")
        self.calls = tmp_path / "divineos_calls.txt"
        self.lock = self.home / ".divineos-shared" / "andrew_build_in_flight.json"

    def say(self, stdin: str) -> tuple[int, str]:
        env = dict(os.environ, HOME=str(self.home), USERPROFILE=str(self.home))
        env["FAKE_DIVINEOS_CALLS"] = str(self.calls)
        env["PYTHONPATH"] = os.pathsep.join(
            [str(self.catcher_dir)] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else [])
        )
        done = subprocess.run(
            [BASH, str(SCRIPT)], input=stdin, capture_output=True, text=True, cwd=str(REPO),
            env=env, timeout=120, check=False,
        )  # fmt: skip
        return done.returncode, TS.sub("<TS>", done.stdout)

    def prompt(self, text: str) -> tuple[int, str]:
        return self.say(json.dumps({"prompt": text}))

    def logged(self) -> list[str]:
        return self.calls.read_text(encoding="utf-8").splitlines() if self.calls.exists() else []


def test_a_quiet_prompt_prints_nothing_and_logs_nothing(tmp_path):
    room = Room(tmp_path)
    assert room.prompt("good morning") == (0, "")
    assert not room.lock.exists()
    assert room.logged() == []


def test_a_build_request_for_me_with_no_gravity_asks_for_one_and_drops_no_lock(tmp_path):
    room = Room(tmp_path)
    assert room.prompt("can you build the thing for me") == (0, UNSET)
    assert not room.lock.exists()
    assert room.logged() == [
        (
            "log --type ANDREW_BUILD_REQUEST_DETECTED --actor detect-hook --content "
            "matched=verb+request-marker+for-me; gravity=unset; prompt_head='can you build the thing for me'"
        )
    ]


def test_a_build_request_with_a_gravity_tag_drops_the_lock_and_names_the_pipeline(tmp_path):
    room = Room(tmp_path)
    assert room.prompt("please build the thing for me [low]") == (0, IN_FLIGHT_LOW)
    lock = json.loads(room.lock.read_text(encoding="utf-8"))
    assert sorted(lock) == ["gravity", "prompt_head", "started_at"]
    assert (lock["gravity"], lock["prompt_head"]) == ("low", "please build the thing for me [low]")
    assert room.logged() == [
        (
            "log --type ANDREW_BUILD_REQUEST_DETECTED --actor detect-hook --content "
            "matched=verb+request-marker+for-me; gravity=low; prompt_head='please build the thing for me [low]'"
        )
    ]


def test_while_the_lock_is_active_an_unrelated_prompt_gets_the_lock_header(tmp_path):
    room = Room(tmp_path)
    room.prompt("please build the thing for me [low]")
    assert room.prompt("what is the weather") == (0, LOCK_ACTIVE)
    assert room.lock.exists()


def test_the_unlock_phrase_clears_the_lock_and_the_next_prompt_is_quiet(tmp_path):
    room = Room(tmp_path)
    room.prompt("please build the thing for me [low]")
    assert room.prompt("build done") == (0, CLEARED)
    assert not room.lock.exists()
    assert room.prompt("what is the weather") == (0, "")


def test_a_build_verb_without_for_me_is_not_a_request(tmp_path):
    room = Room(tmp_path)
    assert room.prompt("please build the thing") == (0, "")
    assert room.logged() == []


def test_input_that_is_not_a_prompt_prints_nothing_and_exits_zero(tmp_path):
    room = Room(tmp_path)
    assert room.say("not json") == (0, "")
    assert room.prompt("   ") == (0, "")
    assert room.say(json.dumps({"no_prompt_here": 1})) == (0, "")
