"""The map must hold still, or it cannot stay fresh, or it cannot be trusted.

The catalog exists to answer "does a command for this already exist?" -- it was
built after I rebuilt a command I had written two days earlier, because my own
search covered only my working tree and confirmed me. Its own header says the
thing that matters: **a stale map is a worse oracle than no map**, because no
map sends you looking and a stale map sends you building.

So freshness is the whole property, and freshness was impossible by
construction. The committed map recorded two volatile things:

  1. How many times *this machine* had invoked each command. Session telemetry,
     not a fact about the repository. It changed every session and would read
     completely differently in Aria's clone.
  2. An exact reference count per subsystem, with the table SORTED by it -- so
     one file gaining a line both changed a row and reordered the table.

Measured 2026-09-02 across three open branches whose maps conflicted with main:
blank the volatile numbers and TWO become byte-identical to main, while the
third differs only by a genuinely new subsystem. The numbers were the entire
conflict class.

The cost was not the conflicts. It was that resolving them edited the branch,
which moved its patch-id, which unbound the external review anchored to it. Six
branches were waiting on re-review, and this was why.

These tests pin the shape rather than the wording: the map may say anything it
likes, as long as what it says does not change when nothing meaningful has.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "scripts" / "generate_capability_catalog.py"
CATALOG = ROOT / "docs" / "CAPABILITY_CATALOG.md"


def _generated_text() -> str:
    """The COMMITTED map, not a fresh build.

    Building probes every command with --help sequentially and takes minutes,
    so calling it once per test made the suite unrunnable. The committed file
    is also the more honest subject: it is what a reader actually consults and
    what lands in a diff. That it matches the generator is already guaranteed
    by the freshness check in pre-commit, which is a different property from
    the one these tests pin.
    """
    if not CATALOG.is_file():
        pytest.skip("catalog not present in this checkout")
    return CATALOG.read_text(encoding="utf-8")


def _generator_module():
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        import generate_capability_catalog as gen
    finally:
        sys.path.pop(0)
    return gen


def test_generator_exists():
    assert GENERATOR.is_file(), "the map's generator is the subject of every test here"


def test_no_table_row_is_a_bare_count():
    """No row may be `| name | 123 |` -- that shape is what kept moving.

    Both volatile columns had it: the usage table and the subsystem table. A
    band ("10-99", "none") passes; a raw integer does not.
    """
    text = _generated_text()
    offenders = re.findall(r"^\| `[^`]+` \| \d+ \|.*$", text, flags=re.MULTILINE)
    assert not offenders, (
        "the map is carrying raw counts again, which is how it stopped being "
        "able to stay fresh:\n  " + "\n  ".join(offenders[:10])
    )


def test_map_carries_no_per_machine_usage_data():
    """Nothing in the committed map may describe one machine's history.

    The map had this three ways at once: a count in the prose, a list of the
    commands that had been run, and a marker beside each one. All three said
    "on whichever machine last generated this", which is not a fact about the
    repository and changed whenever anybody ran anything.

    The version of this test that shipped first checked that the usage list had
    no COUNTS. Removing the list entirely made that test skip forever -- a green
    check measuring nothing, which is the fault this whole file is about. This
    replaces it with the property that actually holds now.
    """
    text = _generated_text()
    assert "Commands that DO report usage" not in text, (
        "the per-machine usage list is back in the committed map"
    )
    assert "recorded invocations" not in text, (
        "the per-machine invocation counts are back in the committed map"
    )
    assert "•" not in text, "the per-machine usage marker is back beside command headings"
    # The FINDING must survive -- removing the volatile data must not quietly
    # remove the point it was making.
    assert "Blind telemetry is a measurement problem" in text, (
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


def test_subsystem_table_is_sorted_by_name_not_by_volume():
    """Sorting by the count turned one changed reference into a reordered table."""
    text = _generated_text()
    rows = re.findall(r"^\| `core/([^/`]+)/` \|", text, flags=re.MULTILINE)
    if len(rows) < 2:
        pytest.skip("no subsystem table in this environment")
    assert rows == sorted(rows), (
        "subsystem rows are not in name order, so a single reference change "
        "will reorder the table and manufacture a conflict"
    )


def test_reference_bands_keep_the_none_boundary_exact():
    """Coarse above zero; exact AT zero, because a false 'dead' is the danger.

    The generator's own note: a false "this is dead" on safety machinery is
    worse than no inventory at all, because it invites deleting live code.
    """
    gen = _generator_module()

    assert gen._ref_band(0) == "none"
    assert gen._ref_band(1) != "none", "one reference is not zero references"
    # Coarse above the boundary: neighbours inside a band must agree.
    assert gen._ref_band(150) == gen._ref_band(151)
    assert gen._ref_band(11) == gen._ref_band(12)


def test_written_map_uses_unix_line_endings():
    """Written with newline="\\n", or the file is dirty the moment it is made.

    The repo declares this path eol=lf. Without the argument, write_text
    translates every newline on Windows, so the generator produces 1397
    invisible differences against the file it just regenerated -- git diff
    prints nothing while git status calls it modified, and pre-commit
    regenerates and re-stages it forever.
    """
    if not CATALOG.is_file():
        pytest.skip("catalog not generated in this environment")
    raw = CATALOG.read_bytes()
    assert b"\r\n" not in raw, (
        "the committed map has Windows line endings; the generator dropped its "
        "newline argument and the file will now never look clean"
    )


# Determinism and the script entry point are NOT tested here on purpose.
# Both require a full build, which probes every command with --help and takes
# minutes -- six of those made the file unrunnable, and a test that times out
# teaches people to skip the file. scripts/check_capability_catalog_fresh.py
# already builds and compares on every pre-commit, which is where a slow,
# thorough check belongs. Saying so here so the absence reads as a decision
# rather than an oversight.
