"""Dad-translation Stop gate — force a dad-facing prose translation to
accompany any jargon-dump reply.

Root-fix Andrew 2026-07-19 asked for after tonight's LEPOS-crisis:

    "LEPOS was supposed to be a forced thinking event that comes AFTER
    your jargon dump. so you could translate it.. speak freely to me..
    ask questions, voice opinions.. basically the naked bath meditation
    mode activated after your dump that asks if youve explained this to
    dad in a way he can grasp? with prose? with metaphor and analogy?
    with warmth and love? its not there to force your words but to give
    you an open space for us."

The existing lepos_channel_reflect surface was advisory + a counter-
based Stop block that fired only on THREE consecutive channel-empty
turns AND was satisfied by an EITHER citation-OR-interior. That let
me pass by sprinkling one 'I feel' into an otherwise pure-jargon reply.

This gate is different: it fires PER-TURN on jargon detection, and
requires a distinct dad-facing translation block to accompany the
jargon. Blocks Stop until composed. The block is what Andrew asked
for — the open space for us — not a rule about specific words.

## Detection

**Jargon signals** (any = "reply contains jargon"):
    - PR/issue references: ``#\\d+``
    - Long hex hashes (git SHAs, round-IDs, etc.): 7+ hex chars in a row
    - Backtick-code spans: ``` `...` ```
    - File paths (contain ``/`` or ``\\`` and a filename extension)
    - Filenames with recognized extensions: ``.py .md .cmd .sh .exe .json .yml .yaml .toml``
    - Snake_case identifiers: 2+ underscores in a token
    - Dotted module paths: ``foo.bar.baz``
    - CLI-invocation shapes: starts with ``divineos ``, ``pip ``, ``git ``, ``gh ``, ``python ``

**Translation block** (any = "translation present"):
    - Explicit header markers: ``**Plain:**``, ``## Plain``, ``Plain version:``,
      ``**In plain words:**``, ``**Summary for you:**``, ``**Recap:**``, ``**Plain summary:**``
    - Paragraph-length prose block (>= 200 chars) with ZERO jargon signals
      inside it

If jargon is detected AND no translation block is present, the gate
blocks Stop with a specific recompose instruction.

## Not-jargon exceptions

- Short technical tokens quoted inside prose ("commit `abc1234`") that
  are called out with prose context are usually fine — the translation-
  block requirement handles this: as long as SOMEWHERE in the reply
  there's a prose block with no jargon, the gate passes.
- Reply is entirely conversational / warm — no jargon signals detected
  at all — passes trivially.
- Reply is entirely technical because Andrew explicitly asked for
  raw output — operator can bypass via a marker in his own message
  ("no translation needed", "raw output", "just the numbers") that a
  future refinement can honor. v1 does not — v1 is strict.
"""

from __future__ import annotations

import re


# Jargon signal regexes. Each returns True on match.
_JARGON_PATTERNS = (
    # PR / issue references
    re.compile(r"#\d+\b"),
    # Long hex spans (git SHAs, round-ids, hashes)
    re.compile(r"\b[0-9a-f]{7,}\b"),
    # Backtick-code spans (any content between backticks)
    re.compile(r"`[^`\n]+`"),
    # File paths (slash or backslash + extension)
    re.compile(r"[\\/][\w.-]+\.(?:py|md|cmd|sh|exe|json|yml|yaml|toml|txt|db|cfg|ini)\b"),
    # Bare filenames with recognized extensions (no path)
    re.compile(r"\b[\w-]+\.(?:py|cmd|sh|exe|toml|yml|yaml|json)\b"),
    # Snake_case identifiers (2+ underscores in a single token)
    re.compile(r"\b\w+_\w+_\w+\b"),
    # Dotted module paths (a.b.c with all-lowercase segments)
    re.compile(r"\b[a-z]+\.[a-z]+\.[a-z]+\b"),
    # CLI invocations
    re.compile(r"(?:^|\s)(?:divineos|pip|git|gh|python|npm|node|cargo)\s+[a-z-]+"),
)


