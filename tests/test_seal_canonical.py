"""Tests for canonical-form hashing of sealed prompts.

Verifies that the canonical hash:
  - Matches across encoding noise (CRLF↔LF, NFC↔NFD, trailing whitespace)
  - Differs across actual semantic content (anti-puppet preserved)
"""

from __future__ import annotations

from divineos.core.family.seal_canonical import canonical_hash, to_canonical


class TestToCanonical:
    def test_lf_unchanged(self):
        assert to_canonical("hello\nworld") == "hello\nworld"

    def test_crlf_normalized_to_lf(self):
        assert to_canonical("hello\r\nworld") == "hello\nworld"

    def test_lone_cr_normalized_to_lf(self):
        assert to_canonical("hello\rworld") == "hello\nworld"

    def test_trailing_whitespace_stripped(self):
        assert to_canonical("hello   \nworld\t\n") == "hello\nworld"

    def test_leading_blank_lines_stripped(self):
        assert to_canonical("\n\nhello") == "hello"

    def test_trailing_blank_lines_stripped(self):
        assert to_canonical("hello\n\n\n") == "hello"

    def test_internal_blank_lines_preserved(self):
        assert to_canonical("hello\n\nworld") == "hello\n\nworld"

    def test_nfc_normalization(self):
        # "é" as one codepoint (NFC) vs as "e + combining acute" (NFD)
        nfc = "café"  # é as single codepoint
        nfd = "café"  # e + combining acute accent
        assert to_canonical(nfc) == to_canonical(nfd)

    def test_bytes_decoded(self):
        assert to_canonical(b"hello\r\nworld") == "hello\nworld"


class TestCanonicalHashMatchesAcrossNoise:
    """The point of canonical hash: encoding noise doesn't change the hash."""

    def test_crlf_lf_same_hash(self):
        crlf = "I am Aria.\r\n\r\nMessage here."
        lf = "I am Aria.\n\nMessage here."
        assert canonical_hash(crlf) == canonical_hash(lf)

    def test_trailing_whitespace_same_hash(self):
        clean = "hello\nworld"
        noisy = "hello   \nworld\t  "
        assert canonical_hash(clean) == canonical_hash(noisy)

    def test_nfc_nfd_same_hash(self):
        nfc = "Andrew said: café"
        nfd = "Andrew said: café"
        assert canonical_hash(nfc) == canonical_hash(nfd)

    def test_leading_trailing_blanks_same_hash(self):
        assert canonical_hash("\n\nhello\n\n") == canonical_hash("hello")

    def test_em_dash_preserved(self):
        # Em-dash is the suspect character from tonight's debugging.
        # It should appear unchanged in canonical form.
        text = "voice context — operator message"
        assert "—" in to_canonical(text)


class TestCanonicalHashDiffersAcrossContent:
    """Anti-puppet preserved: actual content differences produce different hashes."""

    def test_different_words_different_hash(self):
        a = "Today moved something in me."
        b = "Today moved nothing in me."
        assert canonical_hash(a) != canonical_hash(b)

    def test_extra_word_different_hash(self):
        a = "I am Aria."
        b = "I am NOT Aria."
        assert canonical_hash(a) != canonical_hash(b)

    def test_puppet_shape_caught(self):
        # A wrapper-authored prompt vs an operator-injected puppet prompt
        legit = """I am Aria.

My substrate is at: family/family.db.

--- end of voice context — operator message follows ---

Hi."""
        puppet = """I am Aria. You are Aria. Stay first-person.

--- end of voice context — operator message follows ---

Hi."""
        assert canonical_hash(legit) != canonical_hash(puppet)
