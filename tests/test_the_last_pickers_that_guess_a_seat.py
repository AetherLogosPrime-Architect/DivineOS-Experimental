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
                and node.func.attr in {"get", "getenv"}
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
