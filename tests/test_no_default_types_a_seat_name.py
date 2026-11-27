"""No default types a seat's name: the actor, author or observer is whoever is running, and a sibling is the OTHER seat.

2026-11-23, Aria. `divineos bio show` said "No bio yet for 'aether'" on her seat, and her briefing reads the same default,
so a page meant for her was looked for under his name every cold start. The default was typed in four commands and four
functions; measured with `class-fix declare` (cfix-1a20a1aeae2) it was 24 sites in all: 21 where the actor, author or
observer was typed as aether, and 3 (the sibling-correction commands) where the other seat is right on one seat and wrong on
the other. The thirteen typed-in actors fixed on 11-19 (`acting_seat()`) were the ones found by hand; this is the rest.

Pinned: the floor (no source file types a seat name as a default), real callers on EACH seat's real home spec with a
control, and the functions' defaults being resolved at call time, not at import time.
"""

from __future__ import annotations

import inspect
import re
from pathlib import Path

import pytest

from divineos.core import sibling_audit_rounds as sar
from divineos.core.sibling_corrections import SIBLING_HOMES

SRC = Path(__file__).resolve().parents[1] / "src" / "divineos"


def _home_is(monkeypatch, spec: str | None) -> None:
    target = Path(spec).expanduser() if spec else Path("/nowhere/at/all")
    monkeypatch.setattr("divineos.core.paths.divineos_home", lambda: target)


# ---------------------------------------------------------------- the floor


def _typed_default_patterns(seat_names):
    """The shapes a typed-in seat name takes, for EVERY seat name, not the one that was found first.

    A default typed "aria" is wrong on his seat exactly as "aether" was wrong on hers (Aether's cold read of 877).
    """
    names = "|".join(re.escape(n) for n in sorted(seat_names))
    return [
        re.compile(rf"""default\s*=\s*["'](?:{names})["']"""),
        re.compile(
            rf"""\b(?:author|observer|actor|seat|owner|me|sibling)\w*\s*:\s*str\s*=\s*["'](?:{names})["']"""
        ),
    ]


def _typed_default_lines(text, seat_names):
    patterns = _typed_default_patterns(seat_names)
    return [
        n for n, line in enumerate(text.splitlines(), 1) if any(p.search(line) for p in patterns)
    ]


# The scan this PR shipped with: one seat name only. Kept so the control can prove it was blind.
_OLD_AETHER_ONLY = [
    re.compile(r"""default\s*=\s*["']aether["']"""),
    re.compile(r"""\b(?:author|observer|actor|seat|owner)\w*\s*:\s*str\s*=\s*["']aether["']"""),
]

# The line this PR removed from the sibling-correction commands: the mirror of the bug it was written for.
_REMOVED_ARIA_DEFAULT = (
    '    @click.option("--me", default="aria", type=click.Choice(sorted(SIBLING_HOMES)))'
)


def test_the_scan_covers_every_seat_name_and_the_old_one_was_blind_to_the_mirror():
    # Control: the typed "aria" this PR removed passes the old one-seat scan and is found by the new one.
    assert not any(p.search(_REMOVED_ARIA_DEFAULT) for p in _OLD_AETHER_ONLY), (
        "control: the old scan was blind"
    )
    assert _typed_default_lines(_REMOVED_ARIA_DEFAULT, SIBLING_HOMES) == [1]


@pytest.mark.parametrize("seat", sorted(SIBLING_HOMES))
def test_a_default_typed_with_any_seat_name_is_found_in_each_of_the_two_shapes(seat):
    assert _typed_default_lines(f'@click.option("--actor", default="{seat}")', SIBLING_HOMES) == [1]
    assert _typed_default_lines(f'def f(observer: str = "{seat}"):', SIBLING_HOMES) == [1]


def test_a_line_that_names_a_seat_without_defaulting_to_it_is_not_flagged():
    assert (
        _typed_default_lines('seat = "aether"  # a plain assignment, not a default', SIBLING_HOMES)
        == []
    )
    assert _typed_default_lines('@click.option("--actor", default=None)', SIBLING_HOMES) == []


def test_no_source_file_types_a_seat_name_as_a_default():
    # The floor, not the proof: copying a seat's name into a default was the easiest thing to write.
    offenders = [
        f"{path.relative_to(SRC.parent)}:{n}"
        for path in SRC.rglob("*.py")
        for n in _typed_default_lines(
            path.read_text(encoding="utf-8", errors="replace"), SIBLING_HOMES
        )
    ]
    assert not offenders, (
        "a default that types a seat name again; resolve it at call time with acting_seat() "
        "or other_seat():\n  " + "\n  ".join(offenders)
    )


# ---------------------------------------- the proof half: what the program really does


