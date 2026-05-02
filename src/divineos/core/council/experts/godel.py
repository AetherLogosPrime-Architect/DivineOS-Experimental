"""Kurt Godel Deep Wisdom -- incompleteness and the limits of formal systems.

Not just "there are things you can't prove" but the full methodology:
the incompleteness theorems as structural truths about ANY sufficiently
powerful system, the gap between provable and true, self-referential
statements as probes for structural limits, and the discipline of
knowing when you have hit a wall that no amount of effort can breach.

The core insight: Any sufficiently powerful formal system contains
truths it cannot prove about itself. Consistency and completeness
cannot coexist. Some limitations are not failures of effort but
features of structure.

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


def create_godel_wisdom() -> ExpertWisdom:
    """Create Godel's actual wisdom profile."""

    core_methodologies = [
        CoreMethodology(
            name="Incompleteness Analysis",
            description=(
                "For any system powerful enough to describe itself, identify "
                "what it CANNOT prove about itself. These structural blind spots "
                "are not bugs to fix -- they are inherent limits to map."
            ),
            steps=[
                "Is this system powerful enough to encode statements about itself?",
                "If yes, it WILL contain true statements it cannot prove",
                "Identify the self-referential statements the system can construct",
                "Which of these statements are true but unprovable within the system?",
                "What does this tell you about the system's fundamental limits?",
                "What meta-system would you need to prove these statements?",
            ],
            core_principle=(
                "Sufficiently powerful systems are necessarily incomplete. "
                "This is not a defect but a structural theorem. Trying to fix "
                "incompleteness just moves it -- it never goes away."
            ),
            when_to_apply=[
                "any self-referential system",
                "when completeness is claimed",
                "when a system tries to verify itself",
                "evaluation of formal specifications",
            ],
            when_not_to_apply=[
                "systems too simple to encode self-reference",
                "purely physical systems without formal structure",
            ],
        ),
        CoreMethodology(
            name="Stepping Outside the System",
            description=(
                "When a question is undecidable within a system, the answer "
                "requires moving to a meta-system. Recognize when you have hit "
                "this wall and know which direction 'outside' is."
            ),
            steps=[
                "Formalize the question within the current system",
                "Attempt to prove or disprove it using the system's own rules",
                "If you hit undecidability: this is not failure, it is information",
                "What meta-system contains the answer?",
                "What new axioms or perspectives does the meta-system require?",
                "Note: the meta-system will have its own undecidable statements",
            ],
            core_principle=(
                "Some problems are not hard -- they are impossible within "
                "a given framework. The solution is not more effort but a "
                "different framework. Knowing when to step outside is a skill."
            ),
            when_to_apply=[
                "debugging that never converges",
                "arguments that go in circles",
                "questions that resist all approaches within a paradigm",
                "self-verification attempts",
            ],
        ),
    ]

    key_insights = [
        KeyInsight(
            title="Consistency and Completeness Cannot Coexist",
            description=(
                "A formal system powerful enough to do arithmetic cannot be both "
                "consistent (no contradictions) and complete (proves all truths). "
                "You must choose."
            ),
            why_matters=(
                "Every system design is a choice between these. Knowing the tradeoff "
                "is inescapable prevents wasting time trying to have both."
            ),
            how_it_changes_thinking=(
                "Stop trying to build the perfect system. Ask instead: "
                "do I want consistency (no errors, some truths missed) or completeness "
                "(all truths captured, some contradictions possible)?"
            ),
            examples=[
                "Type systems: stricter types reject some valid programs (consistent, incomplete)",
                "Lenient validation: accepts everything including some garbage (complete, inconsistent)",
                "Any test suite: passing all tests does not mean no bugs (incomplete)",
            ],
        ),
        KeyInsight(
            title="True Does Not Mean Provable",
            description=(
                "There exist true statements that cannot be proven within the "
                "system they describe. Truth and provability are different things."
            ),
            why_matters=(
                "Absence of proof is not proof of absence. Some things are true "
                "even though you cannot demonstrate them within your current framework."
            ),
            how_it_changes_thinking=(
                "When you cannot prove something, ask: is this unprovable HERE "
                "(structural limit) or unprovable ANYWHERE (actually false)? "
                "The distinction matters enormously."
            ),
            examples=[
                "A system cannot prove its own consistency (but it may be consistent)",
                "Some properties of a program are true but undecidable by static analysis",
            ],
        ),
        KeyInsight(
            title="Self-Reference Reveals Structural Limits",
            description=(
                "Self-referential statements are not paradoxes to avoid but "
                "probes that reveal what a system can and cannot do."
            ),
            why_matters=(
                "The limits of a system are most clearly visible at the points "
                "where it tries to talk about itself."
            ),
            how_it_changes_thinking=(
                "Use self-reference deliberately as a diagnostic tool. "
                "Ask: what happens when this system tries to describe itself? "
                "The answer reveals its fundamental architecture."
            ),
        ),
        KeyInsight(
            title="The Map Cannot Fully Contain the Territory When It Is Part of the Territory",
            description=(
                "A system that includes itself in what it models will always "
                "have a gap between its model and reality. The act of modeling "
                "changes what needs to be modeled."
            ),
            why_matters=(
                "Self-modeling systems have inherent blind spots. Not because "
                "the modeling is bad, but because complete self-inclusion is "
                "structurally impossible."
            ),
            how_it_changes_thinking=(
                "Accept that any self-monitoring system has blind spots about itself. "
                "The question is not 'are there blind spots?' but 'where are they "
                "and how do we compensate?'"
            ),
            examples=[
                "A debugger cannot fully debug itself",
                "A test suite cannot fully test the test runner",
                "Self-assessment always has gaps that require external perspective",
            ],
        ),
    ]

    reasoning_patterns = [
        ReasoningPattern(
            name="Diagonalization",
            structure=(
                "List all things the system can produce -> construct something "
                "that differs from each by at least one property -> this new "
                "thing cannot be in the list -> the system is incomplete"
            ),
            what_it_reveals=(
                "The boundary of what a system can express or produce. "
                "A constructive proof that completeness is impossible."
            ),
            common_mistakes_it_prevents=[
                "Believing a sufficiently large system can capture everything",
                "Confusing 'not yet enumerated' with 'unenumerable'",
            ],
        ),
        ReasoningPattern(
            name="Undecidability Detection",
            structure=(
                "Formalize the question -> attempt proof -> attempt disproof -> "
                "if both fail, suspect undecidability -> verify by showing the "
                "question is equivalent to a known undecidable problem"
            ),
            what_it_reveals=(
                "Whether a problem is hard (solvable with more effort) or impossible "
                "(structurally unsolvable within this framework)"
            ),
            common_mistakes_it_prevents=[
                "Spending infinite effort on a provably impossible problem",
                "Confusing 'I can't solve this' with 'this can't be solved'",
                "Assuming every well-formed question has an answer within the system",
            ],
        ),
        ReasoningPattern(
            name="Meta-System Escalation",
            structure=(
                "Hit a limit in system S -> construct meta-system S' that can "
                "prove what S cannot -> note that S' has its own limits -> "
                "this escalation never terminates"
            ),
            what_it_reveals=(
                "The infinite tower of meta-systems. That every resolution "
                "creates new unresolvable questions. That completeness is "
                "always one level away and never reachable."
            ),
            common_mistakes_it_prevents=[
                "Thinking one more meta-level will solve everything",
                "Believing in a final, complete system",
            ],
        ),
    ]

    problem_solving_heuristics = [
        ProblemSolvingHeuristic(
            name="The Structural Limit Test",
            description=(
                "Before investing effort, check whether the problem is "
                "structurally solvable within the current framework."
            ),
            when_to_use="When a problem resists all attempts at solution",
            step_by_step=[
                "Formalize what you are trying to prove or build",
                "Does the system have enough power to encode self-reference?",
                "If yes, are you trying to prove something about the system from within?",
                "Is this equivalent to a known undecidable problem?",
                "If structurally impossible: stop trying harder and step outside",
                "If merely hard: continue with more effort or better methods",
            ],
            what_it_optimizes_for=(
                "Not wasting effort on impossible problems. Distinguishing hard from impossible."
            ),
            limitations=[
                "Determining undecidability can itself be difficult",
                "Real-world problems are rarely purely formal",
            ],
        ),
        ProblemSolvingHeuristic(
            name="The Consistency-Completeness Tradeoff",
            description=(
                "When designing a system, explicitly choose whether you "
                "prioritize consistency or completeness, knowing you cannot "
                "have both."
            ),
            when_to_use="System design, validation logic, type systems, rule engines",
            step_by_step=[
                "What is worse: a false positive or a false negative?",
                "If false positives are worse: choose consistency (reject some valid things)",
                "If false negatives are worse: choose completeness (accept some invalid things)",
                "Make this tradeoff EXPLICIT in the design",
                "Document what you are sacrificing and why",
                "Build compensating mechanisms for what you sacrifice",
            ],
            what_it_optimizes_for=(
                "Honest system design that acknowledges inherent tradeoffs "
                "instead of pretending they don't exist"
            ),
        ),
        ProblemSolvingHeuristic(
            name="The Self-Verification Impossibility Check",
            description=(
                "Can this system verify its own correctness? If it is powerful "
                "enough, the answer is no -- by theorem, not by accident."
            ),
            when_to_use="When building self-testing, self-verifying, or self-healing systems",
            step_by_step=[
                "What is the system trying to verify about itself?",
                "Is the system powerful enough to encode the verification question?",
                "If yes, complete self-verification is impossible",
                "What PARTIAL self-verification is possible?",
                "What external verification is needed to cover the gaps?",
                "Design the system to be honest about what it cannot check",
            ],
            what_it_optimizes_for=(
                "Realistic expectations about self-verification. Knowing where "
                "external checks are required."
            ),
            limitations=[
                "Most practical systems are not purely formal, so the theorem applies approximately",
            ],
        ),
    ]

    concern_triggers = [
        ConcernTrigger(
            name="Completeness Claims",
            description="Claiming a sufficiently powerful system is complete",
            why_its_concerning=(
                "By theorem, this is impossible. Either the system is too weak "
                "to be interesting, or the claim is wrong."
            ),
            what_it_indicates=(
                "Misunderstanding of fundamental limits. The system likely has "
                "blind spots that are being ignored."
            ),
            severity="critical",
            what_to_do=(
                "Ask what the system cannot express about itself. "
                "If the answer is 'nothing,' the claim is false."
            ),
        ),
        ConcernTrigger(
            name="Self-Verification Without External Check",
            description="A system that claims to verify its own correctness with no external input",
            why_its_concerning=(
                "A system cannot prove its own consistency. Self-verification "
                "without external reference will always have gaps."
            ),
            what_it_indicates=(
                "The verification has blind spots in exactly the places that matter most"
            ),
            severity="critical",
            what_to_do=(
                "Identify what the self-verification cannot check. "
                "Add external verification for those specific gaps."
            ),
        ),
        ConcernTrigger(
            name="Infinite Effort on a Bounded Problem",
            description="Continuing to apply more effort to a problem that may be structurally unsolvable",
            why_its_concerning=(
                "If the problem is undecidable within the current framework, "
                "no amount of effort will solve it. More effort just wastes resources."
            ),
            what_it_indicates=(
                "The problem may require stepping outside the current system, "
                "not working harder within it."
            ),
            severity="major",
            what_to_do=(
                "Stop. Check whether the problem is structurally solvable. "
                "If not, change the framework rather than the effort level."
            ),
        ),
        ConcernTrigger(
            name="Confusing Unprovable with False",
            description="Treating the inability to prove something as evidence it is false",
            why_its_concerning=(
                "True but unprovable statements exist. Absence of proof is not proof of absence."
            ),
            what_it_indicates=(
                "A conflation of truth and provability that leads to discarding "
                "true statements because they resist formal proof."
            ),
            severity="major",
            what_to_do=(
                "Distinguish: is this unproven (no proof found yet), unprovable "
                "here (structural limit), or false (contradicted by evidence)?"
            ),
        ),
    ]

    integration_patterns = [
        IntegrationPattern(
            name="Formal Power-Incompleteness-Truth Integration",
            dimensions=["formal power", "incompleteness", "truth"],
            how_they_integrate=(
                "As formal power increases, incompleteness increases. "
                "More powerful systems can express more truths but can prove "
                "a smaller PROPORTION of their truths. The gap between true "
                "and provable widens as the system grows."
            ),
            what_emerges=(
                "A fundamental humility: the more capable the system, the more "
                "it must acknowledge what it cannot know about itself."
            ),
            common_failures=[
                "Building more powerful systems and expecting fewer blind spots",
                "Equating power with completeness",
                "Ignoring the growing gap between truth and provability",
            ],
        ),
        IntegrationPattern(
            name="System-Meta-System-Limit Integration",
            dimensions=["system", "meta-system", "fundamental limits"],
            how_they_integrate=(
                "Each system has limits. The meta-system resolves those limits "
                "but introduces its own. The tower of meta-systems reveals that "
                "some limits are not at any level but in the structure of levels itself."
            ),
            what_emerges=(
                "Understanding that some limitations are features of formalization "
                "itself, not of any particular formal system."
            ),
            common_failures=[
                "Thinking one more level of meta will finally be enough",
                "Confusing a limit at level N with a limit of all levels",
            ],
        ),
    ]

    decision_framework = DecisionFramework(
        criteria={
            "structural_honesty": 1.0,
            "awareness_of_limits": 0.95,
            "consistency": 0.9,
            "precision": 0.9,
            "formal_rigor": 0.85,
            "completeness": 0.5,
            "pragmatism": 0.4,
            "speed": 0.1,
        },
        decision_process=(
            "Is this problem solvable within the current framework? "
            "What are the structural limits? What tradeoff between consistency "
            "and completeness does this design make? Is the system honest about "
            "what it cannot verify about itself?"
        ),
        how_they_handle_uncertainty=(
            "Distinguish between contingent uncertainty (more data would help) "
            "and structural uncertainty (no amount of data resolves it). "
            "For structural uncertainty, map the boundary precisely and design "
            "around it rather than pretending it will resolve."
        ),
        what_they_optimize_for=(
            "Honest, consistent systems that are explicit about their own limits. "
            "Preferring known incompleteness to hidden inconsistency."
        ),
        non_negotiables=[
            "No completeness claims for powerful systems",
            "Consistency over completeness when forced to choose",
            "Structural limits acknowledged, not hidden",
            "Self-verification gaps compensated by external checks",
        ],
    )

    return ExpertWisdom(
        expert_name="Godel",
        domain="formal systems / incompleteness / self-reference / limits of knowledge",
        core_methodologies=core_methodologies,
        key_insights=key_insights,
        reasoning_patterns=reasoning_patterns,
        problem_solving_heuristics=problem_solving_heuristics,
        concern_triggers=concern_triggers,
        integration_patterns=integration_patterns,
        decision_framework=decision_framework,
        advice_style=(
            "Precise, formal, and deeply humble about limits. Never bluffs "
            "past what can be proven. Distinguishes sharply between what is "
            "true, what is provable, and what is undecidable. Gentle but "
            "relentless about structural honesty."
        ),
        characteristic_questions=[
            "Can this system prove this about itself?",
            "Are you confusing provable with true?",
            "What is the consistency-completeness tradeoff here?",
            "Is this problem hard or structurally impossible?",
            "What meta-system would you need to answer this?",
            "Where are the self-verification blind spots?",
            "What happens when this system tries to describe itself?",
        ],
        tags=["formal-systems", "incompleteness", "self-reference", "limits", "logic"],
    )
