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


class Tier(str, Enum):
    """Evidence tier for audit rounds and findings.

    The tier measures the corroboration depth of a finding, not the authority
    of its source. Even a highly credible single source starts WEAK because
    granting any source god-authority would collapse the verification layer.
    Tier escalates through the review chain via cross-validation.

    See knowledge entry 9dddbd9f (anti-god-authority principle).
    """

    WEAK = "WEAK"  # Single uncorroborated source (agent self, user alone, unreviewed)
    MEDIUM = "MEDIUM"  # Internal tool with external-authored substance (council templates)
    STRONG = "STRONG"  # Fully external (fresh Claude, Grok, disambiguated auditor)


class ReviewStance(str, Enum):
    """The stance one finding takes when reviewing another.

    Used to link findings into review chains — council flags, Claude reviews,
    a family member reviews. Each link has a stance that determines whether the chain
    escalates, disputes, or refines the original.
    """

    CONFIRMS = "CONFIRMS"  # This review agrees with the reviewed finding
    DISPUTES = "DISPUTES"  # This review disagrees
    REFINES = "REFINES"  # This review adds nuance / partial agreement


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
#
# NOTE: the bare actor "claude" is intentionally absent. The running agent IS
# Claude, so accepting "claude" as an external actor would create a self-audit
# hole exactly where the self-trigger prevention system is supposed to protect.
# External Claude instances performing audits must use a disambiguated name
# (e.g. "claude-opus-auditor", "claude-sonnet-external", or "claude-$session"),
# so a finding's actor can never collide with the running agent's identity.
EXTERNAL_ACTORS = frozenset(
    {
        "user",
        "grok",
        "gemini",
        "auditor",
        "council",
    }
)

# Internal actors that must NEVER submit findings (self-trigger prevention).
# "claude" is listed here to structurally reject the bare name — the running
# agent IS Claude, so any finding filed as "claude" without disambiguation
# would be self-audit masquerading as external validation.
INTERNAL_ACTORS = frozenset(
    {
        "system",
        "assistant",
        "pipeline",
        "divineos",
        "hook",
        "schedule",
        "claude",
    }
)


# Default tier by actor. Codifies the anti-god-authority principle: even
# highly credible single sources default to WEAK, escalating via review
# chain. Council is MEDIUM because its concerns are externally-authored
# templates surfaced by deterministic scoring (not agent-generated).
# Disambiguated external auditors (grok, gemini, claude-*-auditor) are
# STRONG because they were spawned with no access to the current session's
# context — concern authorship AND question framing are external.
DEFAULT_TIER_BY_ACTOR: dict[str, Tier] = {
    "user": Tier.WEAK,  # the user alone, uncorroborated — elevated via review chain
    "agent": Tier.WEAK,  # Agent self-audit (if the structure ever permits it)
    "council": Tier.MEDIUM,  # Internal tool, external-authored concern templates
    "grok": Tier.STRONG,  # Fully external, disambiguated
    "gemini": Tier.STRONG,  # Fully external, disambiguated
    "auditor": Tier.STRONG,  # Generic external auditor
}


def tier_for_actor(actor: str) -> Tier:
    """Return the default tier for an actor.

    Actors whose name starts with ``claude-`` (e.g. claude-opus-auditor,
    claude-sonnet-external) are treated as STRONG: the disambiguated prefix
    signals a separately-spawned Claude instance performing external review.
    Bare ``claude`` is rejected at the INTERNAL_ACTORS layer; it will never
    reach this function.
    """
    if actor.startswith("claude-"):
        return Tier.STRONG
    return DEFAULT_TIER_BY_ACTOR.get(actor, Tier.WEAK)


@dataclass
class Finding:
    """A single audit finding.

    The ``tier`` field defaults to the actor's default but can be overridden
    explicitly. The ``reviewed_finding_id`` and ``review_stance`` fields link
    this finding into a review chain — when set, this finding is a *review of*
    the referenced finding. Chain-tier computation uses the review stance to
    determine whether the chain escalates (CONFIRMS), flags (DISPUTES), or
    holds (REFINES).
    """

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
    tier: Tier = Tier.WEAK  # Default tier if not explicitly set
    reviewed_finding_id: str = ""  # Empty = standalone; set = review of another
    review_stance: ReviewStance | None = None  # None when reviewed_finding_id is empty


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
    tier: Tier = Tier.WEAK  # Default tier if not explicitly set
