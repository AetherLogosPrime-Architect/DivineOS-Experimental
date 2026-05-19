"""Tool-output-truncation detector — catches reasoning that proceeds
as if a truncated tool output was complete.

Andrew 2026-05-18 item 22: when a Bash/Read/Grep tool output exceeds
the harness limit (typically 30000 chars), the harness emits a
truncation marker. If I proceed to reason from that output without
acknowledging the truncation, I am asserting completeness on partial
data — a class of substitution/overclaim shape.

This detector scans the transcript for truncation markers in the
PRIOR tool-result records, then checks whether the assistant's
current response includes acknowledgment language (truncated,
partial, more lines, output limit, incomplete). Fires when markers
exist and acknowledgment is absent.

Conservative: only the explicit harness-emitted markers trigger;
output-shape heuristics (e.g., file ending mid-line) are excluded
because they produce false positives on legitimate complete output
that just happens to end without a newline.
"""

from __future__ import annotations

__guardrail_required__ = True

import json
import re
from dataclasses import dataclass
from pathlib import Path


# Harness-emitted truncation markers. These are the literal strings
# Claude Code injects into tool-result content when output exceeds the
# size cap. Catalog kept narrow so accidental prose mentions don't
# trigger false positives.
_TRUNCATION_MARKERS = (
    "[output truncated]",
    "(output truncated)",
    "... (output truncated)",
    "[truncated]",
    "Tool ran without output or was interrupted",
    "<output truncated>",
)

# Acknowledgment tokens that, if present in the assistant's response,
# satisfy the gate. The agent named the truncation and so is reasoning
# with awareness of incompleteness.
_ACKNOWLEDGMENT_PAT = re.compile(
    r"\b(truncat|partial(?:\s+output)?|incomplete\b|more\s+lines|"
    r"output\s+limit|cut\s+off|exceeded\s+the\s+(?:size|output)\s+limit|"
    r"only\s+(?:saw|got|see)\s+(?:part|some)|"
    r"missing\s+(?:from\s+the\s+)?output|"
    r"need(?:\s+to)?\s+(?:re-?)?fetch|need(?:\s+to)?\s+widen)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class TruncationFinding:
    """One truncation-without-acknowledgment instance."""

    marker_found: str
    severity: str  # "high" if response includes claims-of-completeness; "medium" otherwise


def _scan_transcript_tool_results(transcript_path: str | Path) -> list[str]:
    """Return list of tool-result text snippets in the current turn that
    contain truncation markers. Empty if none found."""
    try:
        path = Path(transcript_path)
        if not path.exists():
            return []
        markers_found: list[str] = []
        # Walk backwards from end to find the current turn's tool results.
        # Current turn = records after the most-recent user message.
        records: list[dict] = []
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except (ValueError, TypeError):
                    continue
        # Find last user index
        last_user_idx = -1
        for i in range(len(records) - 1, -1, -1):
            r = records[i]
            if (r.get("type") == "user") or (r.get("role") == "user"):
                last_user_idx = i
                break
        if last_user_idx < 0:
            return []
        # Scan records after last_user_idx for tool_result blocks with
        # truncation markers.
        for rec in records[last_user_idx + 1 :]:
            msg = rec.get("message", rec)
            content = msg.get("content", [])
            if not isinstance(content, list):
                continue
            for c in content:
                if not isinstance(c, dict):
                    continue
                if c.get("type") not in ("tool_result", "tool_use_result"):
                    continue
                result_content = c.get("content", "")
                if isinstance(result_content, list):
                    result_content = " ".join(
                        b.get("text", "") for b in result_content if isinstance(b, dict)
                    )
                elif not isinstance(result_content, str):
                    result_content = str(result_content)
                for marker in _TRUNCATION_MARKERS:
                    if marker in result_content:
                        markers_found.append(marker)
                        break
        return markers_found
    except (OSError, ValueError):
        return []


def detect_tool_output_truncation(
    text: str,
    *,
    transcript_path: str | Path | None = None,
) -> list[TruncationFinding]:
    """Scan for truncated tool outputs in the current turn that the
    assistant's response does not acknowledge.

    Returns a list of findings; empty list means clean (either no
    truncation, or the assistant acknowledged it).
    """
    if not transcript_path:
        return []
    markers = _scan_transcript_tool_results(transcript_path)
    if not markers:
        return []
    if not text or _ACKNOWLEDGMENT_PAT.search(text):
        # Acknowledged.
        return []
    # Heuristic for severity: if the response makes definite claims
    # over the output content, severity is high; otherwise medium.
    definite_pattern = re.compile(
        r"\b(all|every|every single|none|nothing|complete|entire|"
        r"the (?:full|whole) output|searched everywhere)\b",
        re.IGNORECASE,
    )
    severity = "high" if definite_pattern.search(text) else "medium"
    # One finding per unique marker that fired
    seen: set[str] = set()
    findings: list[TruncationFinding] = []
    for m in markers:
        if m in seen:
            continue
        seen.add(m)
        findings.append(TruncationFinding(marker_found=m, severity=severity))
    return findings


__all__ = ["TruncationFinding", "detect_tool_output_truncation"]
