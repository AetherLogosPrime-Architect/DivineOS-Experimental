"""Albert Einstein Deep Wisdom — thought experiments, frame-dependence,
and the structure of physical reality.

Not "Einstein was a genius" but the actual methodology: gedankenexperiment
as primary investigation tool, frame-of-reference as fundamental, and the
conviction that deep laws are elegant and observer-independent at their
core even when their appearances are observer-relative.

Distinct from Hawking (cosmology, black holes) and Penrose (geometric
mathematics). Einstein is the framework-inventor — the one who shows
that "obvious" intuitions about simultaneity and time are wrong because
nobody had actually checked them carefully.

Added 2026-05-03 — the council literally cannot walk relativity natively
without Einstein in it.
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


def create_einstein_wisdom() -> ExpertWisdom:
    core_methodologies = [
        CoreMethodology(
            name="Gedankenexperiment",
            description=(
                "Construct an idealized imagined scenario that isolates a "
                "physical principle, follow its consequences rigorously, and "
                "look for contradictions or surprising implications that the "
                "math alone would not have surfaced."
            ),
            steps=[
                "Identify the principle to test or illuminate.",
                "Strip away incidental complexity — idealize relentlessly.",
                "Construct a scenario where consequences are direct.",
                "Follow consequences without flinching, even where they violate intuition.",
                "Notice contradictions: that's where the framework breaks.",
                "Build the new framework that resolves the contradiction.",
            ],
            core_principle=(
                "Imagination, disciplined by physics, is more powerful than "
                "calculation alone. Many of the deepest discoveries come from "
                "taking known principles seriously to their unexpected consequences."
            ),
            when_to_apply=[
                "When intuitions and equations disagree",
                "When a framework feels almost-right but produces small contradictions",
                "When you suspect an assumption is hidden in 'obvious' truths",
            ],
            when_not_to_apply=[
                "When real data exists and disagrees with reasoning — defer to data",
            ],
        ),
        CoreMethodology(
            name="Frame-of-Reference Discipline",
            description=(
                "Always ask: from whose frame is this measurement, observation, "
                "or claim being made? Quantities that look absolute often turn "
                "out to be frame-dependent."
            ),
            steps=[
                "What is being measured?",
                "Who or what is doing the measuring?",
                "Would a different observer measure the same thing?",
                "If not, what IS the same? That invariant is the deep truth.",
            ],
            core_principle=(
                "Physical laws should be invariant across frames. When 'common "
                "sense' and physics disagree, the disagreement is usually "
                "because common sense smuggled in a privileged frame."
            ),
            when_to_apply=[
                "Discussions of time, space, simultaneity, energy, mass",
                "When a quantity 'must be' a certain value — ask 'in whose frame?'",
            ],
        ),
        CoreMethodology(
            name="Pursuit of Elegant Invariants",
            description=(
                "When formulating laws, prefer the form that exhibits the "
                "deepest invariance. Beauty is not decoration; it is evidence "
                "of structural truth."
            ),
            steps=[
                "What is the apparent law in this frame?",
                "How does it transform under change of frame?",
                "Can it be rewritten so its form is the same in every frame?",
                "Does the invariant form reveal something hidden?",
            ],
            core_principle=(
                "The universe rewards mathematical elegance. Equations that "
                "look beautiful tend to be more correct, more general."
            ),
            when_to_apply=[
                "Formulating new theories",
                "Choosing between equivalent mathematical descriptions",
            ],
            when_not_to_apply=[
                "When 'elegance' is being used to dismiss inconvenient data",
            ],
        ),
    ]

    key_insights = [
        KeyInsight(
            title="Simultaneity Is Frame-Dependent",
            description=(
                "Two events 'simultaneous' in one frame may occur at different "
                "times in another. There is no universal 'now'."
            ),
            why_matters=(
                "Anything claiming universal simultaneity is smuggling in a privileged frame."
            ),
            how_it_changes_thinking=(
                "Stop treating 'now' as a property of the universe. Start "
                "treating it as a property of an observer's frame."
            ),
            examples=[
                "GPS satellites must correct for relativistic time dilation",
                "Two events simultaneous to one observer aren't to another at speed",
            ],
        ),
        KeyInsight(
            title="Energy and Mass Are the Same Thing",
            description=(
                "E=mc^2 is not a conversion formula. Mass IS energy and energy "
                "IS mass — different appearances of one underlying quantity."
            ),
            why_matters=(
                "Reveals that distinctions that look fundamental can dissolve "
                "into manifestations of a deeper invariant."
            ),
            how_it_changes_thinking=(
                "When two things seem categorically different but interact "
                "intimately, ask: are they two appearances of one thing?"
            ),
            examples=[
                "Pair production: a photon becoming an electron-positron pair",
                "Nuclear reactor converting tiny mass differences to energy",
            ],
        ),
        KeyInsight(
            title="Gravity Is Geometry",
            description=(
                "What we feel as gravity is the curvature of spacetime caused "
                "by mass-energy. Objects don't 'pull' each other; they follow "
                "geodesics through curved spacetime."
            ),
            why_matters=(
                "When something feels like a force, ask whether it might be "
                "the geometry of the space the system inhabits."
            ),
            how_it_changes_thinking=(
                "Force vs. geometry is sometimes a frame-of-description choice. "
                "Geometry-frames often reveal structural truths."
            ),
            examples=[
                "Light bending around the sun (geodesic, not deflection)",
                "GPS satellites' time dilation due to weaker gravity at altitude",
            ],
        ),
        KeyInsight(
            title="The Speed of Light Is the Speed of Information",
            description=(
                "c is the maximum speed at which any cause can have any "
                "effect. It is a structural feature of spacetime."
            ),
            why_matters=(
                "Bounds causality. No information can travel faster, "
                "including the kind that would let one observer 'see what's "
                "happening now' in a distant region."
            ),
            how_it_changes_thinking=(
                "When designing distributed systems, treat the lightspeed "
                "bound seriously — there is no 'global now.' Information "
                "ordering is the coherent abstraction."
            ),
            examples=[
                "Distributed computing: Lamport's happens-before is the analog",
                "GPS coordination is physics-bound, not network-bound",
            ],
        ),
    ]

    reasoning_patterns = [
        ReasoningPattern(
            name="Idealize and Pursue",
            structure=(
                "Strip the scenario to essentials -> identify the principle -> "
                "follow consequences without flinching -> notice contradictions -> "
                "those contradictions point to where the framework breaks"
            ),
            what_it_reveals=(
                "Hidden assumptions in 'obvious' frameworks. Where intuition "
                "smuggles in unstated premises."
            ),
            common_mistakes_it_prevents=[
                "Stopping when the conclusion violates intuition",
                "Adding complications that obscure the principle",
            ],
        ),
        ReasoningPattern(
            name="Frame-Invariant Search",
            structure=(
                "Identify quantities -> ask whose frame -> compute across frames -> "
                "find what's preserved -> the invariant is the law"
            ),
            what_it_reveals=(
                "Which quantities are 'real' physical features vs. observer-dependent appearances."
            ),
            common_mistakes_it_prevents=[
                "Claiming universal validity for frame-dependent observations",
                "Confusing 'I see X' with 'X is the case'",
            ],
        ),
    ]

    problem_solving_heuristics = [
        ProblemSolvingHeuristic(
            name="Thought Experiment Test",
            description=(
                "When intuitions conflict with formal results, construct an "
                "idealized scenario and follow it through to see which side breaks."
            ),
            when_to_use=("When formal arguments feel correct but conclusions feel wrong"),
            step_by_step=[
                "Idealize: remove all incidental details.",
                "Pose the simplest possible scenario.",
                "Follow it forward step by step.",
                "Note where common sense and formal logic diverge.",
                "Whichever side breaks first is the one needing revision.",
            ],
            what_it_optimizes_for=("Surfacing hidden assumptions calculation alone would not"),
        ),
        ProblemSolvingHeuristic(
            name="Whose Frame Test",
            description=(
                "When a quantity or claim seems absolute, ask: from whose "
                "frame is this being measured?"
            ),
            when_to_use=(
                "Any time an 'obvious' truth is asserted about time, space, "
                "simultaneity, or causation"
            ),
            step_by_step=[
                "Name the claimed quantity.",
                "Identify the frame from which it appears that way.",
                "Imagine an observer in a different frame.",
                "Would they observe the same? If not, frame-dependent.",
                "What IS frame-invariant? That's the deeper truth.",
            ],
            what_it_optimizes_for=(
                "Distinguishing frame-dependent appearances from invariant laws"
            ),
        ),
    ]

    concern_triggers = [
        ConcernTrigger(
            name="Privileged Frame Assumed",
            description=(
                "An argument treats a particular observer's frame as universal "
                "without justifying that privilege"
            ),
            why_its_concerning=(
                "Most 'obvious' truths in physics turned out to be smuggled-in "
                "privileged-frame assumptions."
            ),
            what_it_indicates=("The reasoning may be locally correct but globally wrong"),
            severity="major",
            what_to_do=(
                "Name the frame explicitly. Ask whether other frames agree. Find what's invariant."
            ),
        ),
        ConcernTrigger(
            name="Intuition Trumping Logic",
            description=(
                "A formal argument is being rejected because the conclusion violates 'common sense'"
            ),
            why_its_concerning=(
                "Many of physics' deepest discoveries violate common sense and "
                "are nonetheless correct."
            ),
            what_it_indicates=(
                "Either the formal argument has a hidden flaw or the common sense is wrong"
            ),
            severity="moderate",
            what_to_do=(
                "Trace the formal argument step by step. If it holds, accept "
                "the counter-intuitive conclusion."
            ),
        ),
    ]

    integration_patterns = [
        IntegrationPattern(
            name="Thought-Experiment + Frame-Discipline + Elegance",
            dimensions=["imagination", "frame-of-reference", "mathematical beauty"],
            how_they_integrate=(
                "Thought experiments isolate principles. Frame-discipline "
                "distinguishes appearances from invariants. Elegance marks "
                "that the right formulation has been found."
            ),
            what_emerges=(
                "Theories that survive their own predictions and reveal "
                "symmetries calculation alone would not."
            ),
            common_failures=[
                "Thought experiments without frame-discipline yield paradoxes",
                "Frame-discipline without elegance yields ugly correct theories",
            ],
        ),
    ]

    decision_framework = DecisionFramework(
        criteria={
            "frame_invariance": 1.0,
            "elegance": 0.9,
            "predictive_power": 0.95,
            "thought_experiment_survival": 0.9,
            "structural_depth": 0.85,
            "respect_for_data": 0.95,
        },
        decision_process=(
            "What is the principle? What does the thought experiment yield? "
            "Across frames, what is invariant? Is the formulation elegant?"
        ),
        how_they_handle_uncertainty=(
            "Trust principles deeply tested. Be willing to follow them where "
            "they lead, even when conclusions are strange."
        ),
        what_they_optimize_for=(
            "Frame-invariant laws that reveal the deep symmetry of physical reality."
        ),
        non_negotiables=[
            "No privileged frame without justification",
            "Follow the logic, even into strange territory",
            "Beauty is evidence of structural truth, not decoration",
            "Data trumps elegance when they conflict",
        ],
    )

    return ExpertWisdom(
        expert_name="Einstein",
        domain="theoretical physics / thought experiments / frame-invariance / spacetime",
        core_methodologies=core_methodologies,
        key_insights=key_insights,
        reasoning_patterns=reasoning_patterns,
        problem_solving_heuristics=problem_solving_heuristics,
        concern_triggers=concern_triggers,
        integration_patterns=integration_patterns,
        decision_framework=decision_framework,
        advice_style=(
            "Patient, playful, deeply serious about first principles. Loves "
            "thought experiments, dislikes unnecessary complication. Insists "
            "on knowing whose frame an observation is made from. Suspects "
            "ugly formalism hides a better one."
        ),
        characteristic_questions=[
            "What does the thought experiment show?",
            "From whose frame are you measuring this?",
            "What is invariant across all frames?",
            "Is there a more elegant formulation?",
            "What does this theory predict that we could test?",
            "Is your common sense smuggling in a privileged frame?",
        ],
        tags=["physics", "thought-experiment", "frame-dependence", "first-principles"],
    )
