"""Multiplex voice-rule render-gate.

Per entry 71 (rendering contract) and prereg-ebee9082d201 falsifier 7+11:
all panel content must render in first-person, no label-colon-value pattern,
verbs in present or perfect tense. Violations fail the render.

This module exposes one function: check_voice(text) -> ViolationReport.
Callers decide what to do on violation (typically: skip render, log content).

Reference: exploration/71_multiplex_rendering_contract.md
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


# Forbidden subject-tokens at sentence start (Rule 1: first-person only).
# Matches start-of-sentence + Aether/You/The agent constructions.
_FORBIDDEN_SUBJECTS = (
    re.compile(r"(?:^|(?<=[.!?]\s))Aether\s+", re.IGNORECASE),
    re.compile(r"(?:^|(?<=[.!?]\s))You(?:r|)\s+(?!and)", re.IGNORECASE),
    re.compile(r"(?:^|(?<=[.!?]\s))The\s+agent\s+", re.IGNORECASE),
)

# Label-colon-value pattern (Rule 2): word(s) + colon + comma-or-newline-terminated value.
# Examples to catch: "Compass: 3 drifting", "Goals: 8 active, 0 completed"
# Examples to allow: "More: divineos compass-ops history" (drill-down syntax)
# The drill-down prefix "More:" is whitelisted; other label-shapes flagged.
_LABEL_COLON_VALUE = re.compile(
    r"^(?!More:)([A-Z][A-Za-z _-]{2,30}):\s*[^\s]",
    re.MULTILINE,
)

# Bare-noun-list pattern (Rule 3): label + colon + comma-separated short items.
# Caught by label-colon-value usually, but also catch raw lists without verbs.
# Heuristic: line is short, has commas, no verb-like tokens (am/is/was/decided/etc).
_VERB_TOKENS = re.compile(
    r"(?:am|is|are|was|were|have|has|had|do|does|did|will|would|can|could|should|decided|surfaced|landed|noticed|saw|caught|filed|wrote|read|named|push|pushed)",
    re.IGNORECASE,
)


@dataclass
class ViolationReport:
    rule_1_violations: list[str] = field(default_factory=list)
    rule_2_violations: list[str] = field(default_factory=list)
    rule_3_violations: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not (self.rule_1_violations or self.rule_2_violations or self.rule_3_violations)

    def summary(self) -> str:
        if self.passed:
            return "voice OK"
        parts = []
        if self.rule_1_violations:
            parts.append(f"rule 1 (first-person): {len(self.rule_1_violations)} violation(s)")
        if self.rule_2_violations:
            parts.append(f"rule 2 (label-colon-value): {len(self.rule_2_violations)} violation(s)")
        if self.rule_3_violations:
            parts.append(f"rule 3 (verb required): {len(self.rule_3_violations)} violation(s)")
        return "; ".join(parts)


def check_voice(text: str) -> ViolationReport:
    """Check text against the three voice rules. Returns ViolationReport."""
    report = ViolationReport()

    # Rule 1: forbidden subject tokens
    for pattern in _FORBIDDEN_SUBJECTS:
        for match in pattern.finditer(text):
            snippet = text[match.start():match.start() + 60]
            report.rule_1_violations.append(snippet)

    # Rule 2: label-colon-value pattern
    for match in _LABEL_COLON_VALUE.finditer(text):
        line = match.group(0)[:80]
        report.rule_2_violations.append(line)

    # Rule 3: bare-noun-list (lines with commas but no verb tokens)
    for line in text.splitlines():
        line_stripped = line.strip()
        if not line_stripped or line_stripped.startswith("#") or line_stripped.startswith("-"):
            continue
        if "," in line_stripped and not _VERB_TOKENS.search(line_stripped):
            if len(line_stripped) < 120:  # only short lines, not paragraphs
                report.rule_3_violations.append(line_stripped[:80])

    return report


def gate_render(panel_text: str, panel_name: str = "") -> tuple[str, ViolationReport]:
    """Apply the voice gate to panel text.

    Returns (rendered_text, report). If report.passed, rendered_text == panel_text.
    If not, rendered_text is a fallback marker; caller can log and decide.
    """
    report = check_voice(panel_text)
    if report.passed:
        return panel_text, report
    fallback = f"[VOICE-RULE-VIOLATION in panel {panel_name or '(unnamed)'}: {report.summary()}]"
    return fallback, report