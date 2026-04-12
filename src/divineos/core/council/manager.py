"""Dynamic Council Manager — select the right experts for the problem.

Instead of running all 28 experts on every problem (expensive, unfocused),
classify the problem and select 5-8 experts whose methodologies are most
relevant. This was identified as the #1 architectural improvement from
the SWE-bench benchmark: reducing token cost while focusing reasoning.

The classification is signal-based, not LLM-based — no extra API calls.
It uses the rich metadata already on each ExpertWisdom: tags, domain,
when_to_apply triggers, concern triggers, and characteristic questions.

Design principle: structure, not control. The manager RECOMMENDS experts;
the caller can override. It never prevents an expert from being consulted.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from divineos.core.council.engine import CouncilEngine, CouncilResult
from divineos.core.council.framework import ExpertWisdom


# ------------------------------------------------------------------
# Problem categories — derived from SWE-bench failure analysis
# ------------------------------------------------------------------


@dataclass
class ProblemCategory:
    """A category of problem with associated signal words and expert affinities."""

    name: str
    description: str
    signals: list[str]  # words/phrases that indicate this category
    core_experts: list[str]  # always include these (by expert name)
    affinity_tags: list[str]  # boost experts with these tags
    weight: float = 1.0  # how strongly this category contributes


# The categories are derived from analyzing 170 SWE-bench tasks.
# Each maps to the expert lenses that proved most valuable.
PROBLEM_CATEGORIES = [
    ProblemCategory(
        name="causal_chain",
        description="Bug where the root cause is distant from the symptom",
        signals=[
            "wrong result",
            "incorrect output",
            "unexpected behavior",
            "regression",
            "used to work",
            "broke after",
            "side effect",
            "downstream",
            "cascading",
            "propagat",
            "chain",
        ],
        core_experts=["Pearl", "Feynman"],
        affinity_tags=["causality", "first-principles", "systems-thinking"],
    ),
    ProblemCategory(
        name="logic_error",
        description="Incorrect condition, wrong operator, flipped logic",
        signals=[
            "wrong condition",
            "logic error",
            "should be",
            "instead of",
            "off-by-one",
            "boundary",
            "edge case",
            "corner case",
            "negative",
            "zero",
            "empty",
            "overflow",
            "underflow",
            "inclusive",
            "exclusive",
            "less than",
            "greater than",
        ],
        core_experts=["Knuth", "Dijkstra"],
        affinity_tags=["correctness", "boundaries", "formal-methods", "edge-cases"],
    ),
    ProblemCategory(
        name="type_error",
        description="Wrong type, missing conversion, type mismatch",
        signals=[
            "typeerror",
            "attributeerror",
            "type error",
            "cast",
            "conversion",
            "isinstance",
            "type mismatch",
            "expected str",
            "expected int",
            "none",
            "nonetype",
            "unicode",
            "encoding",
            "bytes",
            "decode",
            "encode",
        ],
        core_experts=["Dijkstra", "Knuth"],
        affinity_tags=["correctness", "specification", "formal-methods"],
    ),
    ProblemCategory(
        name="api_misuse",
        description="Wrong function called, wrong arguments, wrong method",
        signals=[
            "wrong function",
            "wrong method",
            "api",
            "signature",
            "argument",
            "parameter",
            "deprecated",
            "override",
            "inheritance",
            "subclass",
            "super",
            "mro",
            "dispatch",
            "abstract",
            "interface",
            "protocol",
        ],
        core_experts=["Holmes", "Polya"],
        affinity_tags=["investigation", "verification", "deduction"],
    ),
    ProblemCategory(
        name="state_management",
        description="Stale state, missing cleanup, initialization order",
        signals=[
            "state",
            "cleanup",
            "reset",
            "initialize",
            "init",
            "restore",
            "persist",
            "stale",
            "leak",
            "cache",
            "singleton",
            "global",
            "shared",
            "mutable",
            "fixture",
            "setup",
            "teardown",
            "context manager",
        ],
        core_experts=["Meadows", "Beer"],
        affinity_tags=["systems-thinking", "feedback-loops", "cybernetics"],
    ),
    ProblemCategory(
        name="format_spec",
        description="Output format violation, field width, spec noncompliance",
        signals=[
            "format",
            "width",
            "field",
            "column",
            "align",
            "pad",
            "truncat",
            "spec",
            "rfc",
            "standard",
            "fits",
            "csv",
            "json",
            "xml",
            "html",
            "render",
            "display",
            "print",
            "output format",
            "string format",
        ],
        core_experts=["Knuth", "Polya"],
        affinity_tags=["specification", "correctness", "verification"],
    ),
    ProblemCategory(
        name="concurrency",
        description="Race condition, deadlock, thread safety",
        signals=[
            "thread",
            "race",
            "deadlock",
            "lock",
            "mutex",
            "concurrent",
            "parallel",
            "async",
            "await",
            "coroutine",
            "atomic",
            "synchron",
        ],
        core_experts=["Dijkstra", "Schneier"],
        affinity_tags=["formal-methods", "correctness"],
    ),
    ProblemCategory(
        name="security",
        description="Vulnerability, injection, auth bypass",
        signals=[
            "security",
            "vulnerab",
            "inject",
            "xss",
            "csrf",
            "auth",
            "permission",
            "privilege",
            "escap",
            "saniti",
            "trust",
            "untrusted",
            "malicious",
        ],
        core_experts=["Schneier", "Yudkowsky"],
        affinity_tags=["security", "adversarial-thinking", "threat-modeling"],
    ),
    ProblemCategory(
        name="performance",
        description="Slow, memory, scaling issues",
        signals=[
            "slow",
            "performance",
            "memory",
            "scaling",
            "quadratic",
            "exponential",
            "timeout",
            "oom",
            "optimize",
            "efficient",
            "bottleneck",
            "profile",
        ],
        core_experts=["Knuth", "Shannon"],
        affinity_tags=["information-theory", "correctness"],
    ),
    ProblemCategory(
        name="design_flaw",
        description="Architectural issue, wrong abstraction, coupling",
        signals=[
            "refactor",
            "architecture",
            "design",
            "coupling",
            "cohesion",
            "abstraction",
            "pattern",
            "separation",
            "responsibility",
            "interface",
            "module",
            "dependency",
            "circular",
            "god class",
            "god object",
        ],
        core_experts=["Dijkstra", "Beer"],
        affinity_tags=[
            "structured-programming",
            "viable-system-model",
            "systems-thinking",
            "simplicity",
        ],
    ),
    ProblemCategory(
        name="incomplete_fix",
        description="Patch that addresses part of the problem but not all",
        signals=[
            "partial",
            "incomplete",
            "still fails",
            "another case",
            "also broken",
            "missed",
            "forgot",
            "didn't handle",
            "some cases",
            "sometimes",
            "intermittent",
        ],
        core_experts=["Polya", "Popper"],
        affinity_tags=[
            "verification",
            "solution-check",
            "falsification",
            "completeness",
            "adversarial",
        ],
    ),
]


# ------------------------------------------------------------------
# Always-on experts — provide meta-reasoning on every problem
# ------------------------------------------------------------------

# These 2 experts are included in every consultation because they
# provide meta-level value: Kahneman catches cognitive biases in
# the reasoning process itself, Popper ensures we seek disconfirmation.
ALWAYS_ON = ["Kahneman", "Popper"]

# Target council size
MIN_EXPERTS = 5
MAX_EXPERTS = 8


# ------------------------------------------------------------------
# Expert scoring
# ------------------------------------------------------------------


@dataclass
class ExpertScore:
    """Relevance score for one expert on one problem."""

    expert_name: str
    score: float
    reasons: list[str] = field(default_factory=list)

    def __repr__(self) -> str:
        return f"{self.expert_name}: {self.score:.2f} ({', '.join(self.reasons)})"


def classify_problem(problem: str) -> list[tuple[ProblemCategory, float]]:
    """Classify a problem into categories with confidence scores.

    Returns categories sorted by match strength (descending).
    A category's score = (number of signal matches) * category weight.
    """
    problem_lower = problem.lower()
    results: list[tuple[ProblemCategory, float]] = []

    for category in PROBLEM_CATEGORIES:
        match_count = 0
        for signal in category.signals:
            if signal in problem_lower:
                match_count += 1
        if match_count > 0:
            score = match_count * category.weight
            results.append((category, score))

    results.sort(key=lambda x: x[1], reverse=True)
    return results


def score_experts(
    problem: str,
    experts: dict[str, ExpertWisdom],
) -> list[ExpertScore]:
    """Score every registered expert's relevance to this problem.

    Scoring combines:
    1. Category match — is this expert a core expert for the detected categories?
    2. Tag affinity — do the expert's tags overlap with category affinity tags?
    3. When-to-apply match — do the expert's methodology triggers fire?
    4. Domain keyword match — do words in the problem appear in the expert's domain?
    5. Always-on bonus — meta-reasoning experts get a baseline score.
    """
    problem_lower = problem.lower()
    problem_words = set(re.findall(r"\b\w{4,}\b", problem_lower))

    categories = classify_problem(problem)
    scores: dict[str, ExpertScore] = {}

    # Initialize all experts with zero score
    for name in experts:
        scores[name] = ExpertScore(expert_name=name, score=0.0)

    # 1. Always-on bonus
    for name in ALWAYS_ON:
        if name in scores:
            scores[name].score += 3.0
            scores[name].reasons.append("always-on")

    # 2. Category core expert bonus (strongest signal)
    for category, cat_score in categories:
        for name in category.core_experts:
            if name in scores:
                bonus = 5.0 * (cat_score / max(cat_score, 1.0))
                scores[name].score += bonus
                scores[name].reasons.append(f"core:{category.name}")

    # 3. Tag affinity (moderate signal)
    category_tags: set[str] = set()
    for category, _ in categories:
        category_tags.update(category.affinity_tags)

    if category_tags:
        for name, wisdom in experts.items():
            overlap = category_tags & set(wisdom.tags)
            if overlap:
                scores[name].score += len(overlap) * 1.5
                scores[name].reasons.append(f"tags:{','.join(sorted(overlap))}")

    # 4. When-to-apply trigger match (moderate signal)
    for name, wisdom in experts.items():
        for method in wisdom.core_methodologies:
            for trigger in method.when_to_apply:
                trigger_words = set(re.findall(r"\b\w{4,}\b", trigger.lower()))
                overlap = problem_words & trigger_words
                if len(overlap) >= 2:
                    scores[name].score += 2.0
                    scores[name].reasons.append(f"trigger:{method.name}")
                    break  # one match per methodology is enough

    # 5. Domain keyword match (weak signal)
    for name, wisdom in experts.items():
        domain_words = set(re.findall(r"\b\w{4,}\b", wisdom.domain.lower()))
        overlap = problem_words & domain_words
        if overlap:
            scores[name].score += len(overlap) * 0.5
            scores[name].reasons.append("domain")

    result = list(scores.values())
    result.sort(key=lambda x: x.score, reverse=True)
    return result


def select_experts(
    problem: str,
    experts: dict[str, ExpertWisdom],
    min_experts: int = MIN_EXPERTS,
    max_experts: int = MAX_EXPERTS,
) -> list[ExpertScore]:
    """Select the optimal council for this problem.

    Returns min_experts to max_experts ExpertScores, sorted by relevance.
    Always includes ALWAYS_ON experts. Fills remaining slots by score.
    """
    scored = score_experts(problem, experts)

    selected: list[ExpertScore] = []
    selected_names: set[str] = set()

    # 1. Always include always-on experts
    for es in scored:
        if es.expert_name in ALWAYS_ON and es.expert_name in experts:
            selected.append(es)
            selected_names.add(es.expert_name)

    # 2. Fill remaining slots by score
    for es in scored:
        if len(selected) >= max_experts:
            break
        if es.expert_name not in selected_names and es.score > 0:
            selected.append(es)
            selected_names.add(es.expert_name)

    # 3. If we're below minimum, add top-scored remaining experts
    for es in scored:
        if len(selected) >= min_experts:
            break
        if es.expert_name not in selected_names:
            selected.append(es)
            selected_names.add(es.expert_name)

    return selected


# ------------------------------------------------------------------
# Managed convene — the main API
# ------------------------------------------------------------------


@dataclass
class ManagedCouncilResult:
    """Result of a managed council session.

    Extends CouncilResult with selection metadata.
    """

    council_result: CouncilResult
    selected_experts: list[ExpertScore]
    categories_detected: list[tuple[str, float]]
    total_experts_available: int

    @property
    def problem(self) -> str:
        return self.council_result.problem

    @property
    def analyses(self):
        return self.council_result.analyses

    @property
    def synthesis(self) -> str:
        return self.council_result.synthesis

    def selection_summary(self) -> str:
        """Human-readable summary of why these experts were chosen."""
        parts: list[str] = []
        parts.append(
            f"Selected {len(self.selected_experts)} of {self.total_experts_available} experts"
        )

        if self.categories_detected:
            cats = ", ".join(
                f"{name} ({score:.1f})" for name, score in self.categories_detected[:3]
            )
            parts.append(f"Problem categories: {cats}")

        parts.append("Selected council:")
        for es in self.selected_experts:
            reasons = ", ".join(es.reasons) if es.reasons else "baseline"
            parts.append(f"  {es.expert_name} ({es.score:.1f}): {reasons}")

        return "\n".join(parts)


class CouncilManager:
    """Manages dynamic expert selection for the council engine.

    Wraps CouncilEngine with intelligent expert routing.
    The manager classifies the problem, scores experts, selects
    the optimal 5-8, then delegates to the engine for analysis.

    Usage:
        manager = CouncilManager(engine)
        result = manager.convene("the database query returns wrong results")
        print(result.selection_summary())
        print(result.synthesis)
    """

    def __init__(self, engine: CouncilEngine) -> None:
        self._engine = engine

    @property
    def engine(self) -> CouncilEngine:
        return self._engine

    def convene(
        self,
        problem: str,
        min_experts: int = MIN_EXPERTS,
        max_experts: int = MAX_EXPERTS,
        force_experts: list[str] | None = None,
    ) -> ManagedCouncilResult:
        """Convene the right experts for this problem.

        Args:
            problem: The problem to analyze.
            min_experts: Minimum experts to include (default 5).
            max_experts: Maximum experts to include (default 8).
            force_experts: Always include these experts (by name),
                          in addition to the auto-selected ones.
        """
        experts = self._engine.experts

        # Score and select
        selected = select_experts(problem, experts, min_experts, max_experts)
        selected_names = [es.expert_name for es in selected]

        # Add forced experts if not already selected
        if force_experts:
            for name in force_experts:
                if name not in selected_names and name in experts:
                    selected.append(
                        ExpertScore(
                            expert_name=name,
                            score=0.0,
                            reasons=["forced"],
                        )
                    )
                    selected_names.append(name)

        # Classify for metadata
        categories = classify_problem(problem)
        categories_meta = [(cat.name, score) for cat, score in categories]

        # Convene with selected experts only
        council_result = self._engine.convene(
            problem=problem,
            expert_names=selected_names,
        )

        return ManagedCouncilResult(
            council_result=council_result,
            selected_experts=selected,
            categories_detected=categories_meta,
            total_experts_available=len(experts),
        )

    def explain_selection(self, problem: str) -> str:
        """Explain which experts would be selected and why.

        Useful for debugging and understanding the selection logic.
        Does not run analysis — just shows the routing decision.
        """
        experts = self._engine.experts
        categories = classify_problem(problem)
        scored = score_experts(problem, experts)
        selected = select_experts(problem, experts)
        selected_names = {s.expert_name for s in selected}

        parts: list[str] = []
        parts.append(f"Problem: {problem[:100]}...")
        parts.append("")

        if categories:
            parts.append("Detected categories:")
            for cat, score in categories:
                parts.append(f"  {cat.name} ({score:.1f}): {cat.description}")
                parts.append(f"    Core experts: {', '.join(cat.core_experts)}")
        else:
            parts.append("No specific category detected — using general scoring")

        parts.append("")
        parts.append("All expert scores:")
        for es in scored[:15]:  # top 15
            marker = " *" if es.expert_name in selected_names else ""
            reasons = ", ".join(es.reasons) if es.reasons else "—"
            parts.append(f"  {es.score:5.1f}  {es.expert_name:<15}{marker}  ({reasons})")

        parts.append("")
        parts.append(f"Selected ({len(selected)}):")
        for es in selected:
            parts.append(f"  {es.expert_name}: {', '.join(es.reasons)}")

        return "\n".join(parts)
