"""A finding the his-state door detects must reach the next compose.

Aether's reading of the repacked #507, 2026-09-23: the repack left
``stop_carry`` in the archive. ``run_state_check`` imports it inside a bare
``except``, so a real finding was detected and then dropped in silence -- and
every test still passed, because none drove the path through to a carried
finding. This one does, end to end, so a missing helper fails a test instead of
going quiet.
"""

from __future__ import annotations

import json

from divineos.hooks import stop_carry
from divineos.hooks.his_state_claim_hook import GATE_NAME, run_state_check


def _him(text: str) -> str:
    return json.dumps(
        {"type": "user", "userType": "external", "message": {"role": "user", "content": text}}
    )


def _me(text: str) -> str:
    return json.dumps(
        {"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}
    )


def test_a_claim_about_his_body_he_never_raised_is_carried(tmp_path, monkeypatch):
    carry_file = tmp_path / "carry.jsonl"
    monkeypatch.setenv("DIVINEOS_STOP_CARRY", str(carry_file))
    transcript = tmp_path / "t.jsonl"
    transcript.write_text(
        "\n".join(
            [
                _him("go work with Aether on the pile.. the branches need sorting out"),
                _me("You have been awake for almost a full day, so I will hold the question."),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = run_state_check(str(transcript))

    # Carried, not blocked: the return value is what reaches his window.
    assert result is None
    findings = stop_carry.pending()
    assert findings, "the finding was detected and then lost -- the exact fault this pins"
    assert findings[-1].gate == GATE_NAME


def test_his_own_mention_of_sleep_carries_nothing(tmp_path, monkeypatch):
    carry_file = tmp_path / "carry.jsonl"
    monkeypatch.setenv("DIVINEOS_STOP_CARRY", str(carry_file))
    transcript = tmp_path / "t.jsonl"
    transcript.write_text(
        "\n".join(
            [
                _him("im pretty tired tonight, been up since early"),
                _me("You have been awake for almost a full day, so I will hold the question."),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    assert run_state_check(str(transcript)) is None
    assert stop_carry.pending() == []


def test_the_rest_of_is_not_him_raising_rest(tmp_path, monkeypatch):
    """Bare 'rest' was 788 of 1,162 subject hits across his messages (Aether)."""
    carry_file = tmp_path / "carry.jsonl"
    monkeypatch.setenv("DIVINEOS_STOP_CARRY", str(carry_file))
    transcript = tmp_path / "t.jsonl"
    transcript.write_text(
        "\n".join(
            [
                _him("do the rest of the branches after that one"),
                _me("You have been awake for almost a full day, so I will hold the question."),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    assert run_state_check(str(transcript)) is None
    assert stop_carry.pending(), "'the rest of' silenced the door as if he had raised rest"
