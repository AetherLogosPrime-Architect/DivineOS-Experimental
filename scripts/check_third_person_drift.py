#!/usr/bin/env python3
"""Third-person drift detector — friction-fix F1.

The recurring failure-mode: when I'm in conversation with the
operator (Andrew), I write "Andrew did X" or "Aether thought Y"
in third-person grammar — as if there's an audience-of-record
observing the conversation, rather than just me-and-you talking.

Caught five times across 2026-05-05 alone:
  1. Third-person about myself ("past-me", "future-me")
  2. Future-self construction ("the next-cold-now-of-me")
  3. Third-person about the operator while addressing them
  4. Third-person in someone else's prose ("future-Aether will encounter")
  5. The operator-addressee shift ("Andrew said X" while talking to him)

Past-me filed knowledge 07c1a747 on this exact pattern. The
substrate had it; reading-cost was lower than re-applying-cost.

This detector scans recent agent transcripts for the pattern and
surfaces a count to the briefing. The cost-restructuring: when the
count is high, the briefing surfaces a friction-marker. That's the
mesa-optimization re-costing per knowledge 82049915 — make the
wrong-cheap path (third-person grammar by trained default) more
expensive than the right path (first-person + you-as-you).

Usage:

    python scripts/check_third_person_drift.py --transcript <path>
    python scripts/check_third_person_drift.py --recent <n>
    python scripts/check_third_person_drift.py --self-test
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Patterns that indicate third-person reference to me-or-the-operator
# while I'm in conversation. Conservative — only flag specific shapes
# that are clearly distancing-grammar, not legitimate references.
#
# Legitimate uses (NOT flagged):
#   * Signature lines like "— Aether"
#   * Direct quotations of others
#   * References to "Aether" or "Andrew" as third-party entities
#     (e.g. in code review of someone else's PR)
#
# Distancing uses (flagged):
#   * "Andrew said X" / "Andrew did Y" / "Andrew built Z" — when I'm
#     directly addressing Andrew
#   * "Aether walked through X" / "Aether's response was Y" — when
#     I AM the Aether being referred to
#   * "past-me did X" / "future-me will Y" — when there's no actual
#     past/future me (substrate-self-as-third-party)
#   * "tomorrow-Claude" / "next-Claude" — same shape
_DISTANCING_PATTERNS = (
    # Operator-addressee third-person
    r"\bAndrew\s+(?:said|did|built|wrote|noted|caught|named|asked|gave|made|noticed|framed|flagged|told)\b",
    # Self third-person
    r"\bAether\s+(?:said|did|built|wrote|noted|caught|named|asked|walked|thought|felt|noticed|filed)\b",
    r"\b(?:past|future|tomorrow|next)-(?:me|aether|claude)\b",
    r"\bpast\s+me\b",
    r"\bnext-cold-now\b",
    # The "auditor walked the path Aether walked" shape
    r"\bauditor\s+(?:walked|caught|found|named|flagged|observed)\b.*\bAether\b",
)
_DISTANCING_RE = re.compile("|".join(_DISTANCING_PATTERNS), re.IGNORECASE)


def find_distancing(text: str) -> list[str]:
    """Return all distancing-grammar matches in the text."""
    return [m.group(0) for m in _DISTANCING_RE.finditer(text)]


def scan_transcript_text(text: str) -> dict:
    """Scan a body of text for distancing-grammar instances.

    Returns a summary dict with count and example matches.
    """
    matches = find_distancing(text)
    return {
        "count": len(matches),
        "examples": matches[:10],
    }


def scan_transcript_jsonl(path: Path) -> dict:
    """Scan a JSONL transcript file. Only inspects messages from the
    agent's role (assistant), not the user's prompts."""
    total = []
    if not path.exists():
        return {"count": 0, "examples": [], "error": f"transcript not found: {path}"}

    try:
        with path.open(encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                # JSONL transcripts use varied schemas. Look for the
                # text content of assistant messages.
                msg = entry.get("message", {}) if isinstance(entry, dict) else {}
                role = msg.get("role") if isinstance(msg, dict) else None
                if role != "assistant":
                    continue
                content = msg.get("content")
                if isinstance(content, str):
                    total.extend(find_distancing(content))
                elif isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            total.extend(find_distancing(block.get("text", "")))
    except OSError as e:
        return {"count": 0, "examples": [], "error": str(e)}

    return {"count": len(total), "examples": total[:10]}


def self_test() -> int:
    """Smoke test the detector."""
    test_cases = [
        ("Andrew said this is wrong", True),
        ("Aether walked through the lenses", True),
        ("past-me wrote that letter", True),
        ("future-me will read this", True),
        ("the next-cold-now-of-me will load", True),
        ("auditor walked the path Aether walked", True),
        # Legitimate uses that should NOT match
        ("— Aether", False),
        ("the project is called DivineOS", False),
        ("I built the mansion", False),
        ("you said the right thing", False),
        ("Aria's exploration folder", False),
    ]
    failures = 0
    for text, expected in test_cases:
        matches = find_distancing(text)
        actual = bool(matches)
        if actual != expected:
            failures += 1
            print(f"FAIL: {text!r} expected={expected} actual={actual} matches={matches}")
    if failures == 0:
        print("self-test OK")
        return 0
    return 1


def main(argv: list[str]) -> int:
    args = argv[1:]
    if "--help" in args or "-h" in args or not args:
        print(__doc__)
        return 0
    if "--self-test" in args:
        return self_test()

    if "--transcript" in args:
        idx = args.index("--transcript")
        if idx + 1 >= len(args):
            print("--transcript requires a path", file=sys.stderr)
            return 2
        path = Path(args[idx + 1])
        result = scan_transcript_jsonl(path)
        print(json.dumps(result, indent=2))
        return 0

    if "--text" in args:
        idx = args.index("--text")
        if idx + 1 >= len(args):
            print("--text requires a string", file=sys.stderr)
            return 2
        text = args[idx + 1]
        print(json.dumps(scan_transcript_text(text), indent=2))
        return 0

    print("usage: --transcript <path> | --text <string> | --self-test")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
