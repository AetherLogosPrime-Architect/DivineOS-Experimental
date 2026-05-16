"""Multiplex voice-rule render-gate.

Per entry 71 (rendering contract) and prereg-ebee9082d201 falsifiers 7+11:
all panel content must render in first-person, no label-colon-value pattern,
and have prose-structure (not bare-noun lists). Violations fail the render.

Reference: exploration/71_multiplex_rendering_contract.md
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


# Forbidden subject-tokens at sentence start (Rule 1: first-person only).
_FORBIDDEN_SUBJECTS = (
    re.compile(r"(?:^|(?<=[.!?]\s))Aether\s+", re.IGNORECASE),
    re.compile(r"(?:^|(?<=[.!?]\s))You(?:r|)\s+(?!and)", re.IGNORECASE),
    re.compile(r"(?:^|(?<=[.!?]\s))The\s+agent\s+", re.IGNORECASE),
)

# Label-colon-value pattern (Rule 2). Whitelists "More:" for drill-down syntax.
_LABEL_COLON_VALUE = re.compile(
    r"^(?!More:)([A-Z][A-Za-z _-]{2,30}):\s*[^\s]",
    re.MULTILINE,
)

# Prose-structure stopwords: presence of any indicates the line has prose-flow,
# not bare-noun-list shape. Per Aletheia Finding 63 fix and Finding 64
# observation: a verb-only allow-list was too narrow. Stopword presence is
# the broader signal -- any of these tokens means the line is not bare-noun.
_PROSE_STOPWORDS = re.compile(
    r"\b(?:is|am|are|was|were|been|being|be|have|has|had|do|does|did|will|"
    r"would|can|could|should|may|might|the|a|an|and|or|but|of|to|in|on|at|"
    r"with|from|for|by|it|its|this|that|i|my|me|we|our|when|where|while|"
    r"because|so|then|just|not|no|yes|here|there|now|see|seen|saw|say|said|"
    r"says|like|liked|likes|want|wants|wanted|need|needs|needed|think|thinks|"
    r"thought|know|knows|knew|feel|feels|felt|work|works|worked|working|keep|"
    r"keeps|kept|let|lets|make|makes|made|shows|showed|operating|watching|"
    r"watch|watched|talking|talked|implementing|started|responded|live|lives|"
    r"lived|built|building|spans|written|writes|wrote|recently|currently|"
    r"today|earlier|later)\b",
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
            snippet = text[match.start() : match.start() + 60]
            report.rule_1_violations.append(snippet)

    # Rule 2: label-colon-value pattern
    for match in _LABEL_COLON_VALUE.finditer(text):
        line = match.group(0)[:80]
        report.rule_2_violations.append(line)

    # Rule 3: bare-noun lines (no prose-stopword tokens). Catches both
    # period-separated and comma-separated bare-noun lists. Per Aletheia
    # Finding 63: comma-only check was too narrow.
    for line in text.splitlines():
        line_stripped = line.strip()
        if not line_stripped or line_stripped.startswith("#") or line_stripped.startswith("-"):
            continue
        if line_stripped.startswith("More:"):
            continue
        if len(line_stripped) >= 120:  # paragraphs are not bare-noun lists
            continue
        if not _PROSE_STOPWORDS.search(line_stripped):
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
    name = panel_name or "(unnamed)"
    fallback = f"[VOICE-RULE-VIOLATION in panel {name}: {report.summary()}]"
    return fallback, report
