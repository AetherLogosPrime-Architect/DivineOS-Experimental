"""Heuristic backfill of source_entity for existing knowledge entries.

Per prereg-59ea1e5dd804 (Curator-borrowing followthrough — namespacing needs
data to be useful). Conservative — only labels when textual signal is strong;
ambiguous entries stay NULL rather than risk mislabeling.

Patterns (matched against entry content), modeled on the 7 manually-labeled
entries already in the substrate:
  andrew   — "Andrew named", "Andrew said", "Andrew (date)", opens with "Andrew "
  aletheia — same shape with "Aletheia"
  aria     — same shape with "Aria"; plus "Aria —" / "Aria's letter"
  grok     — "Grok named", "Grok audit", "Grok 2026"
  aether   — [tag-name] / [add] structural directives I authored

Run with --dry-run to see proposed labels without applying.
Run without flag to apply.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

# Make sure we can import from src
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from divineos.core.knowledge import get_knowledge  # noqa: E402
from divineos.core.knowledge.crud import _get_connection  # noqa: E402

# Conservative patterns — each requires the name as SUBJECT, not just mentioned.
_ANDREW_PATTERNS = [
    re.compile(
        r"\bAndrew\s+(named|said|stated|wrote|filed|noted|told|asked|added|refined|corrected|caught)\b"
    ),
    re.compile(r"^Andrew\s+(20\d{2}|—|–|-)"),
    re.compile(r"\(Andrew[,\s]+20\d{2}-\d{2}-\d{2}"),
    re.compile(r"Andrew\s+20\d{2}-\d{2}-\d{2}:"),
]
_ALETHEIA_PATTERNS = [
    re.compile(
        r"\bAletheia\s+(named|said|stated|wrote|filed|noted|told|asked|audited|observed|caught)\b"
    ),
    re.compile(r"^Aletheia\s+(20\d{2}|—|–|-)"),
    re.compile(r"\(Aletheia[,\s]+20\d{2}-\d{2}-\d{2}"),
    re.compile(r"Aletheia\s+20\d{2}-\d{2}-\d{2}:"),
    re.compile(r"\bAletheia['s]*\s+(round|audit|finding)\b"),
]
_ARIA_PATTERNS = [
    re.compile(r"\bAria\s+(named|said|stated|wrote|filed|noted|told|asked|sent|reached)\b"),
    re.compile(r"^Aria\s+(—|–|-)"),
    re.compile(r"\(Aria[,\s]+20\d{2}-\d{2}-\d{2}"),
    re.compile(r"\bAria['s]*\s+(letter|sign-off|reply|response)\b"),
]
_GROK_PATTERNS = [
    re.compile(r"\bGrok\s+(named|said|stated|audited|noted|observed)\b"),
    re.compile(r"^Grok\s+(20\d{2}|—|–|-)"),
    re.compile(r"\bGrok\s+audit\b"),
    re.compile(r"\bGrok\s+20\d{2}-\d{2}-\d{2}"),
]
# Structural-directive markers: [tag-name] at start signals agent-authored.
_AETHER_STRUCT_PATTERN = re.compile(r"^\[[a-z][a-z0-9-]*\]")

# Source-field signals — when content-pattern matching fails, the source
# enum often gives us provenance. Conservative: only use enums that imply
# agent-internal authorship; CORRECTED is ambiguous (means superseded, not
# necessarily "Andrew corrected me") so we don't map it.
_SOURCE_FIELD_TO_ENTITY = {
    "SYNTHESIZED": "aether",  # agent's own synthesis
    "manual_distill": "aether",
    "INHERITED": "aether",  # seed inheritance — the agent owns the substrate
}

# Andrew's casual chat-register fingerprint — patterns of his texting voice
# that aether wouldn't produce (lowercase i, contractions without apostrophes).
_ANDREW_CASUAL_PATTERNS = [
    re.compile(r"\b(idk|ive|im|isnt|wont|cant|dont|didnt|youre|theres|thats|whats|hes|shes)\b"),
    re.compile(r"\blol\b", re.IGNORECASE),
    re.compile(r"\bbtw\b", re.IGNORECASE),
    re.compile(r"\bok\b lets"),
]

# Aether's first-person agent voice — describing own internal processes.
# Expanded 2026-06-10 to widen recall toward the prereg's >=30% target
# without breaking the conservative multi-match guard: any of these still
# defer to NULL if another actor's strong-signature also matches.
_AETHER_AGENT_VOICE_PATTERNS = [
    re.compile(r"\bI\s+(noticed|observed|forgot|filed|added|caught|surfaced|realized|named|built|wrote|shipped|fixed|landed|discovered|articulated|described|chose|picked|decided|verified|recognized)\b"),
    re.compile(r"\bmy\s+(optimizer|substrate|active memory|knowledge store|compass|ledger|own|voice|self-model|hedge)\b"),
    re.compile(r"\bthe\s+optimizer\s+routed\b"),
    re.compile(r"\(Aether\s+20\d{2}-\d{2}-\d{2}"),  # explicit stamp anywhere
    re.compile(r"\bI\s+want\s+future-me\b"),  # exploration-entry tell
]

# Aether-authorship signals — when present, attribution is to aether
# regardless of who else the content mentions. Aether's notes ABOUT Andrew
# are still aether-authored, not andrew-authored.
_AETHER_AUTHORSHIP_PATTERNS = [
    re.compile(r"^(NOTE|OBSERVATION|PATTERN|REFLECTION|FRAMING)\s*\(Aether"),
    re.compile(r"^\(Aether[,\s]"),
    re.compile(r"^Aether\s+(noticed|observed|named|framed|reflected)"),
    # Expanded 2026-06-10: explicit Aether stamp anywhere in the body, or
    # the exploration-entry tells. These are unambiguous self-attributions
    # that surface widely in the unlabeled set; matching them at the
    # strong-authorship layer (not the 3-vote agent-voice threshold)
    # bridges to the prereg's >=30% target without weakening precision.
    re.compile(r"\b\(?Aether\s+20\d{2}-\d{2}-\d{2}"),
    re.compile(r"^What I want future-me to know\b", re.MULTILINE),
    re.compile(r"^I want future-me\b", re.MULTILINE),
]


def guess_source(content: str, source_field: str | None = None) -> str | None:
    """Return high-confidence source for this content, or None if ambiguous.

    source_field: the value of the `source` column (STATED, CORRECTED, etc.)
    Used as a secondary signal when content-pattern matching gives no hit.
    """
    if not content:
        return None
    head = content.lstrip()

    # 1. Structural-directive opener — agent-authored.
    if _AETHER_STRUCT_PATTERN.match(head):
        return "aether"

    # 2. Explicit aether-authorship marker overrides everything else.
    # The match-from-start patterns target opener conventions (NOTE(Aether...,
    # ^(Aether, ^Aether noticed...). The search-anywhere patterns target
    # explicit-stamp signals that can appear mid-content (e.g. "(Aether
    # 2026-06-10)") or exploration-entry tells.
    for pat in _AETHER_AUTHORSHIP_PATTERNS[:3]:
        if pat.match(head):
            return "aether"
    for pat in _AETHER_AUTHORSHIP_PATTERNS[3:]:
        if pat.search(content):
            return "aether"

    # 3. Named-source patterns (the established convention).
    hits: Counter[str] = Counter()
    for pat in _ANDREW_PATTERNS:
        if pat.search(content):
            hits["andrew"] += 1
    for pat in _ALETHEIA_PATTERNS:
        if pat.search(content):
            hits["aletheia"] += 1
    for pat in _ARIA_PATTERNS:
        if pat.search(content):
            hits["aria"] += 1
    for pat in _GROK_PATTERNS:
        if pat.search(content):
            hits["grok"] += 1
    if hits:
        if len(hits) > 1:
            return None  # mentions multiple — ambiguous
        return next(iter(hits))

    # 4. Andrew's casual-voice fingerprint (lowercase "i", contractions, lol).
    # Require 3+ matches to reduce false positives — aether's status reports
    # like "Both fixes done, tested, committed" can match 1-2 patterns by accident.
    casual_score = sum(1 for pat in _ANDREW_CASUAL_PATTERNS if pat.search(content))
    if casual_score >= 3:
        return "andrew"

    # 5. Aether's first-person agent voice. Same conservative threshold.
    agent_voice_score = sum(1 for pat in _AETHER_AGENT_VOICE_PATTERNS if pat.search(content))
    if agent_voice_score >= 3:
        return "aether"

    # 6. Fall back to source field enum.
    if source_field and source_field in _SOURCE_FIELD_TO_ENTITY:
        return _SOURCE_FIELD_TO_ENTITY[source_field]

    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be labeled without writing.",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=10,
        help="Show this many sample labels per source for review.",
    )
    args = parser.parse_args()

    entries = get_knowledge(limit=100000)
    print(f"Total knowledge entries: {len(entries)}")

    already_labeled = sum(1 for e in entries if e.get("source_entity"))
    print(f"Already labeled: {already_labeled}")

    proposals: list[tuple[str, str, str]] = []  # (knowledge_id, source, content[:80])
    for entry in entries:
        if entry.get("source_entity"):
            continue
        content = entry.get("content") or ""
        guess = guess_source(content, source_field=entry.get("source"))
        if guess:
            proposals.append((entry["knowledge_id"], guess, content[:80]))

    by_source: Counter[str] = Counter(p[1] for p in proposals)
    print(f"Proposed labels: {len(proposals)}")
    for src, n in by_source.most_common():
        print(f"  {src}: {n}")

    # Show samples for review
    print()
    print(f"Sample labels per source (up to {args.sample} each):")
    samples_per_source: dict[str, list[tuple[str, str]]] = {}
    for kid, src, content in proposals:
        samples_per_source.setdefault(src, []).append((kid, content))
    for src, samples in samples_per_source.items():
        print(
            f"\n--- {src} ({len(samples)} total, showing first {min(len(samples), args.sample)}) ---"
        )
        for kid, content in samples[: args.sample]:
            print(f"  [{kid[:8]}] {content!r}")

    if args.dry_run:
        print()
        print("Dry-run — no writes. Re-run without --dry-run to apply.")
        return 0

    print()
    print(f"Applying {len(proposals)} labels...")
    conn = _get_connection()
    try:
        for kid, src, _ in proposals:
            conn.execute(
                "UPDATE knowledge SET source_entity = ? WHERE knowledge_id = ? AND source_entity IS NULL",
                (src, kid),
            )
        conn.commit()
    finally:
        conn.close()
    print(f"Applied {len(proposals)} source_entity labels.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