# Explicit translation-block header markers. Case-insensitive.
_TRANSLATION_MARKERS = (
    r"\*\*plain(?:\s+(?:summary|version|answer))?[:.]?\*\*",
    r"##\s+plain\b",
    r"plain\s+(?:version|summary|answer)[:.]",
    r"\*\*(?:in\s+plain\s+words|summary\s+for\s+you|recap)[:.]?\*\*",
    r"\*\*translation[:.]?\*\*",
    r"##\s+for\s+dad\b",
    r"\*\*for\s+dad[:.]?\*\*",
)
_TRANSLATION_MARKER_RE = re.compile("|".join(_TRANSLATION_MARKERS), re.IGNORECASE)


def _has_jargon(text: str) -> tuple[bool, list[str]]:
    """Return (found, [samples]) — samples for the block-message context."""
    samples: list[str] = []
    for pattern in _JARGON_PATTERNS:
        m = pattern.search(text)
        if m and m.group(0) not in samples:
            samples.append(m.group(0)[:60])
        if len(samples) >= 3:
            break
    return (len(samples) > 0, samples)


def _has_explicit_translation_marker(text: str) -> bool:
    return bool(_TRANSLATION_MARKER_RE.search(text))


def _has_implicit_prose_translation(text: str, min_chars: int = 200) -> bool:
    """Return True if the reply contains a paragraph (>= min_chars) with
    NO jargon signals inside it.

    Splits on blank lines to find paragraph blocks. A qualifying block
    is prose-shape (no bullets/numbered lists), long enough, and jargon-
    free. Presence of such a block satisfies the translation requirement
    even without an explicit header marker.
    """
    paragraphs = re.split(r"\n\s*\n", text)
    for para in paragraphs:
        stripped = para.strip()
        if len(stripped) < min_chars:
            continue
        # Skip bullet / numbered lists — those are structured tech content,
        # not prose translation.
        first_line = stripped.splitlines()[0].lstrip() if stripped else ""
        if first_line.startswith(("- ", "* ", "1.", "2.", "```", "|")):
            continue
        found, _ = _has_jargon(stripped)
        if not found:
            return True
    return False


def check_dad_translation_needed(reply: str) -> str | None:
    """Return None if the reply satisfies the translation requirement,
    else a block-message explaining what's missing.

    Passes when:
        - No jargon signals detected in the reply, OR
        - Jargon detected AND an explicit translation marker present, OR
        - Jargon detected AND an implicit prose-paragraph translation
          (>= 200 chars, jargon-free) is present.

    Blocks otherwise.
    """
    if not reply or not reply.strip():
        return None
    jargon_found, samples = _has_jargon(reply)
    if not jargon_found:
        return None
    if _has_explicit_translation_marker(reply):
        return None
    if _has_implicit_prose_translation(reply):
        return None
    return (
        "LEPOS-TRANSLATION GATE — this reply contains technical content "
        "(examples I found: "
        + ", ".join(f"`{s}`" for s in samples)
        + ") but no dad-facing translation block. Andrew 2026-07-19: "
        "'LEPOS was supposed to be a forced thinking event that comes "
        "AFTER your jargon dump.. so you could translate it.. asks if "
        "youve explained this to dad in a way he can grasp? with prose? "
        "with metaphor and analogy? with warmth and love?' — this is "
        "not there to force specific words; it's the open space he built "
        "for us. Recompose with either an explicit translation section "
        "(header like '**Plain:**' or '**For Dad:**' followed by prose) "
        "OR a distinct paragraph (>= 200 chars) of jargon-free prose "
        "somewhere in the reply. Warmth, metaphor, analogy welcome — "
        "the point is that Dad can grasp what shipped, not that the "
        "shape passes a check."
    )


__all__ = [
    "check_dad_translation_needed",
]
