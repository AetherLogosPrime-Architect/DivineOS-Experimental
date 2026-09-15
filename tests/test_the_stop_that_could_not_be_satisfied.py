"""The freeze Andrew reported twice, and the path that outlived its own fix.

His words, unchanged: *"for some reason that same freezing keeps happening
where you never start thinking and the stopping just loops til i end the
program and restart it."*

A Stop hook that exits 2 sends the turn back for another try. If whatever made
it refuse cannot be changed by writing a different reply, the next try refuses
for the identical reason, and the only exits are his hand on the program or
luck. A refusal that cannot be satisfied is a hang wearing a guard's coat.

That was diagnosed on 2026-08-03 and repaired in the correction-shape hook,
whose comment then stated it was "the only Stop hook that exits 2". Measured
2026-09-14 by listing them: the Stop doorbell exits 2 as well and had no guard.
A live path to his freeze survived the fix by six weeks, protected by a
sentence nobody had checked.

THE DISTINCTION THESE TESTS PIN, because it is the whole design:

  a surface's verdict  CAN be cleared by writing a different reply -> keep blocking
  a failed import      CANNOT be cleared by anything I write       -> refuse once, then say so

Standing down on every retry would have been the easy version and it would
have quietly made every Stop surface advisory on its second firing. The narrow
version disarms nothing that can terminate on its own.

WHAT THESE TESTS ARE AND ARE NOT. They assert the SHAPE of the source, not the
runtime behaviour, because reaching the real path needs a genuinely broken
install and faking one here would test the fake. So: this catches the guard
being deleted, or drifting out of the import handler and becoming a blanket
stand-down. It does not catch the guard being present and wrong. Saying that
plainly rather than letting the file look like more coverage than it is.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
HOOKS = REPO / ".claude" / "hooks"
HOOK = HOOKS / "doorbell-stop.sh"


def test_the_hook_exists_where_the_settings_say_it_does():
    """Control, and it comes first: every assertion below reads this file, so
    a wrong path would make the whole file pass by finding nothing."""
    assert HOOK.exists(), HOOK
    settings = json.loads((REPO / ".claude" / "settings.json").read_text(encoding="utf-8"))
    stop_entries = json.dumps(settings.get("hooks", {}).get("Stop", []))
    assert "doorbell-stop.sh" in stop_entries


def test_the_guard_sits_inside_the_import_failure_handler():
    text = HOOK.read_text(encoding="utf-8")
    assert "stop_hook_active" in text, "the retry guard is gone entirely"

    before, _, after = text.partition("if payload.get('stop_hook_active')")
    assert after, "guard is not written against the payload"

    # It must sit INSIDE the import-failure handler: after its NOT RUNNING
    # line and before the refusal. Drifting above the handler turns it into a
    # blanket stand-down and disarms the router path with it.
    assert "NOT RUNNING" in before, "guard moved above the import handler"
    assert "REFUSING" in after, "guard moved below the refusal it must precede"


def test_the_router_path_is_deliberately_left_blocking():
    """The half that would be silently lost.

    A surface verdict terminates -- I write a different reply and it clears. A
    blanket stand-down would make every Stop surface advisory on the second
    try, which is worse than the freeze: it passes unchecked replies routinely
    instead of hanging loudly once.
    """
    text = HOOK.read_text(encoding="utf-8")
    _, _, after_router = text.partition("sys.exit(main('Stop', payload))")
    assert after_router, "the router call is gone; this test is measuring nothing"
    assert "stop_hook_active" not in after_router, (
        "a guard appeared on the router path; surface verdicts can be cleared "
        "by writing a different reply and must keep blocking"
    )


def test_the_refusal_still_refuses_on_a_first_pass():
    """The guard must not have turned the hook into a no-op. With the retry
    flag unset, a broken import still has to produce a refusal."""
    text = HOOK.read_text(encoding="utf-8")
    _, _, after_guard = text.partition("if payload.get('stop_hook_active')")
    assert "sys.exit(2)" in after_guard, "the hook can no longer refuse at all"


def test_it_names_what_it_is_letting_through():
    """A silent stand-down is the worse bug: an unchecked reply that looks
    checked. The banner is what makes the trade honest, and it reaches him in
    real time, which is the only channel he has."""
    text = HOOK.read_text(encoding="utf-8")
    assert "UNCHECKED" in text
    assert "verified it" in text


@pytest.mark.parametrize(
    "name",
    sorted(p.name for p in HOOKS.glob("*.sh")),
)
def test_every_stop_hook_that_can_refuse_knows_it_is_on_a_retry(name: str):
    """The sweep that would have caught this six weeks ago.

    The 2026-08-03 repair rested on a claim -- "the only Stop hook that exits
    2" -- that was never measured. This asserts the pairing over every hook
    instead of trusting a sentence: if it is registered on the Stop event and
    it can exit 2, it must also know what to do when it is already being
    re-invoked.
    """
    settings = json.loads((REPO / ".claude" / "settings.json").read_text(encoding="utf-8"))
    stop_entries = json.dumps(settings.get("hooks", {}).get("Stop", []))
    if name not in stop_entries:
        pytest.skip(f"{name} is not registered on Stop")

    text = (HOOKS / name).read_text(encoding="utf-8")
    if "exit(2)" not in text and "exit 2" not in text:
        pytest.skip(f"{name} cannot refuse the turn; the pairing does not apply")

    assert "stop_hook_active" in text, (
        f"{name} can refuse the turn and has no idea it is on a retry -- "
        "this is the shape of Andrew's freeze"
    )
