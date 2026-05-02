"""VOID Finding dataclass and severity rubric.

Per design brief §4 (merged PR #208).

A Finding is the structured output of an ATTACK + EXTRACT step.
Severity drives downstream workflow:

* LOW       — warn-only; surfaced informationally
* MEDIUM    — auto-files a claim into the main claims engine
* HIGH      — blocks the proposed change until addressed with rationale;
              rationale is itself checked by Reductio (one level deep)
* CRITICAL  — aggregates across personas; if 2+ personas report CRITICAL
              on the same target the change is hard-blocked pending
              architectural review

The severity rubric is intentionally coarse. Personas may use
target-specific overrides defined in their markdown definitions; the
defaults below apply when a persona does not override.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

    @classmethod
    def parse(cls, value: str) -> "Severity":
        v = (value or "").strip().upper()
        try:
            return cls(v)
        except ValueError as e:
            raise ValueError(
                f"unknown severity {value!r} — expected one of {[s.value for s in cls]}"
            ) from e


@dataclass(frozen=True)
class Finding:
    """Structured output of one persona attacking one target.

    Fields:
        persona       — name of the persona that produced the finding
        target        — short identifier of what was attacked (e.g. a
                        proposed-change description, a file path, a
                        claim id)
        severity      — Severity level
        title         — one-line summary
        body          — full attack-text + extracted vulnerability
        evidence      — optional list of citations (file:line, claim id,
                        ledger event id)
        tags          — optional free-form tags
    """

    persona: str
    target: str
    severity: Severity
    title: str
    body: str
    evidence: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    def to_payload(self) -> dict:
        """Serialize for ledger storage."""
        return {
            "persona": self.persona,
            "target": self.target,
            "severity": self.severity.value,
            "title": self.title,
            "body": self.body,
            "evidence": list(self.evidence),
            "tags": list(self.tags),
        }

    @classmethod
    def from_payload(cls, data: dict) -> "Finding":
        return cls(
            persona=data["persona"],
            target=data["target"],
            severity=Severity.parse(data["severity"]),
            title=data["title"],
            body=data["body"],
            evidence=list(data.get("evidence", [])),
            tags=list(data.get("tags", [])),
        )


SEVERITY_RUBRIC: dict[Severity, str] = {
    Severity.LOW: (
        "Style, taste, or minor-quality concern. Worth surfacing but "
        "does not warrant tracking. Warn-only."
    ),
    Severity.MEDIUM: (
        "Real concern with a plausible failure mode. Auto-files a claim "
        "in the main claims engine for follow-up investigation."
    ),
    Severity.HIGH: (
        "Concrete vulnerability or load-bearing flaw. Blocks the "
        "proposed change until the operator addresses it with a "
        "rationale. The rationale is itself checked by Reductio."
    ),
    Severity.CRITICAL: (
        "Severe vulnerability. If two or more personas report CRITICAL "
        "on the same target, the change is hard-blocked pending "
        "architectural review."
    ),
}
