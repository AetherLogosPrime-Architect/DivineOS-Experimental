"""The eighth copy has to be visible at the moment of writing.

Andrew 2026-09-19: *"you keep making the same mistake over and over, and even
being fully aware of it does not help.. only structure does.. make the mistake
impossible to do, by automating the correct choice before you need to make
it."*

Seven private copies of shell-command-head parsing have been found and deleted
over months, each repair fixing the instance and leaving the gradient. The
gradient is that writing five lines costs nothing at the moment of writing,
while discovering the shared module costs a search that only succeeds if you
already suspect it exists.

Both directions are pinned, and the forced failure is the important one. I
spent this session finding checks that were never shown to be able to find
anything -- a measure that reported healthy on no data, an alarm blind to the
case it existed for. A check whose only test is that it passes is that same
shape wearing a different coat.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "check_no_private_command_parsing.py"


def _load():
    spec = importlib.util.spec_from_file_location("_privcheck", _SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def checker(tmp_path, monkeypatch):
    mod = _load()
    monkeypatch.setattr(mod, "ROOT", tmp_path)
    monkeypatch.setattr(mod, "SEARCH_ROOTS", (tmp_path / "src",))
    monkeypatch.setattr(mod, "ALLOWED", {})
    (tmp_path / "src").mkdir()
    return mod, tmp_path / "src"


def _write(where: Path, name: str, body: str) -> None:
    (where / name).write_text(body, encoding="utf-8")


def test_a_planted_wrapper_list_is_found(checker):
    """The forced failure. Silence is only meaningful once this passes."""
    mod, src = checker
    _write(
        src,
        "sneaky.py",
        'WRAPPERS = ("cd", "env", "sudo", "exec")\n'
        "def head(c):\n"
        "    t = c.split()\n"
        "    return t[0] if t else ''\n",
    )
    hits, _ = mod.offenders()
    assert hits, "a planted private parser was not found"
    assert "wrappers" in hits[0][1]


def test_a_planted_assignment_stripper_is_found(checker):
    mod, src = checker
    _write(src, "sneaky2.py", 'import re\nASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")\n')
    hits, _ = mod.offenders()
    assert hits
    assert "NAME=value" in hits[0][1]


def test_calling_the_shared_home_is_not_a_finding(checker):
    """The whole point. Importing the home clears the shape."""
    mod, src = checker
    _write(
        src,
        "good.py",
        "from divineos.core.command_parsing import resolve_command_head\n"
        'WRAPPERS = ("cd", "env", "sudo", "exec")  # a leftover constant\n',
    )
    assert mod.offenders()[0] == []


def test_ordinary_code_is_quiet(checker):
    """A noisy check teaches the route around itself, which is the fault above."""
    mod, src = checker
    _write(src, "plain.py", "def add(a, b):\n    return a + b\n")
    _write(src, "strings.py", 'PATHS = ("src", "scripts")\nNOTE = "cd into the repo first"\n')
    hits, read = mod.offenders()
    assert hits == []
    assert read == 2, "the check must report what it actually read"


def test_an_unreadable_file_is_unknown_rather_than_clean(checker, monkeypatch):
    """Cannot-read is its own answer. This session's entire lesson."""
    mod, src = checker
    _write(src, "boom.py", "x = 1\n")

    def _raise(*_a, **_k):
        raise OSError("nope")

    monkeypatch.setattr(Path, "read_text", _raise)
    hits, _ = mod.offenders()
    assert hits
    assert "COULD NOT READ" in hits[0][1]


def test_the_live_tree_is_clean():
    """If this fails, an eighth private parser has appeared. That is the finding.

    A live check rather than a fixture, deliberately: a rule that only holds in
    a temporary directory is not holding anything.
    """
    mod = _load()
    hits, _ = mod.offenders()
    assert hits == [], f"private command-head parsing: {hits}"


def test_the_allowlist_entries_all_carry_a_reason():
    """The cheapest route around this check, so the entries stay legible.

    A written reason does not prevent a bad entry -- it makes one readable by
    whoever audits it, which is the weaker and honest claim. The refutation to
    watch is growth: a long list means the shapes are matching the wrong thing
    rather than the tree being clean.
    """
    mod = _load()
    assert len(mod.ALLOWED) <= 4, "a growing allowlist means the shapes are wrong"
    for path, reason in mod.ALLOWED.items():
        assert len(reason) >= 30, f"{path} has a reason too thin to audit"
