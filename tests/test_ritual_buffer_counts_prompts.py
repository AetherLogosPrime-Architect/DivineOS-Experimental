"""The ritual's grace buffer is spent by HIS prompts, never by my tool calls.

Dad, 2026-10-16: the hard block must not interrupt mid-flow; it is a buffer. The
buffer was three prompts of grace, but the same script also runs before every
tool call of mine, and the counter went up on both. Three tool calls spent it
and the wall landed in the middle of a task.

These drive the LIVE hook against a transcript past the start line. The pair is
the point: "a tool call does not spend grace" alone is satisfied by a counter
that never counts; "his prompt does" proves it still counts.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
HOOK = REPO / ".claude" / "hooks" / "auto-cycle-token-trigger.sh"


def _bash() -> str | None:
    for candidate in (
        r"C:\Program Files\Git\bin\bash.exe",
        "/usr/bin/bash",
        shutil.which("bash") or "",
    ):
        if candidate and Path(candidate).exists() and "System32" not in candidate:
            return candidate
    return None


BASH = _bash()
pytestmark = pytest.mark.skipif(
    not HOOK.exists() or BASH is None,
    reason="hook or a POSIX bash absent here -- could-not-look, which is not a pass",
)

# Past the 850k start, under the 890k hard line: the buffer is in play.
IN_THE_BUFFER = 860_000


def _transcript(tmp_path: Path, tokens: int) -> Path:
    path = tmp_path / "session.jsonl"
    row = {
        "type": "assistant",
        "message": {"usage": {"input_tokens": tokens, "output_tokens": 0}},
    }
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    return path


def _run(tmp_path: Path, transcript: Path, event: str) -> None:
    env = {
        **os.environ,
        "AUTO_CYCLE_STATE_DIR": str(tmp_path),
        "AUTO_CYCLE_HOOK_EVENT": event,
        "DIVINEOS_PYTHON": sys.executable,
    }
    payload = json.dumps({"transcript_path": str(transcript), "prompt": "hi"})
    subprocess.run(
        [BASH, str(HOOK)],
        input=payload.encode(),
        capture_output=True,
        env=env,
        cwd=REPO,
        timeout=120,
    )


def _defers_used(tmp_path: Path, transcript: Path) -> int:
    key = hashlib.sha1(str(transcript).encode()).hexdigest()[:12]
    state = tmp_path / f"ritual_{key}.json"
    if not state.exists():
        return 0
    return int(json.loads(state.read_text(encoding="utf-8")).get("defers_used") or 0)


def test_a_tool_call_does_not_spend_the_buffer(tmp_path):
    tx = _transcript(tmp_path, IN_THE_BUFFER)
    for _ in range(4):
        _run(tmp_path, tx, "PreToolUse")
    assert _defers_used(tmp_path, tx) == 0


def test_his_prompt_does_spend_the_buffer(tmp_path):
    tx = _transcript(tmp_path, IN_THE_BUFFER)
    _run(tmp_path, tx, "UserPromptSubmit")
    assert _defers_used(tmp_path, tx) == 1


def test_the_numbers_dad_named():
    text = HOOK.read_text(encoding="utf-8")
    assert "AUTO_CYCLE_FIRE_TOKENS:-850000" in text
    assert "AUTO_CYCLE_HARD_TOKENS:-890000" in text
