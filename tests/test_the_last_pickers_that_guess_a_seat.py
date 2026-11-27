"""Round two of 877: a picker that reads a FOLDER NAME and falls back to a seat name is the typed default again,
written as logic where the option-default scans cannot see it (Aether's cold read of 144a3e1dc, finding 1).

The one function is core.sibling_audit_rounds.acting_seat(); anything that asks "which seat is acting" goes
through it, and when it says unknown-seat the caller says so and does not guess."""

import ast
from pathlib import Path

import pytest

from divineos.core import his_lessons_shelf
from divineos.core.sibling_corrections import SIBLING_HOMES

SRC = Path(__file__).resolve().parents[1] / "src" / "divineos"
MARKER = "SEAT-NAME-OK"


def _home_is(monkeypatch, spec):
    target = Path(spec).expanduser() if spec else Path("/nowhere/at/all")
    monkeypatch.setattr("divineos.core.paths.divineos_home", lambda: target)


@pytest.fixture(autouse=True)
def _no_override(monkeypatch):
    monkeypatch.delenv("DIVINEOS_SEAT", raising=False)


@pytest.mark.parametrize("seat", sorted(SIBLING_HOMES))
def test_the_shelf_names_the_seat_from_the_data_home_not_from_the_folder(
    monkeypatch, tmp_path, seat
):
    _home_is(monkeypatch, SIBLING_HOMES[seat])
    other = next(n for n in SIBLING_HOMES if n != seat)
    # Standing in a folder that names the OTHER seat, and in one that names none.
    for folder in (f"DivineOS-{other.title()}-new", "w-pr-seat"):
        here = tmp_path / folder
        here.mkdir()
        monkeypatch.chdir(here)
        assert his_lessons_shelf.seat() == seat


def test_an_unresolvable_home_is_unknown_seat_not_a_plausible_name(monkeypatch, tmp_path):
    _home_is(monkeypatch, None)
    for folder in ("w-pr-seat", "DivineOS-Experimental-Aria-new"):
        here = tmp_path / folder
        here.mkdir()
        monkeypatch.chdir(here)
        assert his_lessons_shelf.seat() == "unknown-seat"


def test_the_explicit_override_still_comes_first(monkeypatch):
    _home_is(monkeypatch, None)
    monkeypatch.setenv("DIVINEOS_SEAT", "aria")
    assert his_lessons_shelf.seat() == "aria"


def test_the_waiting_claim_surface_says_could_not_check_when_the_seat_is_unknown(monkeypatch):
    from divineos.core import hook_surfaces as hs
    from divineos.core import landing_status

    _home_is(monkeypatch, None)
    monkeypatch.setattr(hs, "_last_assistant_text", lambda payload: "#722 waits on Aletheia.")
    monkeypatch.setattr(landing_status, "read_letters", lambda: {})
    out = hs.waiting_claim_surface({})
    assert not out.refused, (
        "a claim must not be refused by looking for letters under a seat that does not exist"
    )
    assert out.state == "could-not-run"
    assert "seat" in (out.error or "")


# ----------- what each changed caller answers on a seat it cannot tell (Aether's holes 1 and 2)
# An unknown seat must read as "could not tell", never as a plausible empty answer: a count of 0, a plain
# False, an empty shelf. These pin the answer each caller gives, so the false-clean cannot come back quietly.


def test_the_lessons_shelf_says_it_could_not_search_on_an_unknown_seat(tmp_path):
    ask = "yes the same thing again please"
    out = his_lessons_shelf.surface(ask, "unknown-seat", index_dir=tmp_path, log=None)
    assert "cannot tell which seat" in out, out
    # Control: a real seat with the same empty index is stopped by the index, not by the seat, so the
    # assertion above cannot be passing on the index error that both would otherwise hit.
    real = his_lessons_shelf.surface(ask, "aria", index_dir=tmp_path, log=None)
    assert "cannot tell which seat" not in real and "could not be searched" in real


def test_a_named_seat_the_shelf_does_not_know_is_named_not_called_unknown(tmp_path):
    # If a third seat is added to the tree and not to FAMILY, the shelf must not say it cannot tell which
    # seat this is: it can, and the fault is the shelf's list (Aether's note on 240c9a8e9).
    out = his_lessons_shelf.surface(
        "yes the same thing again please", "a-third-seat", index_dir=tmp_path, log=None
    )
    assert "a-third-seat" in out and "cannot tell which seat" not in out, out


def test_an_exploration_count_on_an_unknown_seat_is_none_not_zero(monkeypatch, tmp_path):
    from divineos.core import multiplex_panels

    _home_is(monkeypatch, None)
    monkeypatch.chdir(tmp_path)
    assert multiplex_panels._exploration_count() is None


