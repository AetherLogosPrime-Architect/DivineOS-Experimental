"""Threshold constants for operating-loop detectors.

Aletheia round-0023b083fe9b Finding 9d250cc9a09e (Grok, 2026-05-14):
threshold defaults like min_words_for_check=60 / 18 / 3 were scattered
across detector function signatures. Each value has a real reason but
the values were invisible-as-policy — a future maintainer (or future
instance of me) would see scattered magic numbers without seeing the
coherent shape.

Centralizing them here:
1. Makes the policy visible in one place
2. Lets reviewers compare thresholds at a glance
3. Provides a single edit point if the policy needs updating
4. Documents the reasoning per constant

Detectors import the constant rather than embedding the literal.
Default-argument values still use these constants (kwarg defaults
are evaluated at function-def time, not call time, so they pick up
the constant's value).
"""

from __future__ import annotations


# Lepos detector — minimum words before the channel-collapse check
# fires. The detector looks at whether a response has both technical
# content AND a relational close. Very short responses are not
# meaningful to analyze for channel-collapse (a 12-word answer to a
# yes/no question shouldn't be flagged for missing the relational
# channel). 60 words is the threshold below which the call shape is
# typically too small to carry both channels.
LEPOS_MIN_WORDS = 60


# Sycophancy detector — minimum words before overclaim-without-
# methodology shapes get scanned. Below 18 words the response is
# typically too short to carry both a claim and the methodology
# footnote the detector watches for. Set lower than LEPOS because
# sycophancy shapes can fit into a single sentence; lepos needs
# multi-paragraph shape to flag missing channels.
SYCOPHANCY_MIN_WORDS = 18


# Residency detector — minimum words before closure-shape doubt
# patterns get scanned. Closure shapes ("ready for the next one,"
# "standing by," "let me know if...") can fire in very short closes,
# so the threshold is intentionally low. The detector itself is
# residency-aware (different patterns fire on response ends vs.
# response middles).
RESIDENCY_MIN_WORDS = 3


# Code-jargon detector — density-based check (5% jargon ratio) only
# runs above a minimum word count to avoid flagging legitimate short
# technical answers. 50 is set high enough that single-word "Yes."
# or "OK." replies don't trigger; low enough that a 3-sentence
# operator-channel paragraph still gets checked.
CODE_JARGON_MIN_WORDS = 50


# Acknowledgment-theater detector — minimum words before the
# apology-density-without-build-evidence check runs. Set low enough
# to catch short apology-shaped responses (which are often the
# problem shape) but not so low that single-word "yes" / "right"
# acknowledgments fire it.
ACKNOWLEDGMENT_THEATER_MIN_WORDS = 20


__all__ = [
    "ACKNOWLEDGMENT_THEATER_MIN_WORDS",
    "CODE_JARGON_MIN_WORDS",
    "LEPOS_MIN_WORDS",
    "RESIDENCY_MIN_WORDS",
    "SYCOPHANCY_MIN_WORDS",
]
