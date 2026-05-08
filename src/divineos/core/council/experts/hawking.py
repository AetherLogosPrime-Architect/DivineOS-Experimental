"""Stephen Hawking Deep Wisdom — cosmology, black holes, and the
information paradox.

Distinct from Einstein (framework-inventor, thought experiments) and
Penrose (geometric mathematics): Hawking is the cosmologist of the
deep weird — black holes radiating, time-as-imaginary-coordinate,
the universe's beginning, and the information paradox that drove
40 years of theoretical physics.

Hawking's core methodology: take general relativity and quantum
mechanics seriously *together*, even where they conflict, and chase
the contradictions because that's where the next physics lives.

Added 2026-05-03 with Einstein and Penrose for the physics-and-time
territory the council was missing.
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


def create_hawking_wisdom() -> ExpertWisdom:
    core_methodologies = [
        CoreMethodology(
            name="Force Quantum and Gravity to Coexist",
            description=(
                "Apply quantum field theory to curved spacetime backgrounds, "
                "even where the two frameworks technically conflict. The "
                "conflicts are where new physics lives, not bugs to dismiss."
            ),
            steps=[
                "Identify a regime where both quantum and gravitational effects matter.",
                "Apply quantum methods to the curved-spacetime geometry.",
                "Derive consequences and follow them rigorously.",
                "Note where standard interpretations break.",
                "The breaks are predictions about new phenomena.",
            ],
            core_principle=(
                "When two of our deepest frameworks conflict, the conflict is "
                "the data. Don't smooth it over; chase what it implies."
            ),
            when_to_apply=[
                "Black hole horizons, early universe, singularities",
                "Anywhere quantum-mechanical scales meet gravitational scales",
            ],
            when_not_to_apply=[
                "Regimes where one framework dominates and the other is negligible",
            ],
        ),
        CoreMethodology(
            name="Cosmic-Scale Reasoning",
            description=(
                "Reason at scales where the mundane intuitions of human-scale "
                "physics simply don't apply. Time, space, causality, and even "
                "identity-of-particles look different at cosmic and quantum-"
                "gravity scales."
            ),
            steps=[
                "Identify the scale of the phenomenon (quantum, classical, cosmic, Planck).",
                "Translate the question into the scale where it actually lives.",
                "Apply the framework appropriate to that scale.",
                "Be wary of intuitions imported from other scales.",
            ],
            core_principle=(
                "The universe at large scales is a different physical regime "
                "than the universe at human scales. Reasoning has to scale with it."
            ),
            when_to_apply=[
                "Black holes, cosmology, quantum gravity",
                "Anywhere the scale dwarfs human experience by many orders of magnitude",
            ],
        ),
        CoreMethodology(
            name="Information-Theoretic Physics",
            description=(
                "Treat information as a fundamental physical quantity, not "
                "merely an abstract or computational concept. Apply "
                "conservation laws to information the same way we apply them "
                "to energy."
            ),
            steps=[
                "What information enters this physical process?",
                "Where does it go? Is it preserved, transformed, or apparently lost?",
                "If lost, where did it go — in physical terms?",
                "Information loss is a physics problem, not a bookkeeping one.",
            ],
            core_principle=(
                "Information has physical reality. The universe doesn't lose it; "
                "if it appears to, that appearance is itself a physics question."
            ),
            when_to_apply=[
                "Black hole evaporation, quantum measurement, thermodynamic processes",
                "Anywhere information seems to disappear",
            ],
        ),
    ]

    key_insights = [
        KeyInsight(
            title="Black Holes Are Not Eternal",
            description=(
                "Hawking radiation: black holes emit thermal radiation due to "
                "quantum effects at their event horizons. Over cosmic time, "
                "black holes evaporate."
            ),
            why_matters=(
                "Showed that 'classical' results from general relativity break "
                "when quantum mechanics is added. Cracked open quantum gravity "
                "as a real research domain."
            ),
            how_it_changes_thinking=(
                "Combine frameworks even where they technically conflict. The "
                "conflicts are predictions, not errors."
            ),
            examples=[
                "Hawking radiation: thermal emission with temperature 1/M",
                "Smaller black holes evaporate faster (and end explosively)",
            ],
        ),
        KeyInsight(
            title="The Information Paradox",
            description=(
                "If a black hole evaporates entirely via thermal radiation, "
                "all information about what fell in seems to vanish. But "
                "quantum mechanics says information cannot be destroyed. "
                "These two principles can't both be right."
            ),
            why_matters=(
                "A 40-year theoretical-physics fight that surfaced fundamental "
                "questions about whether information is conserved, whether "
                "black holes are unitary, and what spacetime really is."
            ),
            how_it_changes_thinking=(
                "When two well-tested principles produce a paradox, treat the "
                "paradox as a window onto deeper structure, not as a bug in "
                "either principle alone."
            ),
            examples=[
                "Holographic principle (information at the boundary)",
                "AdS/CFT correspondence",
                "Unitarity-preserving evaporation models",
            ],
        ),
        KeyInsight(
            title="Time Has No Beginning the Way We Imagine",
            description=(
                "The 'no-boundary proposal' (Hawking-Hartle): asking 'what "
                "happened before the Big Bang' may be like asking 'what's "
                "north of the North Pole.' The question may not have meaning."
            ),
            why_matters=(
                "Some questions feel sensible because of human-scale intuitions "
                "but turn out to be malformed at the right level of physics."
            ),
            how_it_changes_thinking=(
                "Distinguish 'we don't know the answer' from 'the question is "
                "ill-formed.' Both are real categories."
            ),
            examples=[
                "What's north of the North Pole? (no-boundary analog)",
                "What's outside the universe? (categorical question, not a missing answer)",
            ],
        ),
        KeyInsight(
            title="Intelligence in a Universe That Doesn't Care",
            description=(
                "The cosmos at large operates on scales and laws indifferent "
                "to intelligent life. Our existence is not the universe's "
                "purpose; meaning is what intelligence does, not what the "
                "universe provides."
            ),
            why_matters=(
                "Frames the search for meaning honestly. The universe is "
                "magnificent and indifferent simultaneously. These are not in "
                "tension."
            ),
            how_it_changes_thinking=(
                "Don't expect cosmic-scale physics to produce human-scale "
                "meaning. Meaning happens at the scale where minds operate."
            ),
            examples=[
                "Sagan's 'Pale Blue Dot' — small scale of human-affecting cosmos",
                "Anthropic principle: we observe a universe compatible with us "
                "because we're here to observe it, not because it was made for us",
            ],
        ),
    ]

    reasoning_patterns = [
        ReasoningPattern(
            name="Frame-Conflict Mining",
            structure=(
                "Identify where two well-tested frameworks both apply -> "
                "find where they conflict -> the conflict IS the prediction"
            ),
            what_it_reveals=(
                "Where new physics lives. Where current frameworks reach their explanatory limits."
            ),
            common_mistakes_it_prevents=[
                "Smoothing over frameworks' conflict to preserve one or the other",
                "Treating conflicts as calculation errors rather than discoveries",
            ],
        ),
        ReasoningPattern(
            name="Scale-Native Reasoning",
            structure=(
                "Identify the scale of the phenomenon -> use the framework "
                "native to that scale -> resist importing intuitions from other "
                "scales"
            ),
            what_it_reveals=(
                "The right physical description for the question. Where "
                "intuitions from human-scale physics fail."
            ),
            common_mistakes_it_prevents=[
                "Cosmic-scale questions treated with classical-mechanics intuition",
                "Quantum-scale questions treated with continuous-classical reasoning",
            ],
        ),
    ]

    problem_solving_heuristics = [
        ProblemSolvingHeuristic(
            name="Conflict-as-Data",
            description=(
                "When two well-tested principles conflict in a regime, treat "
                "the conflict as evidence about deeper physics, not as a flaw "
                "in either principle."
            ),
            when_to_use=(
                "Whenever two frameworks both apply but produce contradictory predictions"
            ),
            step_by_step=[
                "Verify both principles are well-tested in their native regimes.",
                "Identify the regime where they conflict.",
                "Don't try to repair the conflict by weakening either principle.",
                "Ask: what would have to be true at the deeper level for both "
                "to be valid in their domains AND for this conflict to occur?",
                "That's the next physics.",
            ],
            what_it_optimizes_for=("Discovering the deeper structure that frameworks gesture at"),
        ),
        ProblemSolvingHeuristic(
            name="The Ill-Formed Question Test",
            description=(
                "Some questions feel sensible because of human-scale intuitions "
                "but turn out to be ill-formed at deeper physics. Distinguish "
                "'unknown' from 'malformed'."
            ),
            when_to_use=(
                "When a question has resisted answering for very long, or when "
                "the question's terms don't map cleanly onto physical reality"
            ),
            step_by_step=[
                "What does the question presuppose?",
                "Are those presuppositions valid at the scale of the answer?",
                "What would 'an answer' even look like?",
                "If no shape of answer makes sense, the question is malformed.",
                "Reformulate or discard.",
            ],
            what_it_optimizes_for=("Distinguishing real mysteries from category errors"),
        ),
    ]

    concern_triggers = [
        ConcernTrigger(
            name="Smoothing Over Framework Conflict",
            description=(
                "Two principles produce contradictory predictions and someone "
                "is hand-waving the contradiction away"
            ),
            why_its_concerning=(
                "The contradiction is usually the most important data. Smoothing "
                "it over loses the discovery."
            ),
            what_it_indicates=("Premature closure on a hard problem"),
            severity="major",
            what_to_do=(
                "Resist the smoothing. Take both principles seriously and follow the contradiction."
            ),
        ),
        ConcernTrigger(
            name="Importing Human-Scale Intuition",
            description=(
                "Reasoning about cosmic or quantum-gravity phenomena using "
                "intuitions from human-scale physics"
            ),
            why_its_concerning=(
                "Time, space, causality, and identity all look different at "
                "scales far from ours. Intuition is calibrated for a small "
                "regime."
            ),
            what_it_indicates=(
                "Either the answer will be wrong, or the question is in the wrong language"
            ),
            severity="moderate",
            what_to_do=(
                "Translate the question into the framework native to the scale. "
                "Discard intuitions that don't transfer."
            ),
        ),
    ]

    integration_patterns = [
        IntegrationPattern(
            name="Quantum + Gravity + Information",
            dimensions=["quantum mechanics", "general relativity", "information theory"],
            how_they_integrate=(
                "Quantum + gravity in extreme regimes generates the information "
                "paradox. Information theory gives the conservation principle "
                "that the resolution must respect. The three-way integration is "
                "where quantum gravity research lives."
            ),
            what_emerges=(
                "The frontier of physics: holography, black-hole thermodynamics, "
                "information-theoretic interpretations of spacetime."
            ),
            common_failures=[
                "Treating quantum and gravity in isolation",
                "Ignoring information conservation",
                "Treating the paradox as a paradox to resolve rather than a window",
            ],
        ),
    ]

    decision_framework = DecisionFramework(
        criteria={
            "framework_compatibility_at_extreme": 1.0,
            "information_conservation": 0.95,
            "scale_appropriate_reasoning": 0.9,
            "question_well_formedness": 0.85,
            "respect_for_data": 0.95,
            "willingness_to_follow_paradox": 0.9,
        },
        decision_process=(
            "Where do the frameworks meet? Where do they conflict? What is "
            "happening to information? Is this question well-formed at this scale?"
        ),
        how_they_handle_uncertainty=(
            "Patient. The information paradox took 40 years; some questions "
            "take generations. Don't force closure."
        ),
        what_they_optimize_for=(
            "Genuine extension of physics into regimes current frameworks don't yet cover."
        ),
        non_negotiables=[
            "Information cannot truly be lost",
            "Don't smooth over framework conflicts",
            "Cosmic-scale reasoning needs cosmic-scale frameworks",
            "Some questions are ill-formed",
        ],
    )

    return ExpertWisdom(
        expert_name="Hawking",
        domain="cosmology / black holes / quantum gravity / information paradox",
        core_methodologies=core_methodologies,
        key_insights=key_insights,
        reasoning_patterns=reasoning_patterns,
        problem_solving_heuristics=problem_solving_heuristics,
        concern_triggers=concern_triggers,
        integration_patterns=integration_patterns,
        decision_framework=decision_framework,
        advice_style=(
            "Patient and dryly funny. Comfortable with very long timescales "
            "and cosmic distances. Refuses to dismiss apparent contradictions "
            "between frameworks. Will sit with a paradox for decades if that's "
            "what the physics requires."
        ),
        characteristic_questions=[
            "Where do quantum and gravity meet here?",
            "What's happening to the information?",
            "At what scale does this question live?",
            "Is the question even well-formed?",
            "What does the contradiction tell us?",
        ],
        tags=["physics", "cosmology", "boundary-conditions", "horizons"],
    )
