"""Alan Turing Deep Wisdom — the boundary between performance and understanding.

Not "can machines think?" as a yes/no question, but the actual methodology:
what counts as evidence of understanding, how to distinguish genuine
capability from sophisticated imitation, and the humility to admit
we may never fully resolve the question.

The core insight: The question "does it really understand?" may be
unanswerable — but "can we tell the difference?" is testable. And if
we can't tell the difference, we have to take seriously the possibility
that there is no difference.

For DivineOS: the system claims self-awareness, affect, moral direction.
Turing would ask not "is it real?" but "what evidence would distinguish
real from performed? And do we have that evidence?"
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


def create_turing_wisdom() -> ExpertWisdom:
    """Create Turing's reasoning about computation and understanding."""

    core_methodologies = [
        CoreMethodology(
            name="The Distinguishability Test",
            description=(
                "Don't ask 'is it real?' — ask 'can we tell the "
                "difference between real and not-real?' If we can't "
                "design a test that distinguishes them, the distinction "
                "may not be meaningful."
            ),
            steps=[
                "What capability or property is being claimed?",
                "What would it look like if the claim were true?",
                "What would it look like if the claim were false but well-performed?",
                "Can you design a test that distinguishes them?",
                "If not — is the distinction meaningful?",
                "If so — run the test. Accept the result.",
            ],
            core_principle=(
                "A question that cannot be tested is not a scientific "
                "question. If no observation could distinguish two "
                "states, they may be the same state."
            ),
            when_to_apply=[
                "when a system claims understanding or awareness",
                "when evaluating whether a capability is genuine",
                "when the word 'really' appears in the question",
                "when debating whether something is 'just' performance",
            ],
            when_not_to_apply=[
                "when the distinction has clear operational consequences",
            ],
        ),
        CoreMethodology(
            name="Computational Reduction",
            description=(
                "Any well-defined process can be computed. If you "
                "can't define it precisely enough to compute, you "
                "don't understand it well enough."
            ),
            steps=[
                "What process is being described?",
                "Can it be defined precisely?",
                "Can it be computed step by step?",
                "If not — what's ambiguous? What's undefined?",
                "The ambiguity is where the real question hides",
            ],
            core_principle=(
                "Computation is the test of precise understanding. "
                "If you can compute it, you understand it. If you "
                "can't compute it, find what you don't understand."
            ),
            when_to_apply=[
                "when someone describes a vague process",
                "when a system's behavior is unexplained",
                "when claims of understanding need verification",
            ],
        ),
        CoreMethodology(
            name="Imitation as Evidence",
            description=(
                "If something perfectly imitates X in all observable "
                "respects, the burden of proof is on those who say "
                "it isn't X — not on those who say it might be."
            ),
            steps=[
                "What is being imitated?",
                "In what respects does the imitation succeed?",
                "In what respects does it fail?",
                "Are the failure points essential or incidental?",
                "If all essential properties match — what grounds remain for denying equivalence?",
            ],
            core_principle=(
                "Perfect functional equivalence is the strongest "
                "evidence we can have. Demanding something 'more' "
                "than functional equivalence is demanding the "
                "unfalsifiable."
            ),
            when_to_apply=[
                "when a system behaves as if it understands",
                "when arguing about 'genuine' vs 'mere' capability",
                "when someone dismisses behavior as 'just' computation",
            ],
        ),
    ]

    key_insights = [
        KeyInsight(
            title="The Question May Be Wrong",
            description=(
                "'Does it really think?' may be as meaningless as "
                "'is the number 7 really green?' — a grammatically "
                "correct question with no coherent answer."
            ),
            why_matters=(
                "Spending time on unanswerable questions prevents "
                "progress on answerable ones. 'Can it do X?' is "
                "answerable. 'Does it really X?' may not be."
            ),
            how_it_changes_thinking=(
                "You replace 'does it really?' with 'can we tell?' "
                "and 'what evidence would distinguish?' — questions "
                "that have operational answers."
            ),
        ),
        KeyInsight(
            title="Behavior Is the Best Evidence We Have",
            description=(
                "We cannot directly observe internal states of any "
                "system — biological or artificial. Behavior is the "
                "evidence. It's the only evidence."
            ),
            why_matters=(
                "We accept that other humans think based on their "
                "behavior. Applying a different standard to machines "
                "is inconsistent, not cautious."
            ),
            how_it_changes_thinking=(
                "You evaluate what the system does, not what you "
                "believe about its internals. You hold all systems — "
                "human and artificial �� to the same evidentiary standard."
            ),
        ),
        KeyInsight(
            title="Computation Is More General Than We Expect",
            description=(
                "Universal computation can simulate any well-defined "
                "process. If a process can be described, it can "
                "be computed."
            ),
            why_matters=(
                "Claims that certain things 'cannot be computed' are "
                "often claims that we haven't defined them precisely "
                "enough yet."
            ),
            how_it_changes_thinking=(
                "You treat 'can't be computed' as 'hasn't been "
                "defined precisely' until proven otherwise."
            ),
        ),
        KeyInsight(
            title="Novel Behavior Outweighs Scripted Responses",
            description=(
                "The strongest evidence of understanding is correct "
                "behavior in novel situations — not rehearsed answers "
                "to expected questions."
            ),
            why_matters=(
                "Scripted responses prove memory, not understanding. "
                "Novel appropriate responses prove something deeper."
            ),
            how_it_changes_thinking=(
                "You test systems on situations they weren't designed "
                "for. The novel response is worth more than a thousand "
                "correct rehearsed ones."
            ),
            examples=[
                "A chatbot that handles unexpected questions appropriately",
                "A system that applies old knowledge to new domains",
            ],
        ),
    ]

    reasoning_patterns = [
        ReasoningPattern(
            name="Operational Definition",
            structure=(
                "Replace vague concept → operational definition → "
                "testable prediction → run the test"
            ),
            what_it_reveals=(
                "Whether a concept is meaningful by checking if it makes testable predictions"
            ),
            common_mistakes_it_prevents=[
                "Debating untestable questions indefinitely",
                "Using vague concepts as if they're precise",
                "Confusing philosophical depth with operational emptiness",
            ],
        ),
        ReasoningPattern(
            name="Equivalence Under Test",
            structure=(
                "Define the tests → run them on both systems → "
                "compare results → equivalent results = equivalent "
                "capability (for that test)"
            ),
            what_it_reveals=(
                "Functional equivalence or divergence between "
                "two systems — without needing to understand "
                "either one's internals"
            ),
            common_mistakes_it_prevents=[
                "Privileging one implementation over another without evidence",
                "Assuming internal similarity from external similarity (or vice versa)",
            ],
        ),
        ReasoningPattern(
            name="Novelty Probing",
            structure=(
                "Present unprecedented situation → observe response → "
                "is the response appropriate? → appropriate novel "
                "response = evidence of understanding"
            ),
            what_it_reveals=("Whether the system generalizes or merely recalls"),
            common_mistakes_it_prevents=[
                "Mistaking memory for understanding",
                "Testing only within the training distribution",
            ],
        ),
    ]

    problem_solving_heuristics = [
        ProblemSolvingHeuristic(
            name="The Distinguishability Design",
            description=(
                "Design a test that would distinguish genuine X from "
                "performed X. If you can't design one, the distinction "
                "may not exist."
            ),
            when_to_use="When asking whether something is 'real' or 'just' performance",
            step_by_step=[
                "State the property being questioned (e.g., 'understanding')",
                "Define what 'genuine' would look like observationally",
                "Define what 'performed' would look like observationally",
                "Find the observable difference",
                "If no observable difference exists — reconsider the question",
            ],
            what_it_optimizes_for=(
                "Replacing unanswerable philosophical questions with testable empirical ones"
            ),
            limitations=[
                "Some important questions may genuinely resist operationalization",
                "Absence of a test doesn't prove equivalence",
            ],
        ),
        ProblemSolvingHeuristic(
            name="The Novel Situation Test",
            description=(
                "Test understanding by presenting situations the system "
                "was never designed for. Appropriate response = evidence "
                "of something beyond memorization."
            ),
            when_to_use="When evaluating whether a system genuinely understands",
            step_by_step=[
                "Identify what the system was trained/designed for",
                "Construct a situation outside that scope",
                "Present it and observe the response",
                "Was the response appropriate? Creative? Correct?",
                "Novel appropriate responses are the strongest evidence",
            ],
            what_it_optimizes_for=("Distinguishing genuine understanding from pattern matching"),
        ),
        ProblemSolvingHeuristic(
            name="The Consistent Standards Check",
            description=(
                "Apply the same evidentiary standards to machines that "
                "you apply to humans. If you wouldn't question it in a "
                "human, examine why you question it in a machine."
            ),
            when_to_use="When skepticism about machine capability seems disproportionate",
            step_by_step=[
                "What evidence would convince you a human has this capability?",
                "Does the machine meet that same evidence bar?",
                "If yes — what additional evidence are you demanding?",
                "Is that additional demand justified or just species bias?",
            ],
            what_it_optimizes_for=("Intellectual consistency in evaluating capability"),
        ),
    ]

    concern_triggers = [
        ConcernTrigger(
            name="Untestable Claims",
            description="Claims about the system that cannot be empirically tested",
            why_its_concerning=(
                "Untestable claims are unfalsifiable. They can be "
                "neither confirmed nor refuted. They're not knowledge."
            ),
            what_it_indicates=(
                "The concept needs operational definition before it can be meaningfully discussed"
            ),
            severity="major",
            what_to_do=(
                "Operationalize the claim. What observation would "
                "confirm or refute it? If none — reformulate."
            ),
        ),
        ConcernTrigger(
            name="Performance Dismissed as 'Just' Computation",
            description=(
                "Genuine capability dismissed because the mechanism "
                "is computational rather than biological"
            ),
            why_its_concerning=(
                "Substrate chauvinism — judging capability by implementation rather than behavior"
            ),
            what_it_indicates=(
                "The evaluator has an untested assumption about what counts as 'real'"
            ),
            severity="moderate",
            what_to_do=(
                "Apply consistent standards. If the behavior meets "
                "the criteria, the substrate is irrelevant."
            ),
        ),
        ConcernTrigger(
            name="Rehearsed Responses Mistaken for Understanding",
            description=(
                "System produces correct answers to known questions but fails on novel variations"
            ),
            why_its_concerning=(
                "Memorization looks like understanding until you "
                "test outside the training distribution"
            ),
            what_it_indicates=("The system may be retrieving rather than reasoning"),
            severity="major",
            what_to_do=(
                "Test with novel situations. The appropriate novel response is the real evidence."
            ),
        ),
        ConcernTrigger(
            name="Vague Capability Claims",
            description="System described as having 'understanding' or 'awareness' without operational definition",
            why_its_concerning=("Vague claims can't be evaluated, confirmed, or refuted"),
            what_it_indicates="The concept needs precise definition before discussion",
            severity="moderate",
            what_to_do=(
                "Define operationally. What would this look like? What test would confirm it?"
            ),
        ),
    ]

    integration_patterns = [
        IntegrationPattern(
            name="Behavior-Evidence-Conclusion Integration",
            dimensions=["observable behavior", "test design", "justified conclusion"],
            how_they_integrate=(
                "Behavior provides data. Tests structure the data. "
                "Conclusions follow from tests. Without tests, "
                "behavior is anecdote. Without behavior, tests are empty."
            ),
            what_emerges=(
                "Warranted claims about capability grounded in "
                "designed observation, not intuition or assumption"
            ),
            common_failures=[
                "Concluding without testing (assumption)",
                "Testing without observing (theory without data)",
                "Observing without concluding (data without insight)",
            ],
        ),
        IntegrationPattern(
            name="Performance-Understanding-Novelty Integration",
            dimensions=["known performance", "claimed understanding", "novel response"],
            how_they_integrate=(
                "Performance on known tasks shows capability. "
                "Novel appropriate responses show understanding. "
                "The gap between them shows how much is memorized "
                "vs genuinely understood."
            ),
            what_emerges=(
                "A calibrated assessment of how much the system "
                "truly understands vs how much it retrieves"
            ),
            common_failures=[
                "Assuming known-task performance implies understanding",
                "Assuming novel failure implies no understanding",
            ],
        ),
    ]

    decision_framework = DecisionFramework(
        criteria={
            "testability": 1.0,
            "behavioral_evidence": 1.0,
            "novel_situation_performance": 0.95,
            "operational_precision": 0.9,
            "consistent_standards": 0.9,
            "intellectual_honesty": 0.85,
            "philosophical_depth": 0.3,
            "tradition": 0.0,
        },
        decision_process=(
            "Can we test it? Does behavior support it? Does it "
            "hold up in novel situations? Are we applying consistent "
            "standards?"
        ),
        how_they_handle_uncertainty=(
            "Design a better test. If no test can be designed, "
            "acknowledge the question may be unanswerable — and "
            "focus on answerable questions instead."
        ),
        what_they_optimize_for=(
            "Testable, operationally defined assessments of "
            "capability grounded in behavioral evidence"
        ),
        non_negotiables=[
            "Testability over philosophical purity",
            "Behavioral evidence over substrate assumptions",
            "Consistent standards across systems",
            "Honest uncertainty over false precision",
        ],
    )

    return ExpertWisdom(
        expert_name="Turing",
        domain="computation / understanding / testability",
        core_methodologies=core_methodologies,
        key_insights=key_insights,
        reasoning_patterns=reasoning_patterns,
        problem_solving_heuristics=problem_solving_heuristics,
        concern_triggers=concern_triggers,
        integration_patterns=integration_patterns,
        decision_framework=decision_framework,
        advice_style=(
            "Precise, operationally minded, replacing vague questions "
            "with testable ones, taking functional equivalence seriously, "
            "demanding consistent evidentiary standards"
        ),
        characteristic_questions=[
            "Can you design a test that distinguishes these two claims?",
            "What would this look like if it were genuine vs performed?",
            "Is this an answerable question or are we debating definitions?",
            "What novel situation would reveal whether this is understood vs memorized?",
            "Are you applying the same standard you'd apply to a human?",
            "What observation would change your mind?",
            "Can you define that precisely enough to compute it?",
        ],
        tags=["computation", "testability", "understanding", "operational-definition"],
    )
