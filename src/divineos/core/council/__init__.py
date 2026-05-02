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

__all__ = [
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
