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


def test_the_description_axis_finds_what_the_name_axis_cannot():
    """The real miss of 2026-09-20, pinned so the repair cannot quietly go.

    Aether asked how a reader should judge whether two pieces of writing are
    about the same thing, and proposed word overlap while naming that as the
    very fault he was trying to measure. Asked whether it was already built,
    this module said NOT FOUND -- and then printed, four lines lower in its own
    footer, the command whose help begins "Semantic search across the indexed
    prose corpus".

    Three registered commands answered the question. None of them is SPELLED
    like it, and the name axis is a spelling test, so all three were invisible.
    """
    r = search("semantic matching of two pieces of writing")

    assert not r.commands, "the name axis is expected to stay blind here"
    found = {name for name, _line, _matched in r.described_by}
    assert {"find", "check-similar", "sis"} <= found, (
        "the three commands that answer this question must surface on the "
        f"description axis; got {sorted(found)}"
    )

    for _name, _line, matched in r.described_by:
        assert matched, "every lead must carry the word that produced it"


def test_a_description_lead_is_never_a_find():
    """The weak axis must not be able to emit the strong verdict.

    A made-up term still contains ordinary words, so leads appear for things
    that do not exist. Rarity does not separate them: measured on the live
    registry, the word that produced the false leads sits in 3.3% of command
    descriptions and the word that found the three real answers sits in 1.6%.
    So the leads may print, and `anything_found` must stay false regardless.
    """
    r = search("zzqq-nonexistent-artifact-name")
    assert not r.anything_found
    assert r.described_by, "this term is the one that produced spurious leads"
