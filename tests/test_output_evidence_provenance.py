"""Only MACHINE-produced output counts as evidence.

Aether, 2026-08-11, with a specimen he had already committed:

    "Write an unverified claim into a file. Later, read that file. The claim's
     text is now in this turn's tool output. The gate goes quiet. My own
     fabrication has become its own verification."

His actual instance: he wrote "verified end-to-end at exit code 2" into a test
exemption as the justification for not wiring a gate further. It was false —
the hook was returning 0. Under the first version of the suppressor, Reading
that file would have silenced the gate on exactly that sentence.

The property that makes it worse than a normal hole: it REWARDS putting claims
in files. A fabrication living only in a reply stays catchable; one committed
to a docstring becomes permanently self-verifying.
"""

from __future__ import annotations

import json
from pathlib import Path

from divineos.core.operating_loop_audit import _extract_turn_tool_outputs

FABRICATION = "verified end-to-end at exit code 2"


def _transcript(tmp_path: Path, tool: str, command: str | None, body: str) -> str:
    inp = {"command": command} if command is not None else {"file_path": "tests/test_x.py"}
    records = [
        {"message": {"content": [{"type": "tool_use", "id": "u1", "name": tool, "input": inp}]}},
        {"message": {"content": [{"type": "tool_result", "tool_use_id": "u1", "content": body}]}},
    ]
    p = tmp_path / "transcript.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")
    return str(p)


def _counts(tmp_path: Path, tool: str, command: str | None, body: str) -> bool:
    return any(
        body in o for o in _extract_turn_tool_outputs(_transcript(tmp_path, tool, command, body))
    )


def test_reading_my_own_fabrication_is_not_evidence(tmp_path):
    """Aether's exploit, verbatim. This is the test that had to exist."""
    assert _counts(tmp_path, "Read", None, FABRICATION) is False


def test_catting_the_file_through_a_shell_is_not_evidence(tmp_path):
    """His tool-name filter alone leaves this open: `cat` is typed text
    wearing an execution tool's clothes."""
    assert _counts(tmp_path, "Bash", "cat tests/test_x.py", FABRICATION) is False


def test_grep_result_is_not_evidence(tmp_path):
    assert _counts(tmp_path, "Grep", None, FABRICATION) is False


def test_machine_output_still_counts(tmp_path):
    """The gate must keep working. Over-filtering here would make every claim
    unverifiable and the suppressor pointless."""
    assert _counts(tmp_path, "Bash", "python -m pytest -q", "11046 passed") is True


def test_unresolvable_origin_is_not_evidence(tmp_path):
    """A result whose originating tool cannot be identified is not proof of
    anything — absence of provenance is not provenance."""
    records = [
        {
            "message": {
                "content": [
                    {"type": "tool_result", "tool_use_id": "orphan", "content": FABRICATION}
                ]
            }
        }
    ]
    p = tmp_path / "orphan.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")
    assert _extract_turn_tool_outputs(str(p)) == []


def test_file_echo_pattern_does_not_over_match():
    """A pattern too broad would discard real command output as 'typed'."""
    from divineos.core.operating_loop_audit import _FILE_ECHO_CMD

    assert _FILE_ECHO_CMD.search("cat notes.md")
    assert _FILE_ECHO_CMD.search("cd /x && cat notes.md")
    assert not _FILE_ECHO_CMD.search("python -m pytest -q")
    assert not _FILE_ECHO_CMD.search("concatenate.py --run")
