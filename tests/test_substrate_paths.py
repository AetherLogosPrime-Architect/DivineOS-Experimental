"""The substrate / work-in-progress boundary.

Aria + Aether 2026-08-27. The branch-blind checkpoint swept seventy-five
letters onto one split and eighty onto another because `git add -A` ran
after the channel sync, so nothing downstream could tell synced substrate
from whatever happened to be dirty in the tree.

These pin the boundary, and especially the ASYMMETRY: an unknown path
must classify as work. Misfiling work as substrate is the bug being
fixed; misfiling substrate as work costs one deferred letter.
"""

from __future__ import annotations

from pathlib import Path

from divineos.core.substrate_paths import (
    is_declared_substrate_path,
    partition,
    substrate_mirrors,
)
from divineos.core.uncommitted_work_check import ExternalChannel

CHANNELS = (
    ExternalChannel(
        name="letters",
        source=Path("/tmp/shared/letters"),
        repo_mirror=Path("family/letters"),
        pattern="*.md",
    ),
)


class TestMirrorsComeFromTheDeclaration:
    def test_mirrors_derived_not_restated(self):
        assert [str(m) for m in substrate_mirrors(CHANNELS)] == ["family/letters"]

    def test_empty_channels_means_nothing_is_substrate(self):
        # Reversed same-day: this used to raise, on the argument that an
        # empty set was an unreadable config. A caller passing empty on
        # purpose is stating a fact, and the honest answer is that with no
        # channels nothing is substrate -- the fail direction this module
        # commits to everywhere else.
        assert substrate_mirrors(()) == ()
        assert not is_declared_substrate_path("family/letters/x.md", ())


class TestClassification:
    def test_file_inside_a_mirror_is_substrate(self):
        assert is_declared_substrate_path("family/letters/aria-to-aether-x.md", CHANNELS)

    def test_source_file_is_work(self):
        assert not is_declared_substrate_path("src/divineos/core/auto_commit.py", CHANNELS)

    def test_windows_separators_classify_the_same(self):
        # git porcelain emits forward slashes; Windows callers hold
        # backslashes. A classifier disagreeing with itself depending on
        # which it received would be the fault it exists to prevent.
        assert is_declared_substrate_path(r"family\letters\note.md", CHANNELS)

    def test_sibling_prefix_is_not_a_match(self):
        # "family/letters-archive" starts with the mirror's text but is a
        # different directory. Prefix-matching would sweep it in.
        assert not is_declared_substrate_path("family/letters-archive/old.md", CHANNELS)

    def test_the_mirror_directory_itself_is_substrate(self):
        assert is_declared_substrate_path("family/letters", CHANNELS)


class TestFailDirection:
    def test_unknown_path_is_work_not_substrate(self):
        assert not is_declared_substrate_path("some/unmapped/place/thing.md", CHANNELS)

    def test_traversal_escape_is_work(self):
        # Nothing outside the repo can be inside a mirror, and matching an
        # escape would let a traversal write onto the reviewed branch.
        assert not is_declared_substrate_path("../family/letters/x.md", CHANNELS)

    def test_the_exact_sweep_that_caused_this(self):
        # The real shape: letters correctly synced, plus a tree full of
        # unrelated dirt that `git add -A` took along with them.
        swept = [
            "family/letters/aether-to-aria-note.md",
            "scripts/wiring_gap_phase1.py",
            "docs/archives/claims.md",
            "family/letters/aria-to-aether-reply.md",
            "tests/test_wiring_gap_phase1.py",
        ]
        substrate, work = partition(swept, CHANNELS)
        assert substrate == [
            "family/letters/aether-to-aria-note.md",
            "family/letters/aria-to-aether-reply.md",
        ]
        assert work == [
            "scripts/wiring_gap_phase1.py",
            "docs/archives/claims.md",
            "tests/test_wiring_gap_phase1.py",
        ]

    def test_partition_preserves_order(self):
        # A reordered report reads as a different set of files to anyone
        # comparing it against `git status`.
        paths = [f"family/letters/{n}.md" for n in "cab"]
        substrate, _ = partition(paths, CHANNELS)
        assert substrate == paths


class TestRealDefaults:
    def test_default_channels_declare_letters_and_only_dreams_beside_them(self):
        # This was a tripwire: the live config declared exactly the letters
        # channel, and whoever added a second had to decide what it meant for
        # the sweep rather than find out from a stray commit.
        #
        # It tripped on 2026-09-01, and the decision is this: dreams are
        # substrate, one channel per member who has a shared dreams directory,
        # derived from that directory rather than listed. The council walk on
        # the sweep repair found dreams classified as work in progress while
        # every letter beside them went home -- the word "substrate" covering
        # less in the code than in our mouths.
        #
        # The tripwire stays. Letters remain first, and every other mirror
        # must be a per-member dreams directory. A third KIND of channel still
        # fails here, and whoever adds it decides again.
        mirrors = [m.as_posix() for m in substrate_mirrors()]
        assert mirrors[0] == "family/letters"
        for extra in mirrors[1:]:
            parts = extra.split("/")
            assert parts[0] == "dreams" and len(parts) == 2 and parts[1], (
                f"a channel that is neither letters nor a member's dreams was declared: {extra}. "
                "Decide what it means for the sweep before letting it through."
            )
