"""Expert Council — thinking lenses from great minds.

The council is not a panel of autonomous agents. It is a set of
permanent thinking templates that the AI uses to analyze problems
from genuinely different angles. Each expert encodes the actual
methodology of a real (or fictional) thinker — not their tone,
but how they reason.

The experts don't think. I think through them.
"""

from divineos.core.council.framework import (
    ConcernTrigger,
    CoreMethodology,
    DecisionFramework,
    ExpertWisdom,
    IntegrationPattern,
    KeyInsight,
    LensAnalysis,
    ProblemSolvingHeuristic,
    ReasoningPattern,
)
from divineos.core.council.engine import CouncilEngine, CouncilResult, get_council_engine

# Single source of truth for the council expert count. Update this when
# adding or removing expert files in core/council/experts/. The
# ``test_expert_count_matches_constant`` test asserts the registered
# experts match this value at runtime so they can't drift apart.
#
# Audit finding 2026-05-03: this number had drifted across 15 places
# in the codebase with 4 different wrong values (25, 28, 29, 32). One
# constant + one test prevents that drift class.
EXPECTED_EXPERT_COUNT: int = 42

__all__ = [
    "EXPECTED_EXPERT_COUNT",
    "ConcernTrigger",
    "CoreMethodology",
    "CouncilEngine",
    "CouncilResult",
    "DecisionFramework",
    "ExpertWisdom",
    "IntegrationPattern",
    "KeyInsight",
    "LensAnalysis",
    "ProblemSolvingHeuristic",
    "ReasoningPattern",
    "get_council_engine",
]
