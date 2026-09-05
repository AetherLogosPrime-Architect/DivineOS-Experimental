"""The map's properties, pinned on the GENERATOR rather than on the artifact.

The catalog exists to answer "does a command for this already exist?" -- it was
built after I rebuilt a command I had written two days earlier, because my own
search covered only my working tree and confirmed me. Its header says the thing
that matters: **a stale map is a worse oracle than no map**, because no map
sends you looking and a stale map sends you building.

WHY THESE MOVED OFF THE FILE, 2026-09-03. The map is no longer committed.
Measured across the whole open queue, every conflict on every conflicted branch
was one of two files and the catalog was in all of them -- not one line of
anyone's code. Aletheia ruled it out of the tree:

    "A file that neither party authors, that no reviewer reads, and that blocks
    everything, is not carrying any of the meaning my signature is supposed to
    cover. Removing it from the tree makes my signature cover MORE, not less."

Four tests here used to read the committed file and `pytest.skip` when it was
absent. Untracking it would have turned all four into permanent skips -- green
checks measuring nothing, which is the exact fault this file's own history is
about, and which the previous version of this docstring warned against while
leaving the shape in place.

So each property moved to where it can be checked without the artifact:

  * shape of the map's numbers      -> the band function that produces them
  * no per-machine telemetry        -> the call sites inside build(), which is
                                       stronger than matching the output: it
                                       catches reintroduction where it happens
  * subsystem ordering              -> the function that orders them
  * unix line endings               -> the write call that must ask for them

Two properties were RETIRED rather than relocated, and saying so explicitly so
the absence reads as a decision. The map holding still mattered because a moving
committed file manufactured conflicts and unbound reviews anchored to the diff.
Out of the tree, there is no diff to disturb. What survives is that the map must
not describe one machine -- true regardless of tracking, and pinned below.
"""

from __future__ import annotations

import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "scripts" / "generate_capability_catalog.py"


def _generator_module():
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        import generate_capability_catalog as gen
    finally:
        sys.path.pop(0)
    return gen


def test_generator_exists():
    assert GENERATOR.is_file(), "the map's generator is the subject of every test here"


def test_bands_are_never_bare_counts():
    """`| name | 123 |` is the shape that kept the map moving.

    A band ("10-99", "none") is stable across a reference appearing or leaving;
    a raw integer is not. Checked on the function that produces the cell rather
    than on a rendered row, so it holds without building anything.
    """
    gen = _generator_module()
    for n in (0, 1, 2, 9, 10, 11, 50, 99, 100, 101, 5000):
        band = gen._ref_band(n)
        assert not band.isdigit(), (
            f"_ref_band({n}) returned the bare count {band!r}; the map is "
            "carrying raw numbers again, which is how it stopped holding still"
        )


def test_reference_bands_keep_the_none_boundary_exact():
    """Coarse above zero; exact AT zero, because a false 'dead' is the danger.

    The generator's own note: a false "this is dead" on safety machinery is
    worse than no inventory at all, because it invites deleting live code.
    """
    gen = _generator_module()

    assert gen._ref_band(0) == "none"
    assert gen._ref_band(1) != "none", "one reference is not zero references"
    assert gen._ref_band(150) == gen._ref_band(151)
    assert gen._ref_band(11) == gen._ref_band(12)


def test_the_map_never_reaches_for_the_per_machine_reading():
    """The map must not describe whichever machine last generated it.

    It had this three ways at once: a count in the prose, a list of commands
    that had been run, and a marker beside each. All three said "on this
    machine", which is not a fact about the repository and changed whenever
    anybody ran anything -- so it read completely differently in Aria's clone.

    Pinned at the CALL SITE rather than in the output. Matching the rendered
    text only catches the data after it has been formatted in; this catches
    build() asking for it at all, which is where a reintroduction would start.
    """
    gen = _generator_module()
    body = inspect.getsource(gen.build)
    for reach in ("_usage_counts", "local_usage_report"):
        assert reach not in body, (
            f"build() calls {reach}(), so per-machine telemetry is on its way "
            "back into a file meant to describe the repository"
        )


def test_the_telemetry_finding_survived_the_removal_of_the_telemetry():
    """Removing the volatile data must not quietly remove the point it made.

    Matched against the source with its quote marks removed and its whitespace
    collapsed, so adjacent string literals read as the one sentence they will
    render as. Two earlier versions failed here: the first asserted the
    sentence whole, and the second collapsed whitespace but left the quotes
    between the literals. Both reported that the finding had been DROPPED while
    it sat in plain view four lines above the assertion. A test whose failure
    message names the wrong cause sends the next reader to repair something
    that was never broken -- which is this month's fault in test clothing.
    """
    gen = _generator_module()
    body = " ".join(inspect.getsource(gen.build).replace('"', "").split())
    assert "Blind telemetry is a measurement problem" in body, (
        "the blind-telemetry finding was dropped along with the volatile "
        "numbers; the finding is the reason the section exists"
    )


def test_the_local_reading_still_exists_somewhere():
    """Moved, not deleted. A signal that goes nowhere has been lost, not relocated."""
    gen = _generator_module()
    assert hasattr(gen, "local_usage_report"), (
        "the per-machine usage reading was removed from the map with the "
        "promise that it prints to the terminal instead; that function is the "
        "promise being kept"
    )
    report = gen.local_usage_report()
    assert "THIS machine" in report or "this machine" in report.lower(), (
        "the local reading must say whose machine it describes -- saying it "
        "without saying that is how it ended up in a shared file"
    )


def test_subsystems_come_out_in_name_order_not_volume_order():
    """Sorting by the count turned one changed reference into a reordered table.

    Reads the function rather than the rendered table: it scans files and takes
    no subprocess, so it is cheap enough to run everywhere -- which is the whole
    point of moving it off the artifact.
    """
    gen = _generator_module()
    rows = gen._subsystems()
    names = [r[0] for r in rows]
    assert names == sorted(names), (
        "subsystem rows are not in name order, so a single reference change will reorder the table"
    )


def test_the_generator_still_asks_for_unix_line_endings():
    """Written with newline="\\n", or the file is dirty the moment it is made.

    The repo declares this path eol=lf. Without the argument, write_text
    translates every newline on Windows, so the generator produces hundreds of
    invisible differences against the file it just regenerated. Untracking the
    map removes the git consequence but not the local one: a file that never
    looks clean still teaches whoever reads it to stop trusting the check.
    """
    gen = _generator_module()
    body = inspect.getsource(gen.main)
    assert 'newline="\\n"' in body or "newline='\\n'" in body, (
        "the generator's write no longer asks for unix line endings"
    )


# The full build is NOT exercised here, on purpose and now for a second reason.
# It probes every command with --help and takes minutes, which made the file
# unrunnable when six tests each did it -- and a test that times out teaches
# people to skip the file. scripts/check_capability_catalog_fresh.py builds on
# every pre-commit, which is where a slow, thorough check belongs, and it is
# also where "the generator could not run" is made to block.