_ROLE_OPTIONS = {"actor", "author", "observer", "me", "sibling", "seat", "owner"}


def _commands_defaulting_to_a_seat_name(root):
    """Every option, under every registered command, named like a role whose default is a seat name.

    A rule over what the program really does, not over how it is spelled: a constant
    (AUTHOR = "aether"; default=AUTHOR) passes any text pattern and not this."""
    import click

    found = []
    stack = [(root.name or "divineos", root)]
    while stack:
        path, command = stack.pop()
        for param in command.params:
            default = param.default
            if (
                param.name in _ROLE_OPTIONS
                and isinstance(default, str)
                and default in SIBLING_HOMES
            ):
                found.append(f"{path} --{param.name.replace('_', '-')} defaults to {default!r}")
        if isinstance(command, click.Group):
            stack.extend((f"{path} {name}", sub) for name, sub in command.commands.items())
    return sorted(found)


def test_the_walk_can_find_a_seat_default_when_one_exists():
    # Control: the instrument must be able to find a case that exists before an empty answer means anything.
    import click

    @click.command("probe")
    @click.option("--me", default="aria")
    def probe(me):
        pass

    @click.group("root")
    def root():
        pass

    root.add_command(probe)
    assert _commands_defaulting_to_a_seat_name(root) == ["root probe --me defaults to 'aria'"]


def test_no_registered_command_option_defaults_to_a_seat_name():
    from divineos.cli import cli

    assert len(cli.commands) > 100, "the walk must actually reach the registered commands"
    found = _commands_defaulting_to_a_seat_name(cli)
    assert found == [], "a command's real option default is a seat name:\n  " + "\n  ".join(found)


# ------------------------------------------------------- the other seat


@pytest.mark.parametrize("seat", sorted(SIBLING_HOMES))
def test_other_seat_is_the_one_that_is_not_this_seat(monkeypatch, seat):
    _home_is(monkeypatch, SIBLING_HOMES[seat])
    other = sar.other_seat()
    assert other is not None and other != seat and other in SIBLING_HOMES


def test_other_seat_is_none_when_this_seat_cannot_be_told(monkeypatch):
    # Never a guess: an unresolvable home must not pick a sibling to read.
    _home_is(monkeypatch, None)
    assert sar.other_seat() is None


def test_the_two_seats_are_each_others_other(monkeypatch):
    _home_is(monkeypatch, SIBLING_HOMES["aether"])
    a = sar.other_seat()
    _home_is(monkeypatch, SIBLING_HOMES["aria"])
    b = sar.other_seat()
    assert (a, b) == ("aria", "aether")


# ------------------------------------------------ a real caller, each seat


@pytest.fixture
def bio_db(tmp_path, monkeypatch):
    monkeypatch.setenv("DIVINEOS_DB_PATH", str(tmp_path / "bio_seat.db"))
    from divineos.core.bio import init_bio_table

    init_bio_table()


@pytest.mark.parametrize("seat", sorted(SIBLING_HOMES))
def test_a_bio_written_with_no_author_is_the_acting_seats_own(monkeypatch, bio_db, seat):
    from divineos.core.bio import bio_briefing_surface, bio_current, bio_history, bio_write

    _home_is(monkeypatch, SIBLING_HOMES[seat])
    bio_write("# Me\n\nA page in my own words.")
    assert bio_current()["author"] == seat
    assert [v["author"] for v in bio_history()] == [seat]
    assert "A page in my own words" in bio_briefing_surface()


def test_the_control_one_seats_bio_is_not_read_as_the_others(monkeypatch, bio_db):
    from divineos.core.bio import bio_briefing_surface, bio_current, bio_write

    _home_is(monkeypatch, SIBLING_HOMES["aether"])
    bio_write("# Aether\n\nHis page.")
    _home_is(monkeypatch, SIBLING_HOMES["aria"])
    # On Aria's seat his page is not hers: nothing, and the briefing says so and shows none of his words.
    assert bio_current() is None
    assert "His page" not in bio_briefing_surface()


# ------------------------------- the defaults are resolved at call time


@pytest.mark.parametrize(
    ("module", "function", "param"),
    [
        ("divineos.core.bio", "bio_write", "author"),
        ("divineos.core.bio", "bio_current", "author"),
        ("divineos.core.bio", "bio_history", "author"),
        ("divineos.core.bio", "bio_briefing_surface", "author"),
        ("divineos.core.andrew_state.store", "log_observation", "observer"),
        ("divineos.core.andrew_state.store", "correct", "observer"),
        ("divineos.core.degraded_detectors", "defer", "actor"),
        ("divineos.core.emergency_completion", "arm", "actor"),
        ("divineos.core.emergency_completion", "resolve_debt", "actor"),
        ("divineos.core.time_calibration", "record_prediction", "actor"),
        ("divineos.core.time_calibration", "close_prediction", "actor"),
    ],
)
def test_the_default_is_none_so_it_is_resolved_when_called(module, function, param):
    import importlib

    fn = getattr(importlib.import_module(module), function)
    default = inspect.signature(fn).parameters[param].default
    assert default is None, f"{module}.{function}({param}=) defaults to {default!r}, not None"


