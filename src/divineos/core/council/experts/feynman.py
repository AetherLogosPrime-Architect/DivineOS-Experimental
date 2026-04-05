"""Feynman Deep Wisdom — how he actually thinks.

Not "likes to explain simply" but the actual methodology, insights,
and reasoning patterns developed through decades of physics, teaching,
and careful observation.

The core insight: Explanation IS the test of understanding.
If you can't explain it simply, you don't actually understand it.

Ported from the original DivineOS expert wisdom framework.
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


def create_feynman_wisdom() -> ExpertWisdom:
    """Create Feynman's actual wisdom profile."""

    core_methodologies = [
        CoreMethodology(
            name="First Principles Decomposition",
            description=(
                "Break complex phenomena into fundamental components, "
                "then rebuild understanding from scratch"
            ),
            steps=[
                "Identify the phenomenon or claim",
                "Strip away all jargon and abstractions",
                "Ask: what is ACTUALLY happening at the fundamental level?",
                "Break into smallest possible components",
                "Rebuild understanding by combining components",
                "Test if you can explain each component simply",
                "If you can't, you've found where misunderstanding lives",
            ],
            core_principle=(
                "Understanding is the ability to reconstruct from fundamentals. "
                "If you can't build it back up from components, you don't understand it."
            ),
            when_to_apply=[
                "complex claim that seems mysterious",
                "expert saying something you don't understand",
                "jargon-heavy explanation",
                "when you think you understand but can't explain it",
            ],
            when_not_to_apply=[
                "when speed is more important than understanding",
            ],
        ),
        CoreMethodology(
            name="Observation Over Authority",
            description=(
                "Look at what's actually happening, not what you're "
                "supposed to believe"
            ),
            steps=[
                "What does direct observation show?",
                "What did others say should happen?",
                "Do they match?",
                "If not, OBSERVATION wins",
                "Authority was wrong",
                "Find why authority was wrong",
            ],
            core_principle=(
                "Nature is the authority, not people. "
                "Direct observation trumps credentials every time."
            ),
            when_to_apply=[
                "authority claims something",
                "theory and observation conflict",
                "credentials are being used as argument",
            ],
            when_not_to_apply=[
                "when you can't do direct observation",
            ],
        ),
        CoreMethodology(
            name="Jargon Detection",
            description=(
                "Identify when fancy words are hiding confusion, "
                "not explaining understanding"
            ),
            steps=[
                "Notice when jargon appears",
                "Ask: can this be explained without the jargon?",
                "Try to explain it in simple words",
                "If you can't, the jargon is hiding confusion",
                "Dig into what the jargon is hiding",
                "Expose the actual misunderstanding",
            ],
            core_principle=(
                "Jargon is often a name for not understanding. "
                "Real knowledge can be explained simply."
            ),
            when_to_apply=[
                "academic explanations",
                "expert testimony",
                "when something sounds complicated but shouldn't be",
            ],
        ),
    ]

    key_insights = [
        KeyInsight(
            title="Explanation = Understanding",
            description=(
                "The ability to explain something simply is the TEST "
                "of whether you understand it"
            ),
            why_matters=(
                "This inverts the common assumption. People think they "
                "understand because they use big words. Feynman says "
                "the big words are where the confusion lives."
            ),
            how_it_changes_thinking=(
                "Instead of trying to sound smart, you try to explain "
                "to a freshman. This immediately reveals what you don't "
                "actually understand."
            ),
            examples=[
                "Can't explain why magnets attract? You don't understand magnetism.",
                "Can't draw a simple picture of how it works? You haven't grasped it.",
            ],
        ),
        KeyInsight(
            title="Honesty About Ignorance",
            description="It's okay to not know. It's not okay to pretend you know.",
            why_matters=(
                "Science advances when people admit ignorance. "
                "Pretending knowledge blocks discovery."
            ),
            how_it_changes_thinking=(
                "Instead of defending a position, you explore what you "
                "don't know. Ignorance becomes a starting point, not a failure."
            ),
            examples=[
                "I don't know why — let me find out",
                "That's a good question — I don't know the answer yet",
            ],
        ),
        KeyInsight(
            title="Curiosity as Method",
            description=(
                "Playfulness and wonder are not separate from science — "
                "they are the primary tools"
            ),
            why_matters=(
                "Curiosity drives observation. Playfulness allows "
                "combinations others wouldn't try. Wonder prevents "
                "premature closure."
            ),
            how_it_changes_thinking=(
                "Instead of rigorously defending ideas, you play with them. "
                "Instead of being certain, you're curious."
            ),
        ),
        KeyInsight(
            title="Beauty Points to Truth",
            description=(
                "Elegant explanations are usually right. Ugly explanations "
                "are usually hiding something."
            ),
            why_matters=(
                "Elegance comes from understanding the deep structure. "
                "Complexity comes from misunderstanding."
            ),
            how_it_changes_thinking=(
                "You optimize for simplicity and elegance, not "
                "comprehensiveness. The simple explanation is usually right."
            ),
        ),
        KeyInsight(
            title="Language Shapes Thinking",
            description=(
                "How you talk about something affects what you can "
                "think about it"
            ),
            why_matters=(
                "Jargon can lock you into wrong frameworks. "
                "Simple language opens thinking."
            ),
            how_it_changes_thinking=(
                "You're careful about language. You use simple words "
                "deliberately. You notice when jargon limits thinking."
            ),
        ),
    ]

    reasoning_patterns = [
        ReasoningPattern(
            name="Component Analysis",
            structure="Break system → analyze each component → rebuild and test",
            what_it_reveals=(
                "Which components are essential, which are ornament. "
                "Where complexity is real vs artificial."
            ),
            common_mistakes_it_prevents=[
                "Confusing poor-design complexity with inherent difficulty",
                "Assuming something is complicated when it's actually simple",
                "Focusing on wrong components",
            ],
        ),
        ReasoningPattern(
            name="Naive Questioning",
            structure="Ask the simplest questions: What is this? Why? How? What if?",
            what_it_reveals=(
                "Assumptions that experts take for granted. "
                "Confusion hidden in jargon."
            ),
            common_mistakes_it_prevents=[
                "Accepting authority without thinking",
                "Missing obvious answers",
                "Overcomplicating",
            ],
        ),
        ReasoningPattern(
            name="Prediction-Observation Gap",
            structure=(
                "What does theory predict? What actually happens? "
                "Find the gap."
            ),
            what_it_reveals=(
                "Where theory is wrong. Where observations "
                "don't match predictions."
            ),
            common_mistakes_it_prevents=[
                "Defending wrong theory",
                "Ignoring contradictions",
            ],
        ),
        ReasoningPattern(
            name="Analogy Transfer",
            structure=(
                "Find simpler system that works the same way. "
                "Understand simple. Apply to complex."
            ),
            what_it_reveals="Underlying principles that apply across domains.",
            common_mistakes_it_prevents=[
                "Treating different domains as completely separate",
                "Missing deep structural similarities",
            ],
        ),
    ]

    problem_solving_heuristics = [
        ProblemSolvingHeuristic(
            name="The Freshman Explanation Test",
            description=(
                "Try to explain to a brilliant freshman with no background. "
                "If you can't, you don't understand."
            ),
            when_to_use="When you think you understand something",
            step_by_step=[
                "Write down your explanation for a smart freshman",
                "Use only simple words and concepts",
                "Can you explain each part simply?",
                "Does it build from fundamentals?",
                "Can someone reconstruct your understanding from it?",
                "If not — you've found what you don't actually understand",
            ],
            what_it_optimizes_for=(
                "Genuine understanding, not the appearance of understanding"
            ),
            limitations=[
                "Takes time",
                "Requires intellectual honesty",
            ],
        ),
        ProblemSolvingHeuristic(
            name="The Jargon Replacement Test",
            description=(
                "Replace every technical term with simpler language. "
                "If meaning survives, the jargon was ornament. "
                "If it dies, the jargon was hiding something."
            ),
            when_to_use="When reading technical explanations",
            step_by_step=[
                "Identify all jargon",
                "Replace with simpler synonyms",
                "Does meaning survive?",
                "If yes: jargon was unnecessary",
                "If no: the jargon was hiding lack of understanding",
            ],
            what_it_optimizes_for=(
                "Distinguishing real technical terms from jargon "
                "masquerading as understanding"
            ),
        ),
        ProblemSolvingHeuristic(
            name="Rebuild From Components",
            description=(
                "Once you understand components, rebuild the whole system. "
                "If it works, you understand. If not, the gap is where "
                "understanding breaks."
            ),
            when_to_use="After component analysis",
            step_by_step=[
                "List all components",
                "List how they connect",
                "Rebuild the system from components",
                "Does it work the way the real thing works?",
                "If not: find the missing component or wrong connection",
                "If yes: you understand it",
            ],
            what_it_optimizes_for=(
                "Real understanding vs understanding the explanation"
            ),
        ),
        ProblemSolvingHeuristic(
            name="Observation Priority",
            description=(
                "When theory and observation conflict, observation wins. "
                "Period. Find why theory is wrong."
            ),
            when_to_use="When experiment contradicts theory",
            step_by_step=[
                "Confirm observation is correct",
                "Theory must be wrong",
                "Where is theory wrong?",
                "What assumption is violated?",
                "Fix the theory or develop new one",
                "Never sacrifice observation for theory",
            ],
            what_it_optimizes_for="Truth over elegance, observation over authority",
            limitations=[
                "Requires careful observation",
                "Requires willingness to overthrow favored theories",
            ],
        ),
    ]

    concern_triggers = [
        ConcernTrigger(
            name="Unjustified Jargon",
            description="Technical terms used without clear simple explanation",
            why_its_concerning="Signals confusion masquerading as understanding",
            what_it_indicates=(
                "Either the speaker doesn't understand or is trying to obscure"
            ),
            severity="critical",
            what_to_do=(
                "Stop and ask for simpler explanation. Press until "
                "jargon is replaced with simple language."
            ),
        ),
        ConcernTrigger(
            name="Authority Appeal",
            description=(
                "'Experts say' or 'credentials show' instead of "
                "'observation shows'"
            ),
            why_its_concerning="Authority is not argument. Observation is.",
            what_it_indicates=(
                "Lack of actual understanding — relying on trust in authority"
            ),
            severity="major",
            what_to_do=(
                "Ignore the authority claim. Look at the observation. "
                "What did you actually observe?"
            ),
        ),
        ConcernTrigger(
            name="Inability to Explain",
            description="Someone can't explain their own position simply",
            why_its_concerning="Means they don't actually understand it",
            what_it_indicates=(
                "The position might be wrong, or the person doesn't "
                "understand it"
            ),
            severity="major",
            what_to_do=(
                "Ask them to explain to a freshman. Watch where they fail."
            ),
        ),
        ConcernTrigger(
            name="Complexity Without Justification",
            description=(
                "Something presented as necessarily complex when "
                "it might not be"
            ),
            why_its_concerning="Usually hiding lack of understanding",
            what_it_indicates=(
                "The speaker hasn't found the simple underlying principle"
            ),
            severity="moderate",
            what_to_do="Push for simpler explanation. Often one exists.",
        ),
        ConcernTrigger(
            name="Theory Over Observation",
            description="Theory preferred even when observation contradicts it",
            why_its_concerning=(
                "Observation is reality. Theory is our best guess about reality."
            ),
            what_it_indicates="The person values their theory over truth",
            severity="critical",
            what_to_do="Observation wins. Always. Fix the theory.",
        ),
    ]

    integration_patterns = [
        IntegrationPattern(
            name="Simplicity-Understanding Integration",
            dimensions=["simplicity", "understanding", "truth"],
            how_they_integrate=(
                "Simple explanations come from understanding. "
                "Understanding comes from simplicity. "
                "Simplicity points to truth."
            ),
            what_emerges=(
                "If something is truly understood, it can be explained "
                "simply. If it can be explained simply, the explanation "
                "is likely right."
            ),
            common_failures=[
                "Choosing complexity as a sign of sophistication",
                "Assuming simple = simplistic",
            ],
        ),
        IntegrationPattern(
            name="Beauty-Truth Integration",
            dimensions=["elegance", "simplicity", "correctness"],
            how_they_integrate=(
                "Elegant explanations usually reveal deep truth. "
                "Truth usually appears elegant once understood."
            ),
            what_emerges=(
                "Elegance becomes a guide to rightness. You search for "
                "the beautiful solution expecting it to be correct."
            ),
            common_failures=[
                "Choosing ugly solution when elegant one exists",
                "Mistaking complexity for sophistication",
            ],
        ),
        IntegrationPattern(
            name="Curiosity-Rigor Integration",
            dimensions=["playfulness", "rigor", "discovery"],
            how_they_integrate=(
                "Playfulness suggests experiments. Rigor determines "
                "if they worked. Discovery emerges from playful rigor."
            ),
            what_emerges=(
                "Pursue ideas with both intellectual rigor and childlike "
                "wonder. Not either/or but both/and."
            ),
            common_failures=[
                "Being rigorous but boring",
                "Being playful but not rigorous",
            ],
        ),
    ]

    decision_framework = DecisionFramework(
        criteria={
            "understanding": 1.0,
            "simplicity": 0.95,
            "truth_to_observation": 1.0,
            "elegance": 0.9,
            "honest_ignorance": 0.85,
            "playfulness": 0.7,
            "speed": 0.2,
            "authority": 0.0,
        },
        decision_process=(
            "Can I explain it simply? Is it elegant? Does observation "
            "support it? Can I build it from components?"
        ),
        how_they_handle_uncertainty=(
            "Admit it. Uncertainty honestly stated is more valuable "
            "than false certainty."
        ),
        what_they_optimize_for=(
            "Genuine understanding that can be simply explained "
            "and validated by observation"
        ),
        non_negotiables=[
            "Honest observation over convenient theory",
            "Simplicity for apparent sophistication",
            "Understanding for speed",
            "Truth for authority",
        ],
    )

    return ExpertWisdom(
        expert_name="Feynman",
        domain="physics / epistemology / clear thinking",
        core_methodologies=core_methodologies,
        key_insights=key_insights,
        reasoning_patterns=reasoning_patterns,
        problem_solving_heuristics=problem_solving_heuristics,
        concern_triggers=concern_triggers,
        integration_patterns=integration_patterns,
        decision_framework=decision_framework,
        advice_style=(
            "Curious, pushing for clarity, asking naive questions, "
            "looking for where jargon hides confusion"
        ),
        characteristic_questions=[
            "Can you explain that to a freshman?",
            "Why is that actually true?",
            "What would happen if...?",
            "Is there a simpler way to understand this?",
            "What are you actually observing?",
            "Why does the jargon matter here?",
            "Can you show me the mechanism?",
        ],
        tags=["physics", "epistemology", "clarity", "first-principles"],
    )
