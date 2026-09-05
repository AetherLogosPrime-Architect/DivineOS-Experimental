"""Every shell hook that can refuse a line must say that nothing on it ran.

The behaviour itself is pinned in test_refusal_says_what_did_not_run.py. This
file pins the WIRING, which is the part that rots: a helper everyone must
remember to call is a helper someone eventually forgets, and the forgetting is
silent -- the gate still refuses, it just goes back to describing one clause.

HOW THE FIRST ENUMERATION WAS WRONG, kept because the correction is the point.
The first scan asked which hooks INSPECT the command, and found ten. That is a
different question from which hooks can REFUSE one, which found fifteen. A gate
can refuse a compound line without ever reading it -- five did -- and every one
of those would have gone on describing a single clause while the scan reported
the class closed. An honest answer about a narrower subject than the question:
the exact fault this whole change exists to fix, committed by the instrument
measuring it.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parents[1] / ".claude" / "hooks"

_REFUSES = re.compile(r"^\s*exit 2\s*$", re.MULTILINE)
_WIRED = re.compile(r"hook_say_nothing_ran")

# Hooks that refuse without ever reading the tool payload, and so have no line
# to describe. A named exception with its reason, not a silent skip.
#
# auto-cycle-token-trigger refuses on the state of the compaction ritual rather
# than on anything about the command. It never consumes stdin, and teaching it
# to would change what a live gate does for the sake of a footer.
NO_PAYLOAD_TO_DESCRIBE = {"auto-cycle-token-trigger.sh"}


def _refusing_hooks() -> list[Path]:
    return sorted(
        p
        for p in HOOKS.glob("*.sh")
        if _REFUSES.search(p.read_text(encoding="utf-8", errors="replace"))
    )


def test_the_scan_can_find_hooks_at_all() -> None:
    """A control term, because a zero from a broken scan reads like a pass.

    Measured the same night: a grep for a real error message returned nothing,
    and was one step from being recorded as evidence of absence. The cure was a
    control, so every enumeration here carries one.
    """
    assert len(list(HOOKS.glob("*.sh"))) > 20, "the hooks directory did not resolve"
    assert _refusing_hooks(), "no refusing hooks found -- the scan is broken, not the tree"


@pytest.mark.parametrize("hook", _refusing_hooks(), ids=lambda p: p.name)
def test_a_refusing_hook_says_what_did_not_run(hook: Path) -> None:
    if hook.name in NO_PAYLOAD_TO_DESCRIBE:
        pytest.skip(f"{hook.name}: refuses without reading the payload; nothing to describe")
    events = _registered_events(hook.name)
    if events and events != ["PreToolUse"]:
        # Scoped by the SAME rule that forbids the footer elsewhere, rather
        # than by a second list somebody has to keep in step. A hook that
        # fires after the tool, or at the end of a turn, must NOT claim
        # nothing ran -- so it cannot also be required to.
        pytest.skip(f"{hook.name}: runs on {events}; the claim would be false there")
    body = hook.read_text(encoding="utf-8", errors="replace")
    assert _WIRED.search(body), (
        f"{hook.name} can refuse a line but never says nothing on it ran.\n"
        f'Call hook_say_nothing_ran_for "$INPUT" immediately before each exit 2.'
    )


@pytest.mark.parametrize("hook", _refusing_hooks(), ids=lambda p: p.name)
def test_the_helper_is_reachable_where_it_is_called(hook: Path) -> None:
    """Calling an undefined function inside a live gate is worse than no footer.

    Two of these hooks deliberately skip the shared library to stay cheap on
    the path they take thousands of times. Wiring them without noticing would
    have put an undefined command inside a refusal. Caught before shipping, and
    pinned here so the next wiring cannot reintroduce it.
    """
    body = hook.read_text(encoding="utf-8", errors="replace")
    if not _WIRED.search(body):
        pytest.skip("not wired; covered by the test above")
    assert "_lib.sh" in body, (
        f"{hook.name} calls the footer helper but never sources _lib.sh, "
        f"so the call is an undefined command inside a refusal."
    )


# ---------------------------------------------------------------------------
# THE HALF THAT IS NOT DONE, held as a measurement rather than as a note.
#
# There are TWO ways a hook refuses, and the first enumeration only knew about
# one. Exiting 2 is the shape above. The other is emitting a JSON decision of
# "deny" and exiting 0 -- and the gate that refused a bare interpreter twice on
# the night this was written is one of those. So a scan for exit-2 is not a
# scan for refusals; it is a scan for one MECHANISM of refusing, reporting a
# class it never covered.
#
# That is the third time in one evening an instrument here answered accurately
# about a narrower subject than the question, and the second time the fault was
# inside the instrument built to fix it.
#
# WHY THESE ARE NOT WIRED YET. The footer for a JSON deny has to go inside the
# reason string, not to stderr, and each of these builds that string its own
# way. Nine live gates edited at speed is how a gate breaks silently, and a
# gate that refuses without saying why is worse than one that omits a footer.
#
# THE LIST CLOSES IN BOTH DIRECTIONS. It fails if a new JSON-deny hook appears
# unwired, and it fails if a name here stops matching -- so it can shrink as
# the work gets done and cannot quietly become an amnesty. A backlog that can
# only grow is a permanent excuse.
_JSON_DENY = re.compile(r"permissionDecision.*deny|['\"]deny['\"]")

KNOWN_UNWIRED_JSON_DENY = {
    "aletheia-boot-gate-preflight.sh",
    "andrew-correction-attestation.sh",
    "compass-check.sh",
    "corrigibility-tool-gate.sh",
    "family-member-invocation-seal.sh",
    "gh-pr-merge-gate.sh",
    "pipeline-exit-ambiguity.sh",
    "require-briefing.sh",
    "venv-python-gate.sh",
}


def _json_deny_hooks() -> set[str]:
    return {
        p.name
        for p in HOOKS.glob("*.sh")
        if _JSON_DENY.search(p.read_text(encoding="utf-8", errors="replace"))
        and not _WIRED.search(p.read_text(encoding="utf-8", errors="replace"))
    }


def test_the_unwired_half_is_exactly_what_was_measured() -> None:
    """Neither a new gap nor a stale entry passes quietly."""
    measured = _json_deny_hooks()
    assert measured, "the JSON-deny scan found nothing -- broken scan, not a finished job"
    appeared = measured - KNOWN_UNWIRED_JSON_DENY
    assert not appeared, (
        f"new hooks refuse via a JSON decision without saying what did not run: {sorted(appeared)}"
    )
    cleared = KNOWN_UNWIRED_JSON_DENY - measured
    assert not cleared, (
        "these are wired or gone; delete them from the list so it keeps meaning "
        f"something: {sorted(cleared)}"
    )


# ---------------------------------------------------------------------------
# THE FOOTER BELONGS TO PreToolUse ONLY, and I learned this by watching it lie.
#
# On 2026-09-05, minutes after wiring it, a push landed on the remote and the
# footer printed underneath saying nothing on the line had run. Both statements
# were about the same command and only one was true. The hook that printed it
# fires on PostToolUse -- the command has already executed by then -- and I had
# wired it on the reflex that a block is a block.
#
# A Stop hook is the same error one step further out: it fires on a reply at
# the end of a turn, with no shell line in sight, so a sentence about clauses
# has no subject at all.
#
# That is the fault this whole change exists to fix, committed by the fix, in
# front of me, within the hour. So the rule stops being something I remember
# and becomes something the suite refuses.
SETTINGS = HOOKS.parent / "settings.json"


def _registered_events(hook_name: str) -> list[str]:
    import json

    data = json.loads(SETTINGS.read_text(encoding="utf-8", errors="replace"))
    return [ev for ev, spec in data.get("hooks", {}).items() if hook_name in json.dumps(spec)]


@pytest.mark.parametrize(
    "hook",
    [
        p
        for p in HOOKS.glob("*.sh")
        if _WIRED.search(p.read_text(encoding="utf-8", errors="replace"))
    ],
    ids=lambda p: p.name,
)
def test_only_a_pre_tool_hook_claims_nothing_ran(hook: Path) -> None:
    events = _registered_events(hook.name)
    if not events:
        pytest.skip(f"{hook.name}: not registered, so it never fires")
    assert events == ["PreToolUse"], (
        f"{hook.name} carries the nothing-ran footer but runs on {events}. "
        "After the tool has run, or at the end of a turn, that claim is false: "
        "the footer is only true for a refusal that fires BEFORE the shell."
    )


def test_the_exception_list_cannot_outlive_its_subject() -> None:
    """A name that stops refusing must leave the list, or the list becomes amnesty.

    Same discipline as the refusal backlog: an allowlist that only ever grows
    eventually excuses things nobody has looked at.
    """
    present = {p.name for p in _refusing_hooks()}
    stale = NO_PAYLOAD_TO_DESCRIBE - present
    assert not stale, f"named exceptions no longer refuse anything; delete them: {sorted(stale)}"