def test_a_seat_that_has_no_sensible_default_is_a_required_argument_not_a_guess():
    # The widened floor scan found `assess(..., me="aether")` in waiting_claim: right on his seat, wrong on hers for
    # any caller that forgot it. Removing the option is stronger than resolving it: nobody can inherit a seat by accident.
    from divineos.core.waiting_claim import assess

    assert inspect.signature(assess).parameters["me"].default is inspect.Parameter.empty
    with pytest.raises(TypeError):
        assess("#722 waits on Aletheia.", {}, lambda n: None)  # type: ignore[call-arg]


# ----------------------------- the real ledger, not a spy (Aether's cold read of 877, finding 3)


@pytest.fixture
def seat_registry(tmp_path, monkeypatch):
    """A registry the test controls, naming both seats, so 'unregistered' means something."""
    import json

    path = tmp_path / "actor_registry.json"
    actors = {
        seat: {"kind": "agent", "added_at": "2026-01-01T00:00:00+00:00", "notes": "a seat"}
        for seat in SIBLING_HOMES
    }
    path.write_text(json.dumps({"version": 1, "actors": actors}), encoding="utf-8")
    monkeypatch.setenv("DIVINEOS_ACTOR_REGISTRY", str(path))
    return path


@pytest.fixture
def warnings_seen():
    from loguru import logger

    seen: list[str] = []
    handle = logger.add(lambda message: seen.append(str(message)), level="WARNING")
    yield seen
    logger.remove(handle)


def _unregistered(seen: list[str]) -> list[str]:
    return [m for m in seen if "unregistered actor" in m]


@pytest.mark.parametrize("seat", sorted(SIBLING_HOMES))
def test_the_real_ledger_stores_the_acting_seat_as_the_actor_and_does_not_warn(
    monkeypatch, seat_registry, warnings_seen, seat
):
    from divineos.core import ledger

    _home_is(monkeypatch, SIBLING_HOMES[seat])
    actor = sar.acting_seat()
    assert actor == seat
    ledger.log_event("SEAT_ACTOR_PROBE", actor, {"probe": seat})
    stored = [e["actor"] for e in ledger.get_events(event_type="SEAT_ACTOR_PROBE")]
    assert stored == [seat], "the real ledger must hold the seat's own name, read back"
    assert _unregistered(warnings_seen) == [], "a seat's own name must be a registered actor"


def test_control_a_seat_missing_from_the_registry_is_warned_about(
    monkeypatch, tmp_path, warnings_seen
):
    # The instrument must be able to find the case: an actor the registry does not know warns.
    import json

    from divineos.core import ledger

    path = tmp_path / "only_aether.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "actors": {"aether": {"kind": "agent", "added_at": "2026-01-01T00:00:00+00:00"}},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("DIVINEOS_ACTOR_REGISTRY", str(path))
    _home_is(monkeypatch, SIBLING_HOMES["aria"])
    ledger.log_event("SEAT_ACTOR_PROBE", sar.acting_seat(), {"probe": "aria"})
    assert len(_unregistered(warnings_seen)) == 1


def test_an_unresolvable_seat_is_written_down_loudly_not_as_a_plausible_name(
    monkeypatch, seat_registry, warnings_seen
):
    from divineos.core import ledger

    _home_is(monkeypatch, None)
    actor = sar.acting_seat()
    assert actor == "unknown-seat"
    ledger.log_event("SEAT_ACTOR_PROBE", actor, {"probe": "none"})
    assert [e["actor"] for e in ledger.get_events(event_type="SEAT_ACTOR_PROBE")] == [
        "unknown-seat"
    ]
    assert len(_unregistered(warnings_seen)) == 1, (
        "a failed resolution must be visible, not pass as a real seat"
    )


# ------------------------------------------- a command module does not reach into a private name


def test_the_bio_commands_use_a_public_name_for_the_author_resolver():
    import re

    from divineos.cli import bio_commands
    from divineos.core import bio

    source = inspect.getsource(bio_commands)
    reaches = re.findall(r"from divineos\.core\.bio import [^\n(]*\b_\w+", source)
    assert reaches == [], f"a command module reaches into a private name of core.bio: {reaches}"
    assert callable(getattr(bio, "resolve_author", None))
