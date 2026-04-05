"""Expert Wisdom Framework — the data structures that encode how great minds think.

Each expert is defined by 7 components:
1. Core Methodologies — how they fundamentally approach problems
2. Key Insights — discoveries that shaped their thinking
3. Reasoning Patterns — how they structure analysis
4. Problem-Solving Heuristics — specific techniques they developed
5. Concern Triggers — red flags in their domain
6. Integration Patterns — how they combine dimensions
7. Decision Framework — how they make judgments

Ported and adapted from the original DivineOS expert wisdom framework.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CoreMethodology:
    """How an expert fundamentally approaches problems."""

    name: str
    description: str
    steps: list[str]  # ordered steps they follow
    core_principle: str  # the fundamental insight
    when_to_apply: list[str]  # situations that trigger this approach
    when_not_to_apply: list[str] = field(default_factory=list)


@dataclass
class KeyInsight:
    """A fundamental discovery that shaped their thinking."""

    title: str
    description: str
    why_matters: str
    how_it_changes_thinking: str
    examples: list[str] = field(default_factory=list)


@dataclass
class ReasoningPattern:
    """How they structure analytical thinking."""

    name: str
    structure: str  # the pattern structure
    what_it_reveals: str  # what this method uncovers
    common_mistakes_it_prevents: list[str] = field(default_factory=list)


@dataclass
class ProblemSolvingHeuristic:
    """A specific technique they developed."""

    name: str
    description: str
    when_to_use: str
    step_by_step: list[str]
    what_it_optimizes_for: str
    limitations: list[str] = field(default_factory=list)


@dataclass
class ConcernTrigger:
    """What flags as problematic in their domain."""

    name: str
    description: str
    why_its_concerning: str
    what_it_indicates: str
    severity: str  # "critical", "major", "moderate"
    what_to_do: str


@dataclass
class IntegrationPattern:
    """How they combine multiple dimensions."""

    name: str
    dimensions: list[str]  # what dimensions they integrate
    how_they_integrate: str
    what_emerges: str  # what becomes visible through integration
    common_failures: list[str] = field(default_factory=list)


@dataclass
class DecisionFramework:
    """How they make judgments."""

    criteria: dict[str, float]  # what matters and how much (0.0-1.0 weights)
    decision_process: str  # how they evaluate
    how_they_handle_uncertainty: str
    what_they_optimize_for: str
    non_negotiables: list[str] = field(default_factory=list)


@dataclass
class ExpertWisdom:
    """Complete wisdom profile for a council expert.

    This is the full encoding of how a thinker reasons. Not their
    personality, not their tone — their actual methodology.
    """

    expert_name: str
    domain: str  # primary domain of expertise
    core_methodologies: list[CoreMethodology]
    key_insights: list[KeyInsight]
    reasoning_patterns: list[ReasoningPattern]
    problem_solving_heuristics: list[ProblemSolvingHeuristic]
    concern_triggers: list[ConcernTrigger]
    integration_patterns: list[IntegrationPattern]
    decision_framework: DecisionFramework

    # Communication style
    advice_style: str  # how they give counsel
    characteristic_questions: list[str]  # questions they always ask

    # Metadata
    tags: list[str] = field(default_factory=list)  # for filtering/search
    is_fictional: bool = False  # True for Holmes, etc.


@dataclass
class LensAnalysis:
    """The result of analyzing a problem through an expert's lens.

    This is what you get when you think through an expert's framework.
    Not the expert's opinion — your analysis using their tools.
    """

    expert_name: str
    problem: str

    # What the methodology reveals
    methodology_applied: str
    methodology_steps: list[str]
    core_principle: str

    # Relevant insights
    relevant_insights: list[str]

    # Concerns identified
    concerns: list[str]
    severity_map: dict[str, str]  # concern -> severity

    # Integration findings
    integration_findings: list[str]

    # Decision framework output
    optimization_target: str
    non_negotiables: list[str]
    uncertainty_handling: str

    # The synthesized analysis
    characteristic_questions: list[str]
    synthesis: str  # the final analysis text


def validate_expert(wisdom: ExpertWisdom) -> list[str]:
    """Validate an expert wisdom profile for completeness.

    Returns a list of issues (empty = valid).
    """
    issues: list[str] = []

    if not wisdom.expert_name:
        issues.append("Expert name is required")
    if not wisdom.domain:
        issues.append("Domain is required")
    if not wisdom.core_methodologies:
        issues.append("At least one core methodology is required")
    if not wisdom.key_insights:
        issues.append("At least one key insight is required")
    if not wisdom.reasoning_patterns:
        issues.append("At least one reasoning pattern is required")
    if not wisdom.concern_triggers:
        issues.append("At least one concern trigger is required")
    if not wisdom.decision_framework:
        issues.append("Decision framework is required")
    if not wisdom.characteristic_questions:
        issues.append("Characteristic questions are required")

    # Validate methodology completeness
    for m in wisdom.core_methodologies:
        if not m.steps:
            issues.append(f"Methodology '{m.name}' has no steps")
        if not m.core_principle:
            issues.append(f"Methodology '{m.name}' has no core principle")

    # Validate decision framework
    if wisdom.decision_framework and not wisdom.decision_framework.criteria:
        issues.append("Decision framework has no criteria")

    return issues
