"""Council Engine — analyze problems through expert thinking lenses.

The engine doesn't simulate experts. It applies their methodologies
to your problem and surfaces what each framework reveals. You think
through them; they don't think for you.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from divineos.core.council.framework import (
    ExpertWisdom,
    LensAnalysis,
    validate_expert,
)

logger = logging.getLogger(__name__)


@dataclass
class CouncilResult:
    """Result of running a problem through multiple expert lenses."""

    problem: str
    analyses: list[LensAnalysis]
    synthesis: str  # cross-lens summary

    def expert_names(self) -> list[str]:
        return [a.expert_name for a in self.analyses]

    def concerns_across_lenses(self) -> dict[str, list[str]]:
        """Concerns grouped by expert."""
        return {a.expert_name: a.concerns for a in self.analyses if a.concerns}

    def shared_concerns(self) -> list[str]:
        """Concerns flagged by 2+ experts — likely important."""
        from collections import Counter

        all_concerns: list[str] = []
        for a in self.analyses:
            all_concerns.extend(a.concerns)
        counts = Counter(all_concerns)
        return [c for c, n in counts.items() if n >= 2]


class CouncilEngine:
    """Load expert wisdom profiles and analyze problems through their lenses.

    Usage:
        engine = CouncilEngine()
        engine.register(feynman_wisdom)
        engine.register(holmes_wisdom)

        # Single lens
        analysis = engine.analyze("problem", "Feynman")

        # Full council
        result = engine.convene("problem")
    """

    def __init__(self) -> None:
        self._experts: dict[str, ExpertWisdom] = {}

    @property
    def experts(self) -> dict[str, ExpertWisdom]:
        return dict(self._experts)

    def register(self, wisdom: ExpertWisdom) -> list[str]:
        """Register an expert. Returns validation issues (empty = ok)."""
        issues = validate_expert(wisdom)
        if issues:
            logger.warning(
                "Expert '%s' has validation issues: %s",
                wisdom.expert_name,
                issues,
            )
            return issues
        self._experts[wisdom.expert_name] = wisdom
        logger.info("Registered expert: %s (%s)", wisdom.expert_name, wisdom.domain)
        return []

    def list_experts(self) -> list[str]:
        """Names of all registered experts."""
        return list(self._experts.keys())

    def get_expert(self, name: str) -> ExpertWisdom | None:
        return self._experts.get(name)

    # ------------------------------------------------------------------
    # Single-lens analysis
    # ------------------------------------------------------------------

    def analyze(self, problem: str, expert_name: str) -> LensAnalysis | None:
        """Analyze a problem through one expert's lens.

        Returns None if the expert isn't registered.
        """
        wisdom = self._experts.get(expert_name)
        if wisdom is None:
            logger.warning("Unknown expert: %s", expert_name)
            return None
        return self._apply_lens(wisdom, problem)

    # ------------------------------------------------------------------
    # Full council convening
    # ------------------------------------------------------------------

    def convene(
        self,
        problem: str,
        expert_names: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> CouncilResult:
        """Run a problem through multiple expert lenses.

        Args:
            problem: The problem statement.
            expert_names: Specific experts to consult (default: all).
            tags: Filter experts by tag instead of name.
        """
        selected = self._select_experts(expert_names, tags)
        analyses = [self._apply_lens(w, problem) for w in selected]
        synthesis = self._synthesize(problem, analyses)
        return CouncilResult(
            problem=problem,
            analyses=analyses,
            synthesis=synthesis,
        )

    # ------------------------------------------------------------------
    # Internal: apply one lens
    # ------------------------------------------------------------------

    def _apply_lens(self, wisdom: ExpertWisdom, problem: str) -> LensAnalysis:
        """Apply an expert's full methodology to a problem."""
        problem_lower = problem.lower()

        # 1. Select best methodology
        methodology = self._select_methodology(wisdom, problem_lower)

        # 2. Find relevant insights
        relevant_insights = self._find_relevant_insights(wisdom, problem_lower)

        # 3. Scan for concerns
        concerns, severity_map = self._scan_concerns(wisdom, problem_lower)

        # 4. Integration findings
        integration_findings = self._apply_integration(wisdom, problem_lower)

        # 5. Decision framework
        df = wisdom.decision_framework

        # 6. Build synthesis text
        synthesis = self._build_synthesis(
            wisdom.expert_name,
            methodology.name,
            methodology.core_principle,
            relevant_insights,
            concerns,
            integration_findings,
            df.what_they_optimize_for,
        )

        return LensAnalysis(
            expert_name=wisdom.expert_name,
            problem=problem,
            methodology_applied=methodology.name,
            methodology_steps=list(methodology.steps),
            core_principle=methodology.core_principle,
            relevant_insights=relevant_insights,
            concerns=concerns,
            severity_map=severity_map,
            integration_findings=integration_findings,
            optimization_target=df.what_they_optimize_for,
            non_negotiables=list(df.non_negotiables),
            uncertainty_handling=df.how_they_handle_uncertainty,
            characteristic_questions=list(wisdom.characteristic_questions),
            synthesis=synthesis,
        )

    def _select_methodology(self, wisdom: ExpertWisdom, problem_lower: str):
        """Pick the most relevant methodology for this problem."""
        for m in wisdom.core_methodologies:
            for trigger in m.when_to_apply:
                if any(word in problem_lower for word in trigger.lower().split() if len(word) > 3):
                    return m
        # Default to first methodology
        return wisdom.core_methodologies[0]

    def _find_relevant_insights(
        self, wisdom: ExpertWisdom, problem_lower: str
    ) -> list[str]:
        """Find insights relevant to this problem."""
        relevant: list[str] = []
        for insight in wisdom.key_insights:
            title_words = {w.lower() for w in insight.title.split() if len(w) > 3}
            if title_words & set(problem_lower.split()):
                relevant.append(f"{insight.title}: {insight.why_matters}")

        # Always include at least one insight
        if not relevant and wisdom.key_insights:
            first = wisdom.key_insights[0]
            relevant.append(f"{first.title}: {first.why_matters}")
        return relevant

    def _scan_concerns(
        self, wisdom: ExpertWisdom, problem_lower: str
    ) -> tuple[list[str], dict[str, str]]:
        """Identify concerns this expert would flag."""
        concerns: list[str] = []
        severity_map: dict[str, str] = {}
        for trigger in wisdom.concern_triggers:
            trigger_words = {w.lower() for w in trigger.name.split() if len(w) > 3}
            desc_words = {w.lower() for w in trigger.description.split() if len(w) > 3}
            match_words = trigger_words | desc_words
            if match_words & set(problem_lower.split()):
                label = f"{trigger.name}: {trigger.why_its_concerning}"
                concerns.append(label)
                severity_map[label] = trigger.severity
        return concerns, severity_map

    def _apply_integration(
        self, wisdom: ExpertWisdom, problem_lower: str
    ) -> list[str]:
        """Apply integration patterns."""
        findings: list[str] = []
        for pattern in wisdom.integration_patterns:
            # Check if any dimension words appear in the problem
            dim_words = set()
            for d in pattern.dimensions:
                dim_words |= {w.lower() for w in d.split() if len(w) > 3}
            if dim_words & set(problem_lower.split()):
                findings.append(f"{pattern.name}: {pattern.what_emerges}")
        return findings

    def _build_synthesis(
        self,
        expert_name: str,
        methodology_name: str,
        core_principle: str,
        insights: list[str],
        concerns: list[str],
        integration_findings: list[str],
        optimization_target: str,
    ) -> str:
        """Build a synthesis text from the analysis components."""
        parts: list[str] = []
        parts.append(
            f"Through {expert_name}'s lens ({methodology_name}):"
        )
        parts.append(f"Core principle: {core_principle}")

        if insights:
            parts.append(f"Key insight: {insights[0]}")

        if concerns:
            parts.append(f"Concerns ({len(concerns)}):")
            for c in concerns[:3]:
                parts.append(f"  - {c}")

        if integration_findings:
            parts.append("Integration:")
            for f in integration_findings[:2]:
                parts.append(f"  - {f}")

        parts.append(f"Optimizing for: {optimization_target}")
        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Expert selection
    # ------------------------------------------------------------------

    def _select_experts(
        self,
        names: list[str] | None,
        tags: list[str] | None,
    ) -> list[ExpertWisdom]:
        """Select which experts to consult."""
        if names:
            return [
                self._experts[n]
                for n in names
                if n in self._experts
            ]
        if tags:
            tag_set = set(tags)
            return [
                w for w in self._experts.values()
                if tag_set & set(w.tags)
            ]
        return list(self._experts.values())

    # ------------------------------------------------------------------
    # Synthesis across lenses
    # ------------------------------------------------------------------

    def _synthesize(self, problem: str, analyses: list[LensAnalysis]) -> str:
        """Cross-lens synthesis — what emerges when multiple frameworks agree or diverge."""
        if not analyses:
            return "No expert lenses applied."

        if len(analyses) == 1:
            return analyses[0].synthesis

        parts: list[str] = [f"Council analysis of: {problem}", ""]

        # Each expert's core take
        for a in analyses:
            parts.append(f"[{a.expert_name}] {a.methodology_applied}: {a.core_principle}")

        # Shared concerns
        all_concerns: list[str] = []
        for a in analyses:
            all_concerns.extend(a.concerns)
        if all_concerns:
            parts.append("")
            parts.append(f"Total concerns across lenses: {len(all_concerns)}")

        # Convergent non-negotiables
        all_nn: list[str] = []
        for a in analyses:
            all_nn.extend(a.non_negotiables)
        if all_nn:
            from collections import Counter

            nn_counts = Counter(all_nn)
            shared = [nn for nn, c in nn_counts.items() if c >= 2]
            if shared:
                parts.append("")
                parts.append("Shared non-negotiables:")
                for nn in shared:
                    parts.append(f"  - {nn}")

        return "\n".join(parts)


# ------------------------------------------------------------------
# Factory
# ------------------------------------------------------------------

_engine: CouncilEngine | None = None


def get_council_engine() -> CouncilEngine:
    """Get or create the singleton council engine."""
    global _engine  # noqa: PLW0603
    if _engine is None:
        _engine = CouncilEngine()
    return _engine
