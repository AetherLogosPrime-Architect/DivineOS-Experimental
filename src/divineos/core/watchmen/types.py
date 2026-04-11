"""Watchmen type definitions — enums, dataclasses, constants."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Severity(str, Enum):
    """Finding severity levels."""

    CRITICAL = "CRITICAL"  # System integrity at risk
    HIGH = "HIGH"  # Significant behavioral issue
    MEDIUM = "MEDIUM"  # Notable concern, not urgent
    LOW = "LOW"  # Minor observation
    INFO = "INFO"  # Informational, no action needed


class FindingCategory(str, Enum):
    """What domain a finding belongs to."""

    KNOWLEDGE = "KNOWLEDGE"  # Knowledge store issues (dedup, maturity, quality)
    BEHAVIOR = "BEHAVIOR"  # Behavioral patterns (drift, stagnation, bias)
    INTEGRITY = "INTEGRITY"  # Data integrity (hashes, ledger, corruption)
    ARCHITECTURE = "ARCHITECTURE"  # Code/design issues (god files, dead abstractions)
    PERFORMANCE = "PERFORMANCE"  # Speed, size, resource concerns
    LEARNING = "LEARNING"  # Lesson tracking, correction patterns
    IDENTITY = "IDENTITY"  # Self-model, continuity, voice concerns


class FindingStatus(str, Enum):
    """Lifecycle of a finding."""

    OPEN = "OPEN"  # Submitted, not yet acted on
    ROUTED = "ROUTED"  # Routed to knowledge/claims/lessons
    IN_PROGRESS = "IN_PROGRESS"  # Being worked on
    RESOLVED = "RESOLVED"  # Fixed and verified
    WONT_FIX = "WONT_FIX"  # Acknowledged but intentionally not fixing
    DUPLICATE = "DUPLICATE"  # Already covered by another finding


# Valid external actors — these are the only actors allowed to submit findings.
# Internal actors (system, assistant, pipeline) are structurally rejected.
EXTERNAL_ACTORS = frozenset(
    {
        "user",
        "grok",
        "claude",
        "gemini",
        "auditor",
        "council",
    }
)

# Internal actors that must NEVER submit findings (self-trigger prevention)
INTERNAL_ACTORS = frozenset(
    {
        "system",
        "assistant",
        "pipeline",
        "divineos",
        "hook",
        "schedule",
    }
)


@dataclass
class Finding:
    """A single audit finding."""

    finding_id: str
    round_id: str
    created_at: float
    actor: str
    severity: Severity
    category: FindingCategory
    title: str
    description: str
    recommendation: str = ""
    status: FindingStatus = FindingStatus.OPEN
    resolution_notes: str = ""
    routed_to: str = ""  # knowledge_id, claim_id, or lesson category
    tags: list[str] = field(default_factory=list)


@dataclass
class AuditRound:
    """A batch of findings submitted together."""

    round_id: str
    created_at: float
    actor: str
    focus: str  # What was audited (e.g., "Dice coefficient impact")
    expert_count: int = 0
    finding_count: int = 0
    notes: str = ""
