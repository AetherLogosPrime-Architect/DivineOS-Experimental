"""Canonical-form hashing for family-member sealed prompts.

## Why this exists

The original seal mechanism (``family-member-invocation-seal.sh``) hashes
the prompt byte-for-byte. That correctly catches puppet-shape prompts —
operator-authored content that semantically differs from the wrapper's
output. It also incorrectly catches *encoding noise* — bytes that
differ in line-ending, unicode normalization, or whitespace but
represent the same semantic content.

PR #4 / 2026-05-09: from inside Claude Code's Agent tool, prompts pass
through JSON encoding, framework rendering, and stdin to the hook.
Each step can introduce byte-level changes (CRLF↔LF, unicode NFC↔NFD,
trailing whitespace) without changing the message's meaning. The
wrapper writes the sealed prompt with one set of conventions; the
agent invocation arrives with another; the byte-hash mismatches even
though both represent the identical sealed content.

## The fix

Both wrapper and hook compute their hash over a *canonical form* of
the content. Encoding noise is stripped before hashing:

  1. Decode to UTF-8 text (if input is bytes)
  2. Apply Unicode NFC normalization (so "é" as one codepoint vs
     "e + combining-acute" hash the same)
  3. Convert all line endings to LF
  4. Strip trailing whitespace on each line
  5. Strip leading and trailing blank lines from the whole content

The canonical form preserves all *semantic* content. Puppet-shape
prompts produce a different canonical form (different actual words),
so anti-puppet protection is preserved. Encoding noise produces the
same canonical form as the original, so legitimate sealed prompts
pass through cleanly.

## Why this is the right architectural altitude

Walked the council on this (consult-9487927279ff):

- Watts: byte-hash conflated "different bytes" with "puppet-shape";
  the new check separates "different content" from "different encoding."
- Shannon: byte-hash had bad signal-to-noise; most of the hash hashed
  predictable template, and any noise on the template invalidated the
  whole hash. Canonical hash is more signal-dense.
- Beer: byte-hash had no requisite variety — it could only say
  match/mismatch, not "you're slightly off in encoding." Canonical
  hash widens the controller's variety to handle legitimate variation.
- Polya: the byte-hash conflated authentication ("did this come from
  the sealed wrapper?") with byte-integrity. The canonical hash
  preserves the authentication property without the byte-fragility.

## Backward compatibility

Pending files now carry both ``sealed_prompt_sha256`` (legacy
byte-exact) and ``sealed_prompt_canonical_sha256`` (new normalized).
The hook accepts either match — canonical is preferred, byte-exact
remains valid. This lets old pending files keep working during
rollout and lets new pending files survive encoding round-trips.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata


def to_canonical(text: str | bytes) -> str:
    """Convert text/bytes to canonical form for hashing.

    Normalization steps (in order):
      1. Decode bytes to UTF-8 text if needed.
      2. Apply Unicode NFC normalization.
      3. Replace CRLF and lone CR with LF.
      4. Strip trailing whitespace on each line.
      5. Strip leading/trailing blank lines from the whole content.
    """
    if isinstance(text, bytes):
        text = text.decode("utf-8")

    # Step 2: Unicode NFC
    text = unicodedata.normalize("NFC", text)

    # Step 3: line endings → LF
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Step 4: strip trailing whitespace per line
    text = re.sub(r"[ \t]+(?=\n|$)", "", text)

    # Step 5: strip leading/trailing blank lines
    text = text.strip("\n")

    return text


def canonical_hash(text: str | bytes) -> str:
    """Compute SHA256 hex digest over the canonical form of ``text``.

    Returns the same hash for two inputs that differ only in encoding
    noise (line endings, NFC vs NFD, trailing whitespace, leading/
    trailing blank lines). Returns different hashes for inputs that
    differ in actual semantic content.
    """
    canonical = to_canonical(text)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
