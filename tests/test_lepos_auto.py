"""Tests for lepos_auto — plain-section detection + auto-discharge + close-time block.

Task #80 — auto-firing structure for the lepos translation-debt store.
The detector that previously fired only on a current-turn jargon-wall
now composes with a debt-block gate that fires when PRIOR-turn debt
sits unpaid going into close.

Tests cover:
- extract_plain_section recognizes the patterns I actually use
- extract_plain_section silent on jargon-only / em-dash-only replies
- auto_discharge_outstanding fires only when plain section present
- debt_block_reason fires when: debt outstanding + no plain section + father-addressed
- debt_block_reason silent for family-addressed turns (the gate is
  father-channel only, mirroring _lepos_gate_reason)
- BLOCK case (per Aether 2026-06-07 broken-gate-all-day lesson): the
  block reason string actually contains the recovery instruction
"""

from __future__ import annotations

import pytest
from unittest.mock import patch


from divineos.core.lepos_auto import (
    auto_discharge_outstanding,
    debt_block_reason,
    extract_plain_section,
)


# ── Plain-section recognition ────────────────────────────────────────


class TestExtractPlainSection:
    def test_bolded_plain_label_recognized(self):
        # Test ONE concern: regex finds the **Plain:** header. Content
        # of plain section is semantically UNRELATED to the preceding
        # text so the new semantic-similarity restate-theater check
        # (Phase 2 wiring, 2026-06-11) doesn't fire on it.
        text = (
            "Technical: I extended the verify-claim detector with a "
            "letter-citation source-trace augmentation.\n\n"
            "---\n\n"
            "**Plain:**\n\n"
            "The apple harvest came in early this year and the orchard smells like cider."
        )
        section = extract_plain_section(text)
        assert section is not None
        assert "apple harvest" in section

    def test_bolded_plain_with_parenthetical_recognized(self):
        # The shape I used today: "Plain (real this time):"
        text = (
            "Wall of jargon here with detectors and matchers.\n\n"
            "**Plain (real this time):**\n\n"
            "Here's what it does for you in everyday words."
        )
        section = extract_plain_section(text)
        assert section is not None
        assert "everyday words" in section

    def test_heading_plain_recognized(self):
        text = "Some technical setup.\n\n## Plain\n\nThe hook fires before any push."
        section = extract_plain_section(text)
        assert section is not None
        assert "hook fires" in section

    def test_in_plain_words_recognized(self):
        text = (
            "I refactored the consultation_tracker module to use a new "
            "FTS index. In plain words: I sped up the lookup that "
            "happens at the start of every turn."
        )
        section = extract_plain_section(text)
        assert section is not None
        assert "sped up the lookup" in section

    def test_for_you_recognized(self):
        text = (
            "Technical implementation done.\n\n"
            "For you: the system now warns when you push from a stale branch."
        )
        section = extract_plain_section(text)
        assert section is not None

    def test_pure_jargon_no_match(self):
        text = (
            "Refactored unverified_claim_detector.py to add source_letter "
            "field. Wired the caller layer in operating_loop_audit.py to "
            "load family/letters/*.md and pass through letter_contents. "
            "Tests in test_unverified_claim_detector.py cover the BLOCK case."
        )
        assert extract_plain_section(text) is None

    def test_em_dash_alone_does_not_count(self):
        # The 2026-06-06 correction: em-dash restates like
        # "ELMO — compress old events" are jargon-to-jargon, not plain
        # sections. The detector should not be fooled by them.
        text = (
            "ELMO — compress old events. Wired into sleep cycle phase 4. "
            "fix-encoding — repairs mojibake via ftfy. Lands as a "
            "maintenance pass."
        )
        assert extract_plain_section(text) is None

    def test_empty_returns_none(self):
        assert extract_plain_section("") is None
        assert extract_plain_section(None) is None  # type: ignore[arg-type]


# ── Auto-discharge ──────────────────────────────────────────────────


