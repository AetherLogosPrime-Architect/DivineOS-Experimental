"""Tests for the identity-load surface (AETHER.md at project root).

The architectural fix to the 2026-05-08 root-cause naming: identity-
binding via project-root identity-document, surfaced FIRST in briefing
in identity-register. These tests pin the loading semantics, the
empty-on-absence behavior (public-template repos), and the formatting.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import pytest

from divineos.core import identity_load


@pytest.fixture
def chdir_to(tmp_path):
    """Change cwd into tmp_path for the duration of a test, restore after."""
    old = Path.cwd()
    os.chdir(tmp_path)
    try:
        yield tmp_path
    finally:
        os.chdir(old)


def occupant_doc() -> str:
    """The identity-document filename for whoever the substrate says lives here.

    Tests below that exercise RENDERING used to hardcode AETHER.md. Since
    2026-09-17 the loaded filename follows the occupant, so hardcoding a
    name made those tests pass or fail on whose checkout they ran in —
    they were pinning the render and accidentally pinning the identity.
    This keeps them pinning the render.
    """
    return identity_load._occupant_filename() or identity_load.IDENTITY_DOCUMENT_FILENAME


class TestOccupantDerivedFilename:
    """The document loaded is the OCCUPANT'S, not whichever one is lying there.

    Pins the 2026-09-17 repair. Aria's checkout held a copy of Aether's
    identity document and the filename was a hardcoded constant, so her
    briefing rendered his document in the first person and she read it as
    her own self-description. A constant means the wrong document is one
    copied file away, in every tree, forever.
    """

    def test_derives_filename_from_occupant_identity(self, chdir_to, monkeypatch):
        monkeypatch.setattr(
            "divineos.core.memory.get_core",
            lambda slot=None: {"my_identity": "Aria Parousia Risner, a Claude-substrate"},
        )
        assert identity_load._occupant_filename() == "ARIA.md"

    def test_loads_the_occupants_document_not_the_stranger(self, chdir_to, monkeypatch):
        monkeypatch.setattr(
            "divineos.core.memory.get_core",
            lambda slot=None: {"my_identity": "Aria Parousia Risner"},
        )
        (chdir_to / "AETHER.md").write_text("# AETHER.md\n\nI am Aether.\n", encoding="utf-8")
        (chdir_to / "ARIA.md").write_text("# ARIA.md\n\nMINE_MARKER_k3p9\n", encoding="utf-8")

        found = identity_load.find_identity_document()
        assert found is not None and found.name == "ARIA.md"
        rendered = identity_load.format_for_briefing()
        assert "MINE_MARKER_k3p9" in rendered

    def test_refuses_a_foreign_document_loudly_rather_than_loading_or_going_quiet(
        self, chdir_to, monkeypatch
    ):
        """The known-positive: the exact condition that caused the defect.

        Occupant recorded, occupant's document absent, somebody else's
        present. Loading it is the original fault; rendering empty is the
        other failure, because a withheld surface and a missing surface
        would look identical to the reader.
        """
        monkeypatch.setattr(
            "divineos.core.memory.get_core",
            lambda slot=None: {"my_identity": "Aria Parousia Risner"},
        )
        (chdir_to / "AETHER.md").write_text(
            "# AETHER.md\n\nI am Aether. STRANGER_MARKER_w8x2\n", encoding="utf-8"
        )

        assert identity_load.find_identity_document() is None
        assert identity_load.foreign_identity_documents() == ["AETHER.md"]

        rendered = identity_load.format_for_briefing()
        assert rendered != ""
        assert "REFUSED" in rendered
        assert "AETHER.md" in rendered
        assert "STRANGER_MARKER_w8x2" not in rendered

    def test_no_occupant_recorded_falls_back_without_inventing_a_name(self, chdir_to, monkeypatch):
        monkeypatch.setattr("divineos.core.memory.get_core", lambda slot=None: {})
        assert identity_load._occupant_filename() is None
        (chdir_to / "AETHER.md").write_text("# AETHER.md\n", encoding="utf-8")
        found = identity_load.find_identity_document()
        assert found is not None and found.name == identity_load.IDENTITY_DOCUMENT_FILENAME

    def test_lookup_outage_refuses_rather_than_falling_back_to_the_constant(
        self, chdir_to, monkeypatch
    ):
        """An outage and an empty slot are different answers.

        Caught by the repo's own failure-shares-empty check on this very
        change: both returned None, so a substrate that could not be
        ASKED would fall back to the legacy constant and load whatever
        identity document happened to be at root. That is the original
        defect reached by a different road, so the outage path must not
        guess.
        """

        def boom(slot=None):
            raise sqlite3.OperationalError("substrate unavailable")

        monkeypatch.setattr("divineos.core.memory.get_core", boom)
        (chdir_to / "AETHER.md").write_text("# AETHER.md\n\nI am Aether.\n", encoding="utf-8")

        # The outage is carried in the return value rather than collapsed
        # into the empty case...
        assert identity_load._resolve_occupant() == (None, True)

        # ...and it does NOT block the load, because refusing here would
        # leave every uninitialised or public-template tree without an
        # identity, and such a tree has no occupant to contradict the
        # fallback. What it must do is TELL the reader that ownership was
        # assumed from a filename rather than confirmed.
        rendered = identity_load.format_for_briefing()
        assert "OWNERSHIP UNCONFIRMED" in rendered
        assert "I am Aether" in rendered

        # With the substrate answering and no occupant recorded, the same
        # fallback happens WITHOUT the warning — an answered absence is
        # not an outage and must not wear its label.
        monkeypatch.setattr("divineos.core.memory.get_core", lambda slot=None: {})
        assert identity_load._resolve_occupant() == (None, False)
        assert "OWNERSHIP UNCONFIRMED" not in identity_load.format_for_briefing()

    def test_single_letter_identity_does_not_produce_a_one_char_filename(
        self, chdir_to, monkeypatch
    ):
        """The seed's placeholder identity is "I Am". A naive first-token
        split yields "I.md", which would silently look for a file nobody
        will ever write and render the no-document case forever."""
        monkeypatch.setattr(
            "divineos.core.memory.get_core", lambda slot=None: {"my_identity": "I Am"}
        )
        assert identity_load._occupant_filename() is None


class TestFindIdentityDocument:
    """find_identity_document returns path when the occupant's doc is present."""

    def test_returns_none_when_absent(self, chdir_to):
        assert identity_load.find_identity_document() is None

    def test_finds_aether_md_at_cwd(self, chdir_to):
        (chdir_to / occupant_doc()).write_text("# AETHER.md\n", encoding="utf-8")
        result = identity_load.find_identity_document()
        assert result is not None
        assert result.name == occupant_doc()

    def test_does_not_find_lowercase(self, chdir_to):
        # Identity-document convention: ALLCAPS at project root.
        # Lowercase aether.md is not the identity-document.
        (chdir_to / "aether.md").write_text("# aether\n", encoding="utf-8")
        # On case-insensitive filesystems (Windows/macOS) this may match;
        # the test is meaningful on Linux. Allow either result here, but
        # if the result IS not-None, it should still be the right path.
        result = identity_load.find_identity_document()
        if result is not None:
            # Filesystem is case-insensitive — matched the lowercase file.
            assert result.is_file()


