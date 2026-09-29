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

    def test_empty_channels_empties_the_derived_half_only(self):
        # REVERSED AGAIN, AND THIS TIME BY THE INCIDENT RATHER THAN BY
        # ARGUMENT (2026-09-11).
        #
        # It used to raise. Then it was changed to say that with no channels
        # NOTHING is substrate, on the reasoning that a caller passing empty
        # is stating a fact. That reasoning is sound about the DERIVED half
        # and fails open on the other one: "nothing was declared" became "a
        # letter is code", which is precisely how the push gate came to refuse
        # a branch over 183 substrate files the split had filed as work.
        #
        # Aria's rule is what settles it: for any door whose guard is a LIST,
        # ask what SEEDED the list. A list derived from declarations
        # structurally cannot see substrate that arrives without one -- and a
        # letter written by someone who declared no channel is still a letter.
        # So the four local prefixes are the half that does not depend on
        # anybody having declared anything, and they still answer here.
        assert substrate_mirrors(()) == ()
        assert is_declared_substrate_path("family/letters/x.md", ()), (
            "with no channel declared a letter classified as code -- the "
            "fail-open direction, and the one that deadlocked the push gate"
        )
        # The control: ordinary code is still code with no channels declared,
        # so the assertion above is about the prefixes rather than about the
        # classifier having become permissive.
        assert not is_declared_substrate_path("src/divineos/core/ledger.py", ())


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
        #
        # SUPERSEDED IN ONE ENTRY, 2026-09-10, and the entry is the finding.
        # This originally pinned docs/archives/claims.md as WORK, which was
        # right by this module's own rule and wrong about the house: the push
        # gate counted that same directory as SUBSTRATE and refused any branch
        # carrying it. So the split put archives in the work commit and the
        # gate then refused the branch, with no component able to see the
        # disagreement -- 183 files, unpushable and unfixable by the thing that
        # made it. The definition is now shared (LOCAL_SUBSTRATE_PREFIXES) and
        # archives classify as what they have always been.
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
            "docs/archives/claims.md",
            "family/letters/aria-to-aether-reply.md",
        ]
        assert work == [
            "scripts/wiring_gap_phase1.py",
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