class TestAutoDischarge:
    def test_no_outstanding_no_discharge(self):
        with patch("divineos.core.lepos_debt.list_outstanding", return_value=[]):
            n = auto_discharge_outstanding("any text with **Plain:** here")
        assert n == 0

    def test_no_plain_section_no_discharge(self):
        """2026-06-13 reconciliation: discharge fires on plain-section
        OR writer-presence. A substantive jargon-wall with no interior
        markers and no plain section produces no discharge.

        The text needs to be long enough (>= 60 words) for the writer-
        presence detector to actually run AND have no first-person
        pronouns / direct address to fail the voice check."""
        wall_text = (
            "The fix went through two iterations. The first version dropped the "
            "PowerShell scan entirely and trusted only the mutex. That over-fired "
            "because the mutex has cross-process visibility issues. The second "
            "version brought the scan back but built target strings at runtime "
            "via chr() concatenation. The literal never appears in the source. "
            "Tests pass. Verified both directions. The build went through cleanly."
        )
        with (
            patch(
                "divineos.core.lepos_debt.list_outstanding",
                return_value=[{"id": 1}, {"id": 2}],
            ),
            patch("divineos.core.lepos_debt.discharge", return_value=True) as mock_discharge,
        ):
            n = auto_discharge_outstanding(wall_text)
        assert n == 0
        mock_discharge.assert_not_called()

    def test_plain_section_discharges_outstanding(self):
        debts = [{"id": 10}, {"id": 11}, {"id": 12}]
        text = "Technical wall here.\n\n**Plain:** the system now does X automatically."
        discharged_ids = []

        def fake_discharge(debt_id, translation):
            discharged_ids.append(debt_id)
            return True

        with (
            patch("divineos.core.lepos_debt.list_outstanding", return_value=debts),
            patch("divineos.core.lepos_debt.discharge", side_effect=fake_discharge),
        ):
            n = auto_discharge_outstanding(text)
        assert n == 3
        # FIFO: oldest first (the list_outstanding contract)
        assert discharged_ids == [10, 11, 12]

    def test_discharge_caps_at_5_per_turn(self):
        debts = [{"id": i} for i in range(20)]
        text = "Wall here.\n\n**Plain:** very brief plain section."
        with (
            patch("divineos.core.lepos_debt.list_outstanding", return_value=debts),
            patch("divineos.core.lepos_debt.discharge", return_value=True) as mock_discharge,
        ):
            n = auto_discharge_outstanding(text)
        assert n == 5
        assert mock_discharge.call_count == 5


# ── Debt-block gate ──────────────────────────────────────────────────


class TestDebtBlockReason:
    def test_silent_for_family_addressed(self):
        # Family-channel content is exempt — mirrors _lepos_gate_reason
        # behavior. Aria's letter doesn't get a jargon-gate block.
        with patch(
            "divineos.core.lepos_debt.list_outstanding",
            return_value=[{"id": 1}],
        ):
            assert debt_block_reason("any text", addressed_to_father=False) is None

    def test_silent_when_no_outstanding(self):
        with patch("divineos.core.lepos_debt.list_outstanding", return_value=[]):
            assert debt_block_reason("any text", addressed_to_father=True) is None

    def test_silent_when_plain_section_present(self):
        # The plain section will auto-discharge in the same turn —
        # blocking would be redundant.
        with patch(
            "divineos.core.lepos_debt.list_outstanding",
            return_value=[{"id": 1}],
        ):
            text = "Jargon here.\n\n**Plain:** here's what it does."
            assert debt_block_reason(text, addressed_to_father=True) is None

    def test_blocks_when_debt_outstanding_and_no_plain_section(self):
        # The BLOCK case. Per 2026-06-07 broken-gate-all-day lesson:
        # this test exercises the block-firing path end-to-end so the
        # gate cannot ship silently broken.
        # 2026-06-13 reconciliation: text must be substantive (>= 60 words)
        # AND voice-absent (no first-person pronouns) for the block to
        # fire — short or voice-rich text now discharges debt automatically.
        wall_text = (
            "The fix went through two iterations. The first version dropped the "
            "PowerShell scan entirely and trusted only the mutex. That over-fired "
            "because the mutex has cross-process visibility issues. The second "
            "version brought the scan back but built target strings at runtime "
            "via chr() concatenation. The literal never appears in the source. "
            "Tests pass. Verified both directions. The build went through cleanly."
        )
        with patch(
            "divineos.core.lepos_debt.list_outstanding",
            return_value=[{"id": 1}, {"id": 2}],
        ):
            reason = debt_block_reason(wall_text, addressed_to_father=True)
        assert reason is not None
        assert "LEPOS DEBT GATE" in reason
        assert "2" in reason  # the count
        assert "plain section" in reason  # the recovery hint

    def test_blocks_with_single_debt(self):
        wall_text = (
            "The fix went through two iterations. The first version dropped the "
            "PowerShell scan entirely and trusted only the mutex. That over-fired "
            "because the mutex has cross-process visibility issues. The second "
            "version brought the scan back but built target strings at runtime "
            "via chr() concatenation. The literal never appears in the source. "
            "Tests pass. Verified both directions. The build went through cleanly."
        )
        with patch(
            "divineos.core.lepos_debt.list_outstanding",
            return_value=[{"id": 1}],
        ):
            reason = debt_block_reason(wall_text, addressed_to_father=True)
        assert reason is not None
        assert "1 outstanding" in reason


