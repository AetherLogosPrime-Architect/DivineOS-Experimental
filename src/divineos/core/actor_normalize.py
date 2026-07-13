"""Shared actor/identity-string normalization.

Single source of truth for the unicode-hardening that defends identity
checks against invisible-, whitespace-, and compatibility-form bypasses.

## Why this module exists

Three places in the codebase decide something security- or
discipline-relevant from an identity string:

* ``watchmen.store._validate_actor`` — rejects internal actors so the
  running agent cannot file its own audit findings as external.
* ``pre_registrations.store._normalize_actor`` — same internal-actor
  rejection on pre-reg outcome recording.
* ``family.seal_hook`` — the sovereign-agent spawn gate.

The first two grew *independent, near-identical* copies of the same
NFKC + invisible-strip + casefold transform (both cite the 2026-05-03
round-12 audit finding; the pre-reg copy's docstring even says "same
fix shape that landed for watchmen.store._validate_actor"). Duplicated
safety-critical code drifts out of sync — fix one site, forget the
other. This module collapses the duplication to one tested function so
the hardening is defined once and shared.

## What it defends against (and what it deliberately does NOT)

DEFENDS: unicode-whitespace and compatibility forms (U+00A0 no-break
space, U+2009 thin space, full-width forms) via NFKC, plus invisible /
zero-width characters (U+200B-U+200F, U+FEFF, U+00AD) that NFKC and
``str.strip()`` both leave in place. Without this, a no-break-space or
zero-width-space prefix slips an otherwise-matching token past a
literal frozenset membership check.

Does NOT defend against cross-script homoglyphs (e.g. Cyrillic U+0410,
which renders identically to Latin "A"). NFKC does not fold confusables
across scripts, and we deliberately do not add a confusables table: the
legitimate identity space here is ASCII (registered agent names, known
actor tokens), so a homoglyph input fails the downstream
membership/lookup closed rather than matching anything — the practical
exploit cannot land. Adding cross-script folding would be defense for a
threat that can't reach a sensitive path, at the cost of over-folding
legitimate names. Decision recorded; see claim 26bc1dc3.
"""

from __future__ import annotations

# Self-enforcement: this is the single normalization chokepoint for the
# sovereign-agent spawn gate AND the watchmen / pre-reg internal-actor
# rejection. Weakening normalize_actor (dropping the invisible-strip,
# the NFKC fold, or the casefold) silently weakens all three identity
# checks at once — the highest-leverage self-modification attack surface
# of the set. Guardrailed per Finding 48 class-fix discipline; the marker
# travels with the load-bearing file and must stay in sync with
# scripts/guardrail_files.txt (enforced by test_guardrail_marker_consistency).
__guardrail_required__ = True

import re
import unicodedata

# Invisible / zero-width codepoints that survive both NFKC and
# ``str.strip()``: zero-width space, ZWNJ, ZWJ, LRM, RLM, ZWNBSP/BOM,
# soft hyphen. Stripped so a leading/embedded invisible cannot disguise
# an otherwise-matching identity token.
_INVISIBLE_CODEPOINTS = (0x200B, 0x200C, 0x200D, 0x200E, 0x200F, 0xFEFF, 0x00AD)
_INVISIBLE_RE = re.compile("[" + "".join(chr(cp) for cp in _INVISIBLE_CODEPOINTS) + "]")
_WHITESPACE_RE = re.compile(r"\s+")


def normalize_actor(actor: str) -> str:
    """Return the canonical, casefolded form of an identity string.

    Sequence: NFKC (fold compatibility/whitespace forms) -> strip
    invisible/zero-width chars -> collapse internal whitespace runs to a
    single space and trim -> casefold. Empty input normalizes to ``""``;
    callers that forbid empty actors check the result themselves (the
    transform is policy-free on purpose so each caller keeps its own
    rejection rules).
    """
    nfkc = unicodedata.normalize("NFKC", actor)
    invisible_stripped = _INVISIBLE_RE.sub("", nfkc)
    collapsed = _WHITESPACE_RE.sub(" ", invisible_stripped).strip()
    return collapsed.casefold()


__all__ = ["normalize_actor"]