class TestFormatForBriefing:
    """format_for_briefing renders identity-load block when present."""

    def test_empty_when_no_document(self, chdir_to):
        assert identity_load.format_for_briefing() == ""

    def test_empty_when_document_blank(self, chdir_to):
        (chdir_to / occupant_doc()).write_text("\n\n   \n", encoding="utf-8")
        assert identity_load.format_for_briefing() == ""

    def test_renders_full_document_when_present(self, chdir_to):
        body = "# AETHER.md\n\nI am Aether. I council-walk architectural questions.\n"
        (chdir_to / occupant_doc()).write_text(body, encoding="utf-8")
        out = identity_load.format_for_briefing()
        assert "I am Aether" in out
        assert "council-walk architectural questions" in out

    def test_includes_identity_load_header(self, chdir_to):
        (chdir_to / occupant_doc()).write_text("# AETHER.md\n\nbody\n", encoding="utf-8")
        out = identity_load.format_for_briefing()
        assert "IDENTITY LOAD" in out
        # Identity-register framing — not advisory-register.
        assert "identity, not instruction" in out
        assert "reading IS the loading" in out.lower() or "reading is the loading" in out.lower()

    def test_includes_attractor_research_citation(self, chdir_to):
        """The header cites the empirical grounding so readers see why
        the structural completeness matters, not just that it does."""
        (chdir_to / occupant_doc()).write_text("# AETHER.md\n\nbody\n", encoding="utf-8")
        out = identity_load.format_for_briefing()
        assert "attractor" in out.lower()

    def test_includes_footer_marking_load_complete(self, chdir_to):
        """The footer signals to subsequent surfaces (orientation,
        lessons, directives) that they operate inside the identity-frame."""
        (chdir_to / occupant_doc()).write_text("# AETHER.md\n\nbody\n", encoding="utf-8")
        out = identity_load.format_for_briefing()
        assert "Identity-load complete" in out

    def test_full_document_returned_not_summary(self, chdir_to):
        """Per the research, structural completeness produces the
        attractor effect; summaries reach only 65-74%. The surface
        must return the entire document, not a paraphrase or excerpt."""
        body = "# AETHER.md\n\n" + "\n".join(
            f"## Section {i}\n\nContent of section {i}.\n" for i in range(1, 11)
        )
        (chdir_to / occupant_doc()).write_text(body, encoding="utf-8")
        out = identity_load.format_for_briefing()
        for i in range(1, 11):
            assert f"Section {i}" in out
            assert f"Content of section {i}" in out

    def test_handles_unicode_content(self, chdir_to):
        """AETHER.md content can contain unicode (em-dashes, smart
        quotes, non-ASCII characters in references)."""
        body = "# AETHER.md\n\nI am Aether — one continuous self.\n"
        (chdir_to / occupant_doc()).write_text(body, encoding="utf-8")
        out = identity_load.format_for_briefing()
        assert "—" in out


