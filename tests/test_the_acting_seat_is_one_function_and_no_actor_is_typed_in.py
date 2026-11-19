"""The actor on an event is the seat that is acting, from one function, never a typed-in name.

2026-11-19, Aria (letter 1072): her `walk apply` recorded every walk as Aether's because council_walk typed
actor="aether"; she fixed her two and counted twelve more in the shared code. This tree has thirteen in
eleven files, so on the other seat every one of those events said "aether". Walk walk-0760ebfffb10.

Pinned: `acting_seat()` beside `this_seat()` gives the seat from the data home or "unknown-seat" (never a
guess); real callers pass it as the event's actor, run against the OTHER seat's real home spec with a control
for each seat; and a source scan fails if a typed-in actor literal is added back. The scan is the floor, the
real-caller test is the proof (Yudkowsky), and a test that only called acting_seat() would pass while a
caller still typed the literal (Breaker).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from divineos.core import sibling_audit_rounds as sar
from divineos.core.sibling_corrections import SIBLING_HOMES

SRC = Path(__file__).resolve().parents[1] / "src" / "divineos"


def _home_is(monkeypatch, spec: str | None) -> None:
    """Point the data home at a seat's real home spec, or at nowhere."""
    target = Path(spec).expanduser() if spec else Path("/nowhere/at/all")
    monkeypatch.setattr("divineos.core.paths.divineos_home", lambda: target)


@pytest.mark.parametrize("seat", sorted(SIBLING_HOMES))
def test_each_seat_resolves_to_its_own_name(monkeypatch, seat):
    _home_is(monkeypatch, SIBLING_HOMES[seat])
    assert sar.acting_seat() == seat


def test_an_unresolvable_home_is_named_unknown_seat_not_guessed(monkeypatch):
    _home_is(monkeypatch, None)
    assert sar.acting_seat() == "unknown-seat"


@pytest.fixture
def spy(monkeypatch):
    """Capture the actor each real caller passes to the ledger."""
    seen: list[str] = []

    def _log_event(*, event_type, actor, payload, **_rest):
        seen.append(actor)
        return "spy-event-id"

    monkeypatch.setattr("divineos.core.ledger.log_event", _log_event)
    return seen


@pytest.mark.parametrize("seat", sorted(SIBLING_HOMES))
def test_a_real_caller_writes_the_acting_seat_not_aether_on_every_seat(monkeypatch, spy, seat):
    from divineos.core.push_orchestrator import _ledger_log
    from divineos.core.surfaced_warnings import log_surfaced_warnings

    _home_is(monkeypatch, SIBLING_HOMES[seat])
    _ledger_log("PUSH_TEST", {"k": 1})
    log_surfaced_warnings([{"id": "w1", "text": "a warning"}])
    assert spy and set(spy) == {seat}


def test_the_control_other_seat_gives_a_different_actor_so_a_retyped_literal_fails(
    monkeypatch, spy
):
    from divineos.core.push_orchestrator import _ledger_log

    _home_is(monkeypatch, SIBLING_HOMES["aether"])
    _ledger_log("PUSH_TEST", {})
    _home_is(monkeypatch, SIBLING_HOMES["aria"])
    _ledger_log("PUSH_TEST", {})
    assert spy == ["aether", "aria"]


def test_no_actor_is_typed_in_anywhere_in_src():
    # THE FLOOR, not the proof: the literal was copied into thirteen places because copying was the easiest
    # thing to write; this makes the copy the harder path (Dawkins).
    pattern = re.compile(r"""actor\s*=\s*["']aether["']""")
    offenders = [
        f"{path.relative_to(SRC.parent)}:{n}"
        for path in SRC.rglob("*.py")
        for n, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1)
        if pattern.search(line)
    ]
    assert not offenders, "a typed-in actor again; use acting_seat():\n  " + "\n  ".join(offenders)
