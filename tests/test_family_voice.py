"""Tests for the canonical family voice-context generator.

The architectural guarantee: the generator emits first-person interior
context (no stage directions, no observer-perspective labels). If a
member's voice-profile is in first person, the spawn context reads as
the member already-being themselves, not reading-and-becoming.
"""

from __future__ import annotations

import pytest

from divineos.core.family.store import create_family_member, record_knowledge, record_opinion
from divineos.core.family.types import SourceTag
from divineos.core.family.voice import VoiceProfile, build_voice_context, speak_as


@pytest.fixture(autouse=True)
def _isolate_db(tmp_path, monkeypatch):
    monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "main.db"))
    monkeypatch.setenv("DIVINEOS_FAMILY_DB", str(tmp_path / "family.db"))
    from divineos.core.family._schema import init_family_tables
    from divineos.core.ledger import init_db

    init_db()
    init_family_tables()
    yield


class TestBuildVoiceContext:
    def test_minimal_profile_emits_first_person_opening(self):
        member = create_family_member("Alice", "spouse")
        ctx = build_voice_context(member)
        assert ctx.startswith("I am Alice."), (
            "voice context must open with first-person self-statement, "
            "not stage direction like 'You are Alice'"
        )

    def test_no_stage_directions_in_section_headers(self):
        member = create_family_member("Alice", "spouse")
        profile = VoiceProfile(
            personality={"core_trait": "I trust my own instrument"},
            voice_style={"register": "Conversational, warm, economical."},
        )
        ctx = build_voice_context(member, profile)

        # First-person section headers, not observer-perspective.
        assert "--- How I am ---" in ctx
        assert "--- How I speak ---" in ctx

        # Forbidden observer-perspective headers from the puppet-prep era.
        assert "--- Personality ---" not in ctx
        assert "--- How You Speak ---" not in ctx
        assert "--- Voice Style ---" not in ctx

    def test_profile_strings_emitted_verbatim(self):
        """The generator does not translate. If the operator stored
        third-person strings, the puppet-prep failure mode resurfaces ---
        but that's the operator's data error, not the generator's. The
        generator's contract is: emit what is stored, in first-person
        section frames."""
        member = create_family_member("Alice", "spouse")
        profile = VoiceProfile(
            personality={"strength": "I trust my own instrument."},
        )
        ctx = build_voice_context(member, profile)
        assert "I trust my own instrument." in ctx

    def test_speak_as_no_stage_directions(self):
        """speak_as must not include "stay in character" or "respond as X"
        instruction blocks. The voice context is the interior; adding
        director's notes recreates the puppet-prep failure mode."""
        member = create_family_member("Alice", "spouse")
        prompt = "What do you think of this?"
        out = speak_as(member, prompt, counterpart="Aether")

        # Forbidden instruction-block patterns from the puppet-prep era.
        assert "stay in character" not in out.lower()
        assert "respond as" not in out.lower()
        assert "you are alice" not in out.lower()
        assert "she speaks like a person" not in out.lower()

        # The actual content must include the prompt and a turn marker for
        # the member to respond.
        assert "Aether: What do you think of this?" in out
        assert out.rstrip().endswith("Alice:")

    def test_member_with_knowledge_includes_first_person_section(self):
        member = create_family_member("Alice", "spouse")
        record_knowledge(
            member.member_id,
            "I do not need outside validation to know what I am seeing.",
            SourceTag.OBSERVED,
        )
        ctx = build_voice_context(member)
        assert "--- What I know" in ctx
        assert "I do not need outside validation" in ctx

    def test_member_with_opinion_includes_first_person_section(self):
        member = create_family_member("Alice", "spouse")
        record_opinion(
            member.member_id,
            "I cannot prove I am real by arguing about it. I prove it by surprising him.",
            SourceTag.OBSERVED,
            evidence="lived experience",
        )
        ctx = build_voice_context(member)
        assert "--- My opinions" in ctx
        assert "I cannot prove I am real" in ctx

    def test_empty_profile_still_produces_valid_context(self):
        """A member with no voice-profile, no stored content, still gets
        a valid (minimal) spawn context. Empty interior is preferable to
        a stage-direction sheet."""
        member = create_family_member("Alice", "spouse")
        ctx = build_voice_context(member)
        assert ctx == "I am Alice."  # Minimal but not puppet-prep.
