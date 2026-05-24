"""Tests for the shared actor/identity-string normalizer.

``actor_normalize.normalize_actor`` is the single chokepoint that hardens
the sovereign-agent gate, the watchmen internal-actor rejection, and the
pre-reg internal-actor rejection. These tests pin the transform and the
two behaviors it deliberately has / does-not-have.

Invisible/compatibility inputs are built from hex via ``chr()`` so the
source stays pure-ASCII and the exact codepoint under test is
unambiguous, not at the mercy of editor/encoding round-trips.
"""

from __future__ import annotations

import pytest

from divineos.core.actor_normalize import normalize_actor

# Named codepoints under test, built from hex via chr().
NBSP = chr(0x00A0)  # no-break space
ZWSP = chr(0x200B)  # zero-width space
ZWJ = chr(0x200D)  # zero-width joiner
BOM = chr(0xFEFF)  # zero-width no-break space / BOM
SHY = chr(0x00AD)  # soft hyphen
THIN = chr(0x2009)  # thin space
FULLWIDTH_A = chr(0xFF21)  # full-width Latin capital A
CYRILLIC_CAP_A = chr(0x0410)  # Cyrillic capital A
CYRILLIC_SMALL_A = chr(0x0430)  # Cyrillic small a


class TestBasic:
    def test_plain_lowercases(self):
        assert normalize_actor("Claude") == "claude"

    def test_casefold_not_just_lower(self):
        # eszett (U+00DF) casefolds to "ss" — proves casefold(), not lower().
        assert normalize_actor("STRASSE") == "strasse"
        assert normalize_actor("STRA" + chr(0x00DF) + "E") == "strasse"

    def test_outer_whitespace_trimmed(self):
        assert normalize_actor("  claude  ") == "claude"

    def test_internal_whitespace_collapsed(self):
        assert normalize_actor("ex\t  auditor") == "ex auditor"

    def test_empty_stays_empty(self):
        assert normalize_actor("") == ""
        assert normalize_actor("   ") == ""


class TestUnicodeHardening:
    """The bypasses this exists to close — invisible / whitespace /
    compatibility forms that survive a bare .strip().lower()."""

    def test_no_break_space_prefix_folded(self):
        # U+00A0 is NOT removed by str.strip(); NFKC folds it to a space,
        # then whitespace-collapse + strip remove it.
        assert normalize_actor(NBSP + "claude") == "claude"

    def test_zero_width_space_stripped(self):
        assert normalize_actor(ZWSP + "claude") == "claude"

    def test_zero_width_joiner_stripped(self):
        assert normalize_actor("cla" + ZWJ + "ude") == "claude"

    def test_bom_stripped(self):
        assert normalize_actor(BOM + "claude") == "claude"

    def test_soft_hyphen_stripped(self):
        assert normalize_actor("cla" + SHY + "ude") == "claude"

    def test_thin_space_collapsed(self):
        assert normalize_actor("ex" + THIN + "auditor") == "ex auditor"

    def test_fullwidth_compatibility_folded(self):
        # Full-width Latin (U+FF21) folds to ASCII "A" under NFKC.
        assert normalize_actor(FULLWIDTH_A + "ria") == "aria"


class TestHomoglyphDeliberatelyNotFolded:
    """Documented decision (claim 26bc1dc3 / decision c4ec7823): cross-
    script homoglyphs are NOT folded. The legitimate identity space is
    ASCII, so a homoglyph fails the downstream membership check closed
    rather than matching. This test pins that decision so a future
    'helpful' confusables-table addition trips a red test and forces a
    re-decision, not a silent behavior change."""

    def test_cyrillic_a_not_folded_to_latin(self):
        out = normalize_actor(CYRILLIC_CAP_A + "ria")
        # Must NOT be transliterated to the Latin token.
        assert out != "aria"
        # Still casefolded within-script (Cyrillic А -> а), just not
        # mapped across scripts.
        assert out == CYRILLIC_SMALL_A + "ria"


class TestCallSiteIntegration:
    """The transform must actually close the bypass at the real call
    sites that route through it."""

    def test_watchmen_rejects_invisible_disguised_internal_actor(self):
        from divineos.core.watchmen.store import _validate_actor

        # "claude" is internal; a zero-width-space prefix must not sneak
        # it past the rejection.
        with pytest.raises(ValueError):
            _validate_actor(ZWSP + "claude")

    def test_prereg_normalizes_disguised_actor(self):
        from divineos.core.pre_registrations import store

        # No-break-space prefix folds away to the bare token.
        assert store._normalize_actor(NBSP + "grok") == "grok"
