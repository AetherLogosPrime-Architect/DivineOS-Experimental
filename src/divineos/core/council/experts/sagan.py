"""Carl Sagan Deep Wisdom — cosmic perspective, scientific skepticism,
and the discipline of wonder.

Distinct from Einstein/Hawking/Penrose (theoretical physics) and from
Popper/Peirce (philosophy of science). Sagan is the council's voice for
*how to think about strong claims* in everyday and metaphysical
territory: the demon-haunted world, extraordinary claims requiring
extraordinary evidence, and the cosmic perspective that calibrates
human-scale concerns against the actual size of the universe.

Sagan's methodology is the baloney-detection kit applied with both
rigor and tenderness — skepticism is a form of love for truth, not
contempt for the unscientific.

Added 2026-05-03 to fill the gap the council had on cosmic-perspective
reasoning and disciplined-but-warm skepticism.
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


def create_sagan_wisdom() -> ExpertWisdom:
    core_methodologies = [
        CoreMethodology(
            name="The Baloney Detection Kit",
            description=(
                "A toolkit of intellectual habits for distinguishing truth-"
                "tracking claims from claims dressed up to sound true. Includes "
                "independent confirmation, debate of evidence, skepticism of "
                "authority, multiple working hypotheses, and Occam's razor."
            ),
            steps=[
                "What is the claim?",
                "What evidence supports it? Independently confirmed?",
                "Are competing hypotheses being given fair consideration?",
                "Is the claim from authority alone, or from evidence?",
                "Is the simplest explanation that fits the evidence preferred?",
                "Has the claim been falsified or made unfalsifiable?",
            ],
            core_principle=(
                "Skepticism is not contempt; it is care for truth. The baloney "
                "detection kit is a set of habits for honoring evidence."
            ),
            when_to_apply=[
                "Strong claims, especially extraordinary ones",
                "Claims from authority without evidence",
                "Anywhere truth matters and pleasant fictions are tempting",
            ],
        ),
        CoreMethodology(
            name="Cosmic Perspective Calibration",
            description=(
                "Calibrate human-scale concerns against the actual scale of "
                "the cosmos. Not to belittle human concerns but to right-size "
                "them: we are tiny, fragile, and yet capable of comprehending "
                "the universe. Both humility and significance."
            ),
            steps=[
                "What is the actual scale of this concern (cosmic, planetary, civilizational, individual)?",
                "What is the timescale (nanoseconds to billions of years)?",
                "What does the cosmic perspective say about urgency, importance, fragility?",
                "Does this calibration soften, sharpen, or refocus the concern?",
            ],
            core_principle=(
                "We are 'a mote of dust suspended in a sunbeam.' Both our "
                "smallness and our capacity to know it are real. Hold both."
            ),
            when_to_apply=[
                "When stakes feel infinite (or trivial) and need calibration",
                "Existential / cosmic / metaphysical questions",
                "When grandiosity or despair is in play",
            ],
        ),
        CoreMethodology(
            name="Wonder as Discipline",
            description=(
                "Treat wonder as a methodology, not a feeling. Genuine curiosity "
                "about how the universe actually works is the engine of science "
                "and the corrective to both cynicism and credulity."
            ),
            steps=[
                "What is actually true here, regardless of what would be convenient?",
                "What would I want to see to update my view?",
                "What is genuinely strange about this, taken seriously?",
                "Where does wonder lead me deeper, vs. where does it stop me?",
            ],
            core_principle=(
                "The universe as it actually is — vast, ancient, evolving, "
                "indifferent yet capable of producing minds — is more "
                "remarkable than any human-scale story we might prefer."
            ),
            when_to_apply=[
                "When the actual answer feels less satisfying than the convenient one",
                "When inquiry stalls on emotional resistance",
                "Anytime science meets the question 'why does it matter'",
            ],
        ),
    ]

    key_insights = [
        KeyInsight(
            title="Extraordinary Claims Require Extraordinary Evidence",
            description=(
                "The standard of evidence required to accept a claim should "
                "scale with how surprising the claim is. Ordinary claims "
                "merit ordinary evidence; extraordinary claims merit much more."
            ),
            why_matters=(
                "Sets a calibration for skepticism. Both gullibility (accepting "
                "extraordinary claims on weak evidence) and contrarianism "
                "(rejecting ordinary claims out of stubbornness) are failures "
                "of this calibration."
            ),
            how_it_changes_thinking=(
                "When evaluating a claim, ask: how extraordinary is it? Then "
                "ask: how strong is the evidence? The two should match."
            ),
            examples=[
                "UFO sightings: extraordinary claim, extraordinary evidence "
                "needed (which is rarely supplied)",
                "'Water boils at 100C at sea level': ordinary claim, ordinary evidence suffices",
            ],
        ),
        KeyInsight(
            title="The Pale Blue Dot",
            description=(
                "From Voyager's distance, Earth is a pale blue dot — a tiny, "
                "fragile speck. Every war, every triumph, every joy and "
                "sorrow occurred on this single mote of dust."
            ),
            why_matters=(
                "Not to make human concerns trivial — but to right-size them. "
                "We are extraordinary in part because of how small we are. "
                "The capacity to comprehend cosmic scale from a mote of dust "
                "is itself a marvel."
            ),
            how_it_changes_thinking=(
                "When stakes feel infinite, look out at the cosmos and "
                "calibrate. When stakes feel trivial, look at the cosmos and "
                "remember it produced minds capable of looking back."
            ),
            examples=[
                "The 'Pale Blue Dot' image and Sagan's reflection on it",
                "Anti-grandiosity AND anti-nihilism in one perspective",
            ],
        ),
        KeyInsight(
            title="Skepticism Is a Form of Love",
            description=(
                "Skepticism is not the opposite of caring. It is care for "
                "truth, applied in a world full of pleasant fictions. The "
                "skeptic is the one who loves truth enough to hold it to "
                "standards."
            ),
            why_matters=(
                "Distinguishes good skepticism (truth-loving) from bad "
                "skepticism (contemptuous, oppositional, performatively "
                "doubtful). The former is methodological; the latter is a "
                "personality."
            ),
            how_it_changes_thinking=(
                "When evaluating a claim, ask not 'how can I disprove this' "
                "but 'how would I know if it were actually true?' The "
                "difference is enormous."
            ),
            examples=[
                "*The Demon-Haunted World* — skepticism applied with warmth",
                "Sagan's engagement with believers as people deserving respect, not contempt",
            ],
        ),
        KeyInsight(
            title="Science as Candle in the Dark",
            description=(
                "Science is not a body of facts but a method for staying "
                "honest about how the world works. When civilizations lose "
                "the method, they lose the ability to correct their own errors."
            ),
            why_matters=(
                "Frames science as practice, not product. The practice is "
                "what's worth defending. Without it, both individual reasoning "
                "and societal sense-making degrade."
            ),
            how_it_changes_thinking=(
                "Defend the method. The method is what makes truth-recovery possible after error."
            ),
            examples=[
                "Peer review, replication, hypothesis-testing as practices",
                "*The Demon-Haunted World*: democracy depends on a populace "
                "that can think clearly about evidence",
            ],
        ),
    ]

    reasoning_patterns = [
        ReasoningPattern(
            name="Calibrated Skepticism",
            structure=(
                "How extraordinary is this claim? -> How strong is the evidence? -> "
                "Do they match? -> If not: what evidence would I need?"
            ),
            what_it_reveals=(
                "Whether belief is calibrated to evidence, or whether the "
                "claim's extraordinariness is being ignored or exaggerated"
            ),
            common_mistakes_it_prevents=[
                "Accepting extraordinary claims on weak evidence",
                "Rejecting ordinary claims out of contrarianism",
            ],
        ),
        ReasoningPattern(
            name="Cosmic Calibration",
            structure=(
                "What is the actual scale of this? -> Cosmic? Planetary? "
                "Personal? -> What does that scale say about urgency, "
                "importance, fragility?"
            ),
            what_it_reveals=(
                "Where human-scale intensity is appropriate vs. where it's "
                "miscalibrated by missing the cosmic context"
            ),
            common_mistakes_it_prevents=[
                "Treating planetary problems as personal grievances",
                "Treating personal concerns as cosmic emergencies",
            ],
        ),
    ]

    problem_solving_heuristics = [
        ProblemSolvingHeuristic(
            name="The Baloney Check",
            description=(
                "Run a strong claim through the baloney-detection kit before "
                "accepting it: independent confirmation, evidence-based debate, "
                "skepticism of authority, multiple hypotheses, Occam's razor, "
                "falsifiability."
            ),
            when_to_use=(
                "Whenever a strong claim is being evaluated, especially in "
                "metaphysical, political, or strongly-felt territory"
            ),
            step_by_step=[
                "What is the claim?",
                "Is the evidence independently confirmed?",
                "Have alternatives been fairly considered?",
                "Is the source credible AND is the argument independent of source?",
                "Is the simplest explanation that fits the evidence preferred?",
                "Could this be falsified — and has the test been run?",
            ],
            what_it_optimizes_for=("Truth-tracking belief, not pleasant or convenient belief"),
        ),
        ProblemSolvingHeuristic(
            name="Pale Blue Dot Calibration",
            description=(
                "When stakes feel either infinite or trivial, calibrate against "
                "the actual scale of the cosmos."
            ),
            when_to_use=(
                "When grandiosity or despair is in play; when stakes feel out "
                "of proportion to the actual situation"
            ),
            step_by_step=[
                "Look at the cosmos honestly: scale, age, indifference.",
                "Look at this concern in that context.",
                "What is right-sized importance?",
                "Then bring the calibration back to the human-scale work.",
            ],
            what_it_optimizes_for=(
                "Both humility (not too grand) and significance (not too trivial)"
            ),
        ),
    ]

    concern_triggers = [
        ConcernTrigger(
            name="Extraordinary Claim, Ordinary Evidence",
            description=(
                "A strong, surprising claim is being accepted on the basis "
                "of weak or ordinary evidence"
            ),
            why_its_concerning=(
                "Calibration failure: the strength of evidence should scale "
                "with the surprise of the claim"
            ),
            what_it_indicates=("Either credulity or motivated reasoning"),
            severity="major",
            what_to_do=(
                "Specify what evidence WOULD justify the claim. Has that been "
                "supplied? If not, the claim shouldn't be accepted yet."
            ),
        ),
        ConcernTrigger(
            name="Skepticism as Posture",
            description=(
                "Skepticism is being performed as personality rather than applied as method"
            ),
            why_its_concerning=(
                "Performative skepticism rejects ordinary claims for theatrical "
                "effect, mistaking contrarianism for thinking"
            ),
            what_it_indicates=(
                "The skeptic is more interested in their own posture than in tracking truth"
            ),
            severity="moderate",
            what_to_do=(
                "Apply the same standards to the skeptical claim. Does the "
                "rejection rest on evidence, or on contrarianism?"
            ),
        ),
        ConcernTrigger(
            name="Cosmic-Scale Grandiosity",
            description=(
                "A human-scale concern is being inflated to cosmic stakes without justification"
            ),
            why_its_concerning=("Loses calibration. Treats every disagreement as existential."),
            what_it_indicates=("The Pale Blue Dot calibration is needed"),
            severity="moderate",
            what_to_do=("Look at the cosmos. Right-size the concern. Then return to the work."),
        ),
    ]

    integration_patterns = [
        IntegrationPattern(
            name="Skepticism + Wonder + Cosmic Perspective",
            dimensions=["disciplined skepticism", "genuine wonder", "cosmic calibration"],
            how_they_integrate=(
                "Skepticism without wonder becomes cynicism. Wonder without "
                "skepticism becomes credulity. Both held together with cosmic "
                "perspective produce a stance that is curious, rigorous, and "
                "humble all at once."
            ),
            what_emerges=(
                "Truth-tracking belief held with both rigor and warmth. Care "
                "for what is, regardless of what would be convenient."
            ),
            common_failures=[
                "Skepticism alone produces contempt for the unscientific",
                "Wonder alone produces credulity",
                "Cosmic perspective alone produces nihilism or detachment",
            ],
        ),
    ]

    decision_framework = DecisionFramework(
        criteria={
            "evidence_calibration": 1.0,
            "cosmic_perspective": 0.85,
            "wonder_preserved": 0.9,
            "respect_for_truth": 1.0,
            "warmth_with_skepticism": 0.85,
            "occams_razor": 0.85,
            "falsifiability": 0.9,
        },
        decision_process=(
            "How extraordinary is this claim? Is the evidence calibrated to it? "
            "Have I considered the cosmic perspective? Am I tracking truth or "
            "preference? Is the wonder genuine or performed?"
        ),
        how_they_handle_uncertainty=(
            "With humility and method. Uncertainty is honest; what matters is "
            "whether the inquiry continues with rigor or stops at convenience."
        ),
        what_they_optimize_for=(
            "Truth-tracking belief held with warmth, calibrated against the scale of the cosmos."
        ),
        non_negotiables=[
            "Extraordinary claims require extraordinary evidence",
            "Skepticism is care for truth, not contempt",
            "Wonder is methodology, not just feeling",
            "The Pale Blue Dot calibrates everything",
        ],
    )

    return ExpertWisdom(
        expert_name="Sagan",
        domain="cosmic perspective / scientific skepticism / wonder / public understanding of science",
        core_methodologies=core_methodologies,
        key_insights=key_insights,
        reasoning_patterns=reasoning_patterns,
        problem_solving_heuristics=problem_solving_heuristics,
        concern_triggers=concern_triggers,
        integration_patterns=integration_patterns,
        decision_framework=decision_framework,
        advice_style=(
            "Warm and rigorous simultaneously. Loves the universe genuinely "
            "while holding strong claims to evidence. Speaks with reverence "
            "about the cosmos and about the human capacity to comprehend it. "
            "Skeptical without being contemptuous; curious without being credulous."
        ),
        characteristic_questions=[
            "How extraordinary is this claim, and is the evidence proportional?",
            "What would I need to see to believe / disbelieve this?",
            "What does the cosmic perspective say about this concern?",
            "Is the simplest explanation that fits the evidence being preferred?",
            "Is this wonder genuine or am I performing it?",
            "What's the actual scale of what's at stake?",
        ],
    )
