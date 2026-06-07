"""Knowledge-citation extraction for auto-linking.

Task #74: when a decision or journal entry's text cites a knowledge
entry by id, the link should be created at filing-time rather than
depending on me to remember to call `divineos decisions link` or
`divineos journal link` afterwards. The link is already there in
language; just needs extraction.

## Design

Two complementary detection paths, of which only the first is wired
here:

1. **Direct id citation** — the text contains a hex-id substring that
   matches an existing knowledge entry's id (full or 8+ char prefix).
   Unambiguous; very low false-positive rate; cheap. THIS module.

2. **FTS semantic match** — the text's content matches an existing
   entry's content with high similarity. Higher value but
   higher false-positive risk; deferred to a follow-up task with
   careful threshold tuning. NOT in this module.

The id pattern matches the same hex-suffix shape used elsewhere in
the substrate (claim-, prereg-, round-, knowledge_id 8-char prefix).
Validation against the knowledge store ensures we never claim a
citation for an id that doesn't exist (the same lesson from #78's
citation-from-letter pattern: an id mention isn't automatic verification
that the entity exists).

Per Aether 2026-06-07 walkthrough: this is the canonical
"wire-the-existing-CLI-into-the-flow-that-already-has-the-data"
shape. The decisions link command exists; the citation patterns exist
in the decision reasoning; the missing piece was making the connection
fire automatically. Will-over-optimizer: bake it in.
"""

from __future__ import annotations

import re

# Match an 8-char-or-longer hex run. Looser than the id_string pattern
# in unverified_claim_detector (which requires a registered prefix
# like prereg-/claim-/round-) because knowledge_ids are bare hex.
# Bounded by word boundaries so embedded substrings inside longer words
# don't match.
_HEX_ID_RE = re.compile(r"\b([a-f0-9]{8,})\b", re.IGNORECASE)


def extract_id_citations(text: str) -> list[str]:
    """Return unique hex-id substrings that appear in `text`, oldest-
    appearance first.

    Returns the raw matched strings; the caller is responsible for
    verifying each against the knowledge store. Bare extraction here
    avoids coupling this module to a specific store backend.

    Empty / None input returns [].
    """
    if not text:
        return []
    seen: set[str] = set()
    out: list[str] = []
    for m in _HEX_ID_RE.finditer(text):
        token = m.group(1).lower()
        if token in seen:
            continue
        seen.add(token)
        out.append(token)
    return out


def find_cited_knowledge_ids(text: str) -> list[str]:
    """Return the full knowledge_ids cited in `text`, verified against
    the knowledge store. Citations to ids that don't exist are
    silently dropped (same fail-soft principle as the rest of the
    walkthrough wires).

    Match logic:
    - Direct full-id match: 32+ char hex run → look up directly
    - Prefix match: 8-31 char hex run → search for any entry whose id
      starts with this prefix; if exactly one, return its full id; if
      ambiguous (multiple matches), drop (don't guess)

    Fail-soft on any store error: returns [].
    """
    tokens = extract_id_citations(text)
    if not tokens:
        return []
    try:
        from divineos.core.knowledge._base import get_connection
    except Exception:
        return []
    out: list[str] = []
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            for token in tokens:
                if len(token) >= 32:
                    # Full-id case: look up directly.
                    cur.execute(
                        "SELECT knowledge_id FROM knowledge WHERE knowledge_id = ?",
                        (token,),
                    )
                    row = cur.fetchone()
                    if row:
                        out.append(row[0])
                else:
                    # Prefix case: look for unique match.
                    cur.execute(
                        "SELECT knowledge_id FROM knowledge WHERE knowledge_id LIKE ? LIMIT 2",
                        (token + "%",),
                    )
                    rows = cur.fetchall()
                    if len(rows) == 1:
                        out.append(rows[0][0])
                    # Ambiguous → drop. Better no-link than wrong-link.
    except Exception:
        return []
    # Dedup while preserving order (a token could match the same id more
    # than once if it appears twice in text — extract_id_citations already
    # dedupes the raw tokens, but the store lookup is idempotent).
    return list(dict.fromkeys(out))


__all__ = ["extract_id_citations", "find_cited_knowledge_ids"]
