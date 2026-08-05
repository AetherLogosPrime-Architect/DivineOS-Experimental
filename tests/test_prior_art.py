"""Station 0 must not become the fifth thing nobody runs.

The risk with `already-built` is not that it fails — it is that it returns a
confident-looking clean result over an axis it never searched, which is the
exact defect it exists to prevent. So the tests pin the honesty of the report
as hard as the correctness of the search.
"""

from __future__ import annotations

import click

from divineos.core.prior_art import UNSEARCHED_SURFACES, _slug, search


def test_slug_makes_the_three_spellings_match():
    """`build flow`, `build-flow`, `build_flow` are the same thing.

    Every real lookup this session crossed a spelling boundary: the doc is
    `build_flow.md`, the command is `build-flow`, and Andrew says "build flow".
    A matcher that respects the separators finds none of them from the others.
    """
    assert _slug("build flow") == _slug("build-flow") == _slug("build_flow") == "buildflow"


def test_finds_a_thing_that_exists():
    r = search("build flow")
    assert "build-flow" in r.commands
    assert any(p.endswith("core/build_flow.py") for p in r.working_tree)


def test_finds_a_registered_command_by_loose_name():
    """psf is the case that started this: prescribed everywhere, absent here."""
    r = search("psf")
    assert "psf" in r.commands


def test_reports_nothing_for_a_thing_that_does_not_exist():
    r = search("zzqq-nonexistent-artifact-name")
    assert not r.anything_found


def test_unsearched_surfaces_are_named_and_real():
    """The third word, at the report layer.

    Every surface this module declines to search must be a command that
    actually exists — otherwise the report tells the reader to run something
    that is not there, which is the painted-door defect rebuilt inside the
    tool written to find painted doors. Aria shipped exactly that today.
    """
    from divineos.cli import cli

    registered = set(cli.list_commands(click.Context(cli)))
    assert UNSEARCHED_SURFACES, "the module must name what it did not search"
    for invocation, what in UNSEARCHED_SURFACES:
        assert invocation.startswith("divineos ")
        sub = invocation.split()[1]
        assert sub in registered, f"{invocation!r} is named as a remedy but is not a command"
        assert what, "each unsearched surface must say what it covers"