def test_the_obligations_gate_stays_on_when_the_seat_is_unknown(monkeypatch, tmp_path):
    from divineos.core import obligations

    _home_is(monkeypatch, None)
    monkeypatch.delenv("DIVINEOS_MEMBER", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    assert obligations.is_gate_disabled() is False


def test_the_unrouted_home_for_an_unknown_seat_is_not_a_real_place(monkeypatch, tmp_path):
    from divineos.core import instruments

    _home_is(monkeypatch, None)
    monkeypatch.delenv("DIVINEOS_MEMBER", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    home = instruments.unrouted_member_home()
    assert home.name == ".divineos-unknown-seat" and not home.exists()


def test_the_family_queue_briefing_reads_the_acting_seats_queue_not_aethers(monkeypatch):
    from divineos.core import family_queue_surface as fqs

    asked = []
    monkeypatch.setattr(
        fqs.queue, "for_recipient", lambda recipient, **kw: asked.append(recipient) or []
    )
    _home_is(monkeypatch, SIBLING_HOMES["aria"])
    fqs.format_for_briefing()
    _home_is(monkeypatch, SIBLING_HOMES["aether"])
    fqs.format_for_briefing()
    assert asked == ["aria", "aether"]


def test_the_family_queue_briefing_says_so_when_the_seat_is_unknown(monkeypatch):
    from divineos.core import family_queue_surface as fqs

    asked = []
    monkeypatch.setattr(
        fqs.queue, "for_recipient", lambda recipient, **kw: asked.append(recipient) or []
    )
    _home_is(monkeypatch, None)
    out = fqs.format_for_briefing()
    assert "cannot tell which seat" in out and asked == []


def test_the_doorbell_check_is_unknown_when_the_seat_is_unknown(monkeypatch):
    from divineos.core import dashboard_checks

    _home_is(monkeypatch, None)
    result = dashboard_checks.letter_doorbell_listening()
    assert result.state == dashboard_checks.UNKNOWN


def _copies_of_acting_seat(text):
    """`this_seat() or "unknown-seat"` written out by hand: the same answer as acting_seat(), copied."""
    return [
        n.lineno
        for n in ast.walk(ast.parse(text))
        if isinstance(n, ast.BoolOp)
        and isinstance(n.op, ast.Or)
        and any(
            isinstance(v, ast.Call)
            and getattr(v.func, "id", getattr(v.func, "attr", "")) == "this_seat"
            for v in n.values
        )
        and any(isinstance(v, ast.Constant) and v.value == "unknown-seat" for v in n.values)
    ]


def test_the_copy_scan_finds_a_hand_written_acting_seat():
    assert _copies_of_acting_seat('x = this_seat() or "unknown-seat"') == [1]
    assert _copies_of_acting_seat("x = acting_seat()") == []


def test_acting_seat_is_the_only_place_that_spells_out_this_seat_or_unknown():
    where = {}
    for path in sorted(SRC.rglob("*.py")):
        lines = _copies_of_acting_seat(path.read_text(encoding="utf-8", errors="ignore"))
        if lines:
            where[path.relative_to(SRC).as_posix()] = lines
    assert list(where) == ["core/sibling_audit_rounds.py"], where


# ------------------------------------------------ the floor: a seat name as the fallback in logic

_NAMES = frozenset(SIBLING_HOMES)


def _is_name(node):
    return isinstance(node, ast.Constant) and node.value in _NAMES


def _fallback_lines(text):
    """Lines where a seat name is the fallback of real logic: `x or "aether"`, `a if c else "aether"`, or
    `os.environ.get(KEY, "aether")`. Read from the syntax tree, so a help string that says "or 'aether'" is
    prose and not a guess. A deliberate mapping carries the marker on its line."""
    lines = text.splitlines()
    found = set()
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, ast.arguments):
            # `def f(seat="aether")`: the commonest shape of all. A default has no line of its own on the
            # arguments node, so each default constant is judged where it stands.
            for default in [*node.defaults, *node.kw_defaults]:
                if default is not None and _is_name(default):
                    if MARKER not in " ".join(
                        lines[max(default.lineno - 2, 0) : default.end_lineno]
                    ):
                        found.add(default.lineno)
            continue
        hit = (
            (
                isinstance(node, ast.BoolOp)
                and isinstance(node.op, ast.Or)
                and any(map(_is_name, node.values))
            )
            or (isinstance(node, ast.IfExp) and (_is_name(node.body) or _is_name(node.orelse)))
            or (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in {"get", "getenv", "setdefault"}
                and len(node.args) == 2
                and _is_name(node.args[1])
            )
        )
        # The marker sits on the expression's own lines or on the comment line directly above it.
        if hit and MARKER not in " ".join(lines[max(node.lineno - 2, 0) : node.end_lineno]):
            found.add(node.lineno)
    return sorted(found)


def test_the_scan_finds_the_shapes_the_old_scans_could_not_see():
    assert _fallback_lines('return os.environ.get("X") or ("aria" if a else "aether")') == [1]
    assert _fallback_lines('seat = name or "aether"') == [1]
    assert _fallback_lines('m = os.environ.get("K", "aether")') == [1]
    assert _fallback_lines('return "aria" if "aria" in words else "aether"') == [1]
    assert _fallback_lines('x = "aether" if a else "b"  # SEAT-NAME-OK: file to addressee') == []
    assert (
        _fallback_lines('# SEAT-NAME-OK: a file to its addressee\nx = "aether" if a else "b"') == []
    )
    # A marker two lines up excuses nothing: it must sit directly above.
    assert _fallback_lines('# SEAT-NAME-OK: x\nfoo()\nx = "aether" if a else "b"') == [3]


def test_the_scan_finds_a_function_default_and_a_setdefault():
    assert _fallback_lines('def f(seat="aether"):\n    pass') == [1]
    assert _fallback_lines('def f(*, seat="aria"):\n    pass') == [1]
    assert _fallback_lines('d.setdefault("seat", "aether")') == [1]
    assert _fallback_lines("def f(seat=None):\n    pass") == []
    assert _fallback_lines('# SEAT-NAME-OK: x\ndef f(seat="aether"):\n    pass') == []


def test_a_help_string_that_says_or_aether_is_prose_not_a_guess():
    assert _fallback_lines("""click.option("--to", help="Any family member or 'aether'.")""") == []


def test_no_source_file_picks_a_seat_by_falling_back_to_a_name():
    found = []
    for path in sorted(SRC.rglob("*.py")):
        for n in _fallback_lines(path.read_text(encoding="utf-8", errors="ignore")):
            found.append(f"{path.relative_to(SRC)}:{n}")
    assert not found, (
        "a typed seat name as the fallback in logic (use acting_seat(), or mark it SEAT-NAME-OK):\n"
        + "\n".join(found)
    )
