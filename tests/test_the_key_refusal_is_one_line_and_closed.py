"""The push gate's key refusal must be one sentence, never a traceback, and never silence.

Aria's cold read of #597 (2026-10-13): the inline Python that spends the key in
``check-branch-on-push.sh`` is exercised by no test, and its captured output (stderr
included) became the refusal text, so a typo there would print a raw traceback as the
reason. This runs that exact program, cut from the hook file so the test cannot drift
from what fires, against a ledger that cannot be read or is not a seat's, and asserts
the refusal is one plain line.

The refusal must also still REFUSE: empty output here would let a bypass through, so
every case below asserts there is text.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "check-branch-on-push.sh"
SRC = str(Path(__file__).resolve().parents[1] / "src")


def _spend_program() -> str:
    text = HOOK.read_text(encoding="utf-8")
    m = re.search(r'KEY_REFUSAL=\$\(printf .*?-c "\n(.*?)\n" 2>&1\)', text, re.S)
    assert m, "could not find the key-spending program in the hook"
    return m.group(1)


def _run(ledger: str, command: str = "git push -u origin b", raw_input: str | None = None) -> str:
    env = dict(os.environ, DIVINEOS_DB=ledger)
    env["PYTHONPATH"] = SRC + os.pathsep + env.get("PYTHONPATH", "")
    done = subprocess.run(
        [sys.executable, "-c", _spend_program()],
        input=raw_input
        if raw_input is not None
        else json.dumps({"tool_input": {"command": command}}),
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
    )
    return (done.stdout + done.stderr).strip()


def test_an_unreadable_ledger_gives_one_plain_line_not_a_traceback(tmp_path) -> None:
    out = _run(str(tmp_path))  # a directory, not a database: it cannot be opened as one
    assert out, (
        "no text at all: the gate would read this as 'no refusal' and let the bypass through"
    )
    assert "Traceback" not in out
    assert len(out.splitlines()) == 1, out
    assert "key" in out.lower()


def test_a_ledger_with_no_events_table_gives_one_plain_line(tmp_path) -> None:
    import sqlite3

    db = tmp_path / "fresh.db"
    sqlite3.connect(str(db)).close()  # a real, empty database: readable file, no ledger in it
    out = _run(str(db))
    assert out
    assert "Traceback" not in out
    assert len(out.splitlines()) == 1, out


def test_an_error_that_is_not_a_spent_key_is_named_by_class_in_one_line(tmp_path) -> None:
    """The case the old program failed: input that is not JSON raised inside the program
    and the whole traceback became the refusal reason. It is still a refusal, as one line."""
    out = _run(str(tmp_path), raw_input="this is not json")
    assert out, "an error must still refuse: empty output would let the bypass through"
    assert "Traceback" not in out
    assert len(out.splitlines()) == 1, out
    assert "JSONDecodeError" in out or "ValueError" in out


def test_control_the_program_can_find_a_key_state_to_report() -> None:
    # If the cut program were empty or the regex matched nothing, both tests above would
    # fail loudly at the assert in _spend_program; this pins that it contains the call.
    assert "bk.spend('check-branch-on-push'" in _spend_program()
