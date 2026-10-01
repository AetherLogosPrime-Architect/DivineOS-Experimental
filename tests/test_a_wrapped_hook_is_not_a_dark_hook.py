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
from pathlib import Path

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


HOOKS = Path(__file__).resolve().parents[1] / ".claude" / "hooks"


def test_unreadable_settings_yields_nothing_rather_than_guessing(settings, tmp_path, monkeypatch):
    """Cannot-read is not none-registered, and must not silently claim either."""
    p = tmp_path / "broken.json"
    p.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr("scripts.generate_automation_register.SETTINGS", p)
    assert _registered_commands() == {}


# Hooks that are dark ON PURPOSE. A name is listed here only when the hook
# itself carries the decision in its own text, so this list cannot be used to
# excuse a hook that is dark by accident -- the excuse has to live next to the
# thing it excuses.
INTENTIONALLY_UNWIRED = {"translate-first-compose-prime.sh"}


def test_an_unwired_hook_says_so_in_its_own_first_lines():
    """The register calling a hook dark is a FINDING or a DECISION, never a guess.

    REWRITTEN 2026-09-22, because the test that stood here asserted the exact
    opposite of a deliberate choice and would have had me undo it.

    It read: "this hook fires on every prompt; the register called it NOTHING
    CALLS THIS" -- and demanded the hook be wired. The hook's own first six
    lines say INTENTIONALLY UNWIRED (2026-09-07), with the reason and Andrew's
    words under it: "you should not be loading up failure patterns.. just fix
    the damn failures with structure." A reminder about a failure is proof the
    failure is not fixed; the failure it warned about is refused at Stop by a
    real check instead.

    So the earlier test was written without reading the file it was about, and
    the only way to make it pass was to switch something back on that had been
    switched off on purpose. A test that can only be satisfied by undoing a
    documented decision is not a guard, it is a trap.

    What is actually worth enforcing is the thing that was almost enforced by
    accident: a hook nothing calls must SAY it is uncalled on purpose. That
    catches a genuinely forgotten hook -- which is what the register's
    NOTHING CALLS THIS is for -- while leaving a deliberate one alone.
    """
    wired = _registered_commands()
    for name in sorted(INTENTIONALLY_UNWIRED):
        assert name not in wired, (
            f"{name} is listed as intentionally unwired but something calls it "
            "now. Either the wiring is a mistake, or the decision changed and "
            "this list and the hook's own header both need updating."
        )
        body = (HOOKS / name).read_text(encoding="utf-8", errors="replace")
        assert "INTENTIONALLY UNWIRED" in body, (
            f"{name} is dark and does not say why in its own text. A hook that "
            "is off for a reason and a hook that was forgotten look identical "
            "from the register; only the file itself can tell them apart."
        )