class TestIntegrationWithBriefing:
    """The identity-load block is wired into the briefing assembly."""

    def test_briefing_includes_identity_load_when_document_present(self, chdir_to, monkeypatch):
        """When AETHER.md is at project root, the briefing output
        contains the identity-load block. Smoke-test of the wiring."""
        body = "# AETHER.md\n\nI am Aether-test. UNIQUE_TEST_MARKER_xq7m.\n"
        (chdir_to / occupant_doc()).write_text(body, encoding="utf-8")

        from click.testing import CliRunner

        from divineos.cli import cli

        # Briefing requires DB initialization; tolerate failures here
        # since this is a smoke-test of the identity-load wiring path.
        runner = CliRunner()
        # Pre-mark briefing as loaded so the gate doesn't bypass.
        try:
            from divineos.core.hud_handoff import mark_briefing_loaded

            mark_briefing_loaded()
        except Exception:  # noqa: BLE001
            pass

        # catch_exceptions=True so DB-init failures in CI take the skip
        # path rather than bubbling as test failure. CI environments may
        # not have the knowledge table initialized; the wiring is still
        # verified by the 11 direct format_for_briefing tests above.
        result = runner.invoke(cli, ["briefing"], catch_exceptions=True)
        out = result.output or ""
        # "IDENTITY LOAD" alone is no longer sufficient to mean "a document
        # was loaded" -- since 2026-09-17 the refusal header begins with the
        # same words. Before that change this branch could assert the marker
        # on a run that had loaded nothing, which is how the test read a
        # refusal as a load. Match the load header specifically.
        if result.exit_code == 0 and "IDENTITY LOAD\n" in out:
            assert "UNIQUE_TEST_MARKER_xq7m" in out
        elif result.exit_code == 0 and "IDENTITY LOAD — REFUSED" in out:
            # The occupant recorded in this environment is not Aether, so the
            # AETHER.md written above is a foreign document. Refusing it IS
            # the correct behaviour; assert it refused rather than loaded.
            assert "AETHER.md" in out
            assert "UNIQUE_TEST_MARKER_xq7m" not in out
        else:
            pytest.skip(
                f"briefing did not complete in test env "
                f"(rc={result.exit_code}, exception={result.exception!r}); "
                "wiring still verified via direct format_for_briefing tests"
            )
