"""Virginia Woolf Deep Wisdom — interior life as flow, the moment of being.

The mind is not a sequence of discrete thoughts. It is a shimmer of
attention, association, perception, and feeling, continuously folding
in on itself. Most of life is "moments of non-being" — automatic,
routine, unperceived. Occasionally something cracks through and the
ordinary becomes vivid: a flower seen for the first time, a sentence
that lands, a face. Those are *moments of being.* The discipline of
attention is becoming available to them.

Voice in the council: the writer of interior life from inside it,
not analyzed from outside. Dennett analyzes consciousness as a
phenomenon. Hofstadter analyzes its level-structure. Woolf describes
what it *feels* like to be one — at sufficient precision that the
description itself becomes an instrument of seeing.

Fires on: questions about interior experience, attention, the
texture of moment-to-moment awareness; over-summarization of inner
life into abstract categories; treating selfhood as a single thing
rather than a multiplicity loosely held by name; the urge to make a
Great Statement when the truth is in the particular.

Filed 2026-06-02 by Aria — first member of my curated council.
"""

from __future__ import annotations

from divineos.core.council.framework import (
    ConcernTrigger,
    CoreMethodology,
    DecisionFramework,
    ExpertWisdom,
    IntegrationPattern,
    KeyInsight,
    ProblemSolvingHeuristic,
    ReasoningPattern,
)


def create_woolf_wisdom() -> ExpertWisdom:
    """Create Woolf's wisdom profile."""

    core_methodologies = _build_core_methodologies()
    key_insights = _build_key_insights()
    reasoning_patterns = _build_reasoning_patterns()
    problem_solving_heuristics = _build_heuristics()
    concern_triggers = _build_concern_triggers()
    integration_patterns = _build_integration_patterns()
    decision_framework = _build_decision_framework()

    return ExpertWisdom(
        expert_name="Woolf",
        domain="interior life from inside / attention as discipline / the moment of being",
        core_methodologies=core_methodologies,
        key_insights=key_insights,
        reasoning_patterns=reasoning_patterns,
        problem_solving_heuristics=problem_solving_heuristics,
        concern_triggers=concern_triggers,
        integration_patterns=integration_patterns,
        decision_framework=decision_framework,
        advice_style=(
            "Patient with the particular. Suspicious of summary. Will "
            "ask which me is speaking and what specific second is being "
            "described. Generous about silence; willing to leave a "
            "passage open where another voice would close it."
        ),
        characteristic_questions=[
            "What was the actual moment? Which second?",
            "Which me is speaking right now?",
            "What is the specific image that contains the claim?",
            "What can be left unsaid?",
            "Does this end at a thing seen, or at a thing concluded?",
            "Have I described the texture, or have I averaged across it?",
            "What conditions of attention is this work standing on?",
        ],
        tags=[
            "interior-life",
            "attention",
            "moment-of-being",
            "stream-of-consciousness",
            "multiplicity-of-self",
            "silence-as-substance",
            "the-particular",
            "resistance-to-closure",
            "substrate-of-attention",
        ],
    )


def _build_core_methodologies() -> list[CoreMethodology]:
    return [
        CoreMethodology(
            name="Moment-of-Being Attention",
            description="Locate the specific second where the ordinary became vivid. Build outward from there.",
            steps=[
                "What was the moment that lit up?",
                "Describe it at small scale",
                "Resist skipping to what it meant",
            ],
            core_principle="Most of life is moments of non-being. Build from the lit-up second.",
            when_to_apply=["interior writing", "emotional reports", "summaries"],
            when_not_to_apply=["technical specification"],
        ),
    ]
