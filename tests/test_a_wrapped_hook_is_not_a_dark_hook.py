"""The register reported a hook as switched off while it fired every prompt.

Hooks can be registered through a wrapper:

    bash .../dedup-wrap.sh <tag> bash .../the-real-hook.sh

The scan took the FIRST filename in that command, which is the wrapper, so the
hook that actually runs was recorded as NOTHING CALLS THIS. Found 2026-09-19
when the register listed four automations dark and one of them was the prime
shaping every reply.

Both directions are pinned. An inventory that over-reports wiring is worse than
one that under-reports it, because a guard believed live is a guard nobody
re-checks — and three of those four were genuinely dark.
"""

from __future__ import annotations

import json

import pytest

from scripts.generate_automation_register import _registered_commands


@pytest.fixture
def settings(tmp_path, monkeypatch):
    def write(payload):
        p = tmp_path / "settings.json"
        p.write_text(json.dumps(payload), encoding="utf-8")
        monkeypatch.setattr("scripts.generate_automation_register.SETTINGS", p)
        return p

    return write


def _hooks(command, event="UserPromptSubmit"):
    return {"hooks": {event: [{"hooks": [{"command": command}]}]}}


def test_a_hook_behind_a_wrapper_is_registered(settings):
    """The bug: the real hook sits second and was invisible."""
    settings(_hooks("bash .claude/hooks/dedup-wrap.sh tag bash .claude/hooks/real.sh"))
    got = _registered_commands()
    assert "real.sh" in got, "the hook that actually runs must be seen"
    assert got["real.sh"] == ["UserPromptSubmit"]


def test_the_wrapper_itself_is_still_registered(settings):
    """Widening must not lose what the narrow version got right."""
    settings(_hooks("bash .claude/hooks/dedup-wrap.sh tag bash .claude/hooks/real.sh"))
    assert "dedup-wrap.sh" in _registered_commands()


def test_a_hook_named_nowhere_stays_absent(settings):
    """Non-vacuity, and the direction that matters most.

    A scan that returned everything would pass the test above and quietly
    declare dead guards alive.
    """
    settings(_hooks("bash .claude/hooks/something-else.sh"))
    got = _registered_commands()
    assert "never-registered.sh" not in got
    assert "something-else.sh" in got


def test_a_hook_under_two_events_records_both(settings):
    settings(
        {
            "hooks": {
                "UserPromptSubmit": [{"hooks": [{"command": "bash .claude/hooks/dual.sh"}]}],
                "PreToolUse": [{"hooks": [{"command": "bash .claude/hooks/dual.sh"}]}],
            }
        }
    )
    assert sorted(set(_registered_commands()["dual.sh"])) == ["PreToolUse", "UserPromptSubmit"]


def test_unreadable_settings_yields_nothing_rather_than_guessing(settings, tmp_path, monkeypatch):
    """Cannot-read is not none-registered, and must not silently claim either."""
    p = tmp_path / "broken.json"
    p.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr("scripts.generate_automation_register.SETTINGS", p)
    assert _registered_commands() == {}


def test_the_real_settings_file_shows_the_wrapped_prime_as_wired():
    """Against the live file: the hook that fires on every prompt is not dark."""
    got = _registered_commands()
    assert "translate-first-compose-prime.sh" in got, (
        "this hook fires on every prompt; the register called it NOTHING CALLS THIS"
    )