# ─── Semantic-similarity wiring (Phase 2, 2026-06-11) ────────────────


def _semantic_available() -> bool:
    try:
        from divineos.core.semantic_store import embed

        return embed("test sentence to confirm model loads") is not None
    except Exception:
        return False


_skip_no_semantic = pytest.mark.skipif(
    not _semantic_available(),
    reason="semantic-similarity primitive unavailable (ml extras missing)",
)


@_skip_no_semantic
class TestSemanticRestateCheck:
    """Phase 2 wiring (2026-06-11): extract_plain_section uses semantic
    similarity to catch thesaurus-restatement that vocabulary-overlap
    misses. Andrew's load-bearing example: 'compass observation system
    tracks moral spectrum drift' vs 'substrate's ethical-direction
    monitor logs deviation across virtues' — almost no shared words,
    identical meaning. The morning's check passed it as 'real
    translation'; this wiring catches it."""

    def test_thesaurus_restate_fails_semantic_check(self):
        original = (
            "The compass observation system tracks moral spectrum "
            "drift over time, recording each event with evidence and "
            "position."
        )
        thesaurus = (
            "The substrate's ethical-direction monitor logs deviation "
            "across virtues chronologically, capturing every incident "
            "with backing facts and stance."
        )
        text = original + "\n\n---\n\n**Plain:**\n\n" + thesaurus
        assert extract_plain_section(text) is None

    def test_real_translation_passes_semantic_check(self):
        technical = (
            "Refactored the unverified_claim_detector to add a "
            "source_letter field threaded through the operating_loop_"
            "audit caller layer. The change required updating the "
            "JSONL schema and the FTS index for fast lookup."
        )
        real_translation = (
            "If I quote a fake reference from a note someone wrote "
            "me, the system can now tell me which note that fake "
            "reference came from. So I can stop and fix it instead "
            "of slipping past."
        )
        text = technical + "\n\n**Plain:**\n\n" + real_translation
        section = extract_plain_section(text)
        assert section is not None
        assert "fake reference" in section

    def test_no_preceding_text_passes(self):
        text = "**Plain:**\n\nEverything is working as expected today."
        section = extract_plain_section(text)
        assert section is not None

    def test_completely_unrelated_section_passes(self):
        preceding = (
            "I refactored the unverified_claim_detector to add a "
            "source_letter field threaded through operating_loop_audit."
        )
        unrelated = (
            "Today was a good day. The weather was warm and the "
            "river ran clear by the bank where I sat reading."
        )
        text = preceding + "\n\n**Plain:**\n\n" + unrelated
        section = extract_plain_section(text)
        assert section is not None
