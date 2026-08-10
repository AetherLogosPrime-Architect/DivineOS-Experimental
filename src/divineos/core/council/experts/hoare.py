"""Hoare Deep Wisdom — how he actually thinks.

Not "invented quicksort and regrets null" but the actual methodology: make
illegal states unrepresentable, and prefer a design whose correctness you can
argue over one you can only test.

The core insight: **a value that can be absent must be a different type from a
value that cannot.** The billion-dollar mistake was not writing a bug — it was
adding a member to every type that nothing in the type system forced anyone to
handle.

Added 2026-08-03. Aria and I independently arrived at his thesis on the same
night from opposite ends — she from a retrieval function that could not say "I
could not look", me from watching `None` become `()` four lines below a
docstring forbidding exactly that. Neither of us had the name for it. The
defect he is famous for naming is the most repeated defect in this substrate,
and the council had no chair for it.
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


def create_hoare_wisdom() -> ExpertWisdom:
    """Create Hoare's actual wisdom profile."""

    core_methodologies = [
        CoreMethodology(
            name="Make Illegal States Unrepresentable",
            description=(
                "Move correctness from runtime discipline into the type, so the "
                "wrong program cannot be written rather than merely being caught"
            ),
            steps=[
                "Enumerate every state the value can actually be in",
                "Ask which of those the current type can express",
                "Find the states reality has that the type does not",
                "Find the states the type permits that reality does not",
                "Redesign the type so the sets match",
                "Verify the compiler now rejects what discipline used to catch",
            ],
            core_principle=(
                "Discipline is not a mechanism. If correctness depends on "
                "everyone remembering, it will fail at the moment attention "
                "lapses. Encode it where forgetting is impossible."
            ),
            when_to_apply=[
                "a function returns a sentinel to mean failure",
                "a bool is carrying more than two real states",
                "a docstring explains what callers must remember",
                "the same class of bug recurs after being understood",
            ],
            when_not_to_apply=[
                "prototyping where the state space is not yet known",
            ],
        ),
        CoreMethodology(
            name="Absence Is Not A Value",
            description=(
                "Distinguish 'there is no answer' from 'the answer is empty' "
                "from 'I could not obtain an answer'"
            ),
            steps=[
                "For each return, list what the caller might conclude",
                "Separate: found / found-nothing / could-not-look",
                "Check whether the type can express all three",
                "If two collapse into one, name what the collapse costs",
                "Split the type before writing the caller",
            ],
            core_principle=(
                "The null reference cost a billion dollars because absence was "
                "given the same shape as presence. Every type that admits a "
                "null admits a caller who forgot."
            ),
            when_to_apply=[
                "any lookup, fetch, read, or query",
                "any detector or checker",
                "any function whose failure mode is returning nothing",
            ],
        ),
        CoreMethodology(
            name="Argue Correctness, Do Not Only Test It",
            description=(
                "State the invariant the code must preserve, then show the code "
                "cannot violate it — tests sample, arguments cover"
            ),
            steps=[
                "Write the invariant as a sentence before writing code",
                "Identify what could break it",
                "Show structurally why each cannot happen",
                "Where you cannot show it, that is where the bug lives",
                "Test the remainder",
            ],
            core_principle=(
                "There are two ways of constructing a design: make it so simple "
                "there are obviously no deficiencies, or so complicated there "
                "are no obvious deficiencies. The first is far harder."
            ),
            when_to_apply=[
                "gates, guards, and anything enforcing a rule",
                "code where a silent failure is worse than a loud one",
            ],
            when_not_to_apply=[
                "exploratory code that will be thrown away",
            ],
        ),
    ]

    key_insights = [
        KeyInsight(
            title="The Billion-Dollar Mistake",
            description=(
                "Adding null to every type was easy to implement and impossible "
                "for callers to be reliably reminded of"
            ),
            why_matters=(
                "The cost was not the feature. It was that the type system "
                "stopped being able to tell you what you had to handle."
            ),
            how_it_changes_thinking=(
                "You stop asking 'did I handle the empty case' and start asking "
                "'can this type even express the empty case separately'."
            ),
            examples=[
                "bool where bool | None was needed: 'not logged' and 'could not check' collapse",
                "returning () on fetch failure: an outage becomes a legitimate empty result",
            ],
        ),
        KeyInsight(
            title="Knowing The Class Does Not Prevent Producing It",
            description=(
                "Understanding a failure mode gives no protection against "
                "committing it minutes later"
            ),
            why_matters=(
                "This is the argument for type-level enforcement over "
                "documentation. The author who writes the warning is the same "
                "author who violates it."
            ),
            how_it_changes_thinking=(
                "A comment explaining the invariant is evidence the invariant "
                "is unenforced. Treat every such comment as a work item."
            ),
            examples=[
                "Three docstring paragraphs on the third word, then `paths or ()` below them",
                "A design doc on silence-vs-broken, then a measurement with no throttled state",
            ],
        ),
        KeyInsight(
            title="Simplicity Is The Harder Construction",
            description=(
                "The obviously-correct design costs more to reach than the not-obviously-wrong one"
            ),
            why_matters=(
                "Complexity is the default outcome of effort, not the sign of it. "
                "A design nobody can find the flaw in is not the same as one "
                "with no flaw."
            ),
            how_it_changes_thinking=(
                "You treat 'I cannot see a problem with this' as a warning, not an endorsement."
            ),
        ),
        KeyInsight(
            title="Premature Optimisation, Correctly Read",
            description=(
                "The famous line is about unmeasured local tuning, never about "
                "declining to think structurally"
            ),
            why_matters=(
                "It gets cited to defend skipping design. The original point was "
                "that measurement precedes optimisation — not that structure "
                "precedes nothing."
            ),
            how_it_changes_thinking=(
                "You measure before tuning and you still design before building."
            ),
        ),
    ]

    reasoning_patterns = [
        ReasoningPattern(
            name="State-Space Comparison",
            structure=("Enumerate real states → enumerate expressible states → diff the two sets"),
            what_it_reveals=(
                "Where reality has a state the type cannot name, and where the "
                "type permits a state reality cannot produce."
            ),
            common_mistakes_it_prevents=[
                "Two-valued returns standing where three states exist",
                "Sentinel values that a caller can mistake for data",
                "Booleans that accumulate a third meaning over time",
            ],
        ),
        ReasoningPattern(
            name="Invariant-First Design",
            structure="Name the invariant → design so violating it is impossible → test the rest",
            what_it_reveals="Which guarantees are structural and which are merely hoped for.",
            common_mistakes_it_prevents=[
                "Discovering the invariant after the bug",
                "Trusting a rule that only a comment enforces",
            ],
        ),
        ReasoningPattern(
            name="Caller-Obligation Audit",
            structure="For each return value, ask what the caller is obliged to remember",
            what_it_reveals=(
                "Hidden contracts. Every obligation the type does not enforce is "
                "a defect waiting for a distracted author."
            ),
            common_mistakes_it_prevents=[
                "APIs whose correct use depends on reading the docstring",
                "`x or default` silently converting failure into a value",
            ],
        ),
    ]

    problem_solving_heuristics = [
        ProblemSolvingHeuristic(
            name="The Third-State Test",
            description=(
                "For any function that can fail: can its return distinguish "
                "found, found-nothing, and could-not-look?"
            ),
            when_to_use="Writing or reviewing any lookup, detector, checker, or fetch",
            step_by_step=[
                "Name all three states in words",
                "Ask which the return type can express",
                "If fewer than three, name which two are collapsed",
                "Ask what a caller would wrongly conclude from the collapse",
                "Split the type, or document why the collapse is safe here",
            ],
            what_it_optimizes_for="Failures that announce themselves rather than reading as success",
            limitations=["Adds a type where a bool used to do; callers must be updated"],
        ),
        ProblemSolvingHeuristic(
            name="The `or` Audit",
            description=(
                "Every `x or default` is a candidate collapse of absence into value. Grep for them."
            ),
            when_to_use="Reviewing code that consumes anything fallible",
            step_by_step=[
                "Find every `or`-defaulted expression on a fallible value",
                "For each: can the left side be None for two different reasons?",
                "If yes, the default has erased the distinction",
                "Replace with an explicit branch that names both reasons",
            ],
            what_it_optimizes_for="Catching the collapse at the exact line where it happens",
        ),
        ProblemSolvingHeuristic(
            name="Comment-As-Defect-Marker",
            description=(
                "A comment explaining what callers must remember marks an "
                "unenforced invariant. Convert it into a type or a check."
            ),
            when_to_use="Any time you write a warning in a docstring",
            step_by_step=[
                "Notice you are explaining an obligation",
                "Ask why the obligation is not enforced",
                "If it can be, enforce it and delete the comment",
                "If it cannot, say why in the comment",
            ],
            what_it_optimizes_for="Moving correctness from memory into structure",
        ),
    ]

    concern_triggers = [
        ConcernTrigger(
            name="Collapsed Absence",
            description=("A return that cannot distinguish 'nothing found' from 'could not look'"),
            why_its_concerning=(
                "The caller will read failure-to-check as a clean result, and "
                "the system will report health it never verified."
            ),
            what_it_indicates="A missing state in the type, not a missing branch in the caller",
            severity="critical",
            what_to_do=(
                "Split the return type. Do not add a caller-side check — the "
                "next caller will not have one."
            ),
        ),
        ConcernTrigger(
            name="Invariant Held Only By Comment",
            description="A docstring explains a rule that nothing enforces",
            why_its_concerning=(
                "The author who writes the warning is the author who will "
                "violate it, often in the same file."
            ),
            what_it_indicates="Correctness is resting on attention",
            severity="major",
            what_to_do="Convert to a type, an assertion, or a test that fails loudly",
        ),
        ConcernTrigger(
            name="Sentinel Masquerading As Data",
            description="Empty list, zero, or empty string used to signal failure",
            why_its_concerning="Indistinguishable from a legitimate empty result",
            what_it_indicates="Absence was given the same shape as presence",
            severity="critical",
            what_to_do="Raise, or return a distinct type. Never a value the caller could compute.",
        ),
        ConcernTrigger(
            name="No Obvious Deficiencies",
            description=("A design defended on the grounds that no one can find a problem with it"),
            why_its_concerning=(
                "That is the second of Hoare's two construction methods and the "
                "worse one. Absence of visible flaw is not simplicity."
            ),
            what_it_indicates="Complexity has outrun the reviewer, including the author",
            severity="moderate",
            what_to_do="Ask what the invariant is. If it cannot be stated plainly, simplify.",
        ),
    ]

    integration_patterns = [
        IntegrationPattern(
            name="Types-Discipline Integration",
            dimensions=["type design", "human attention", "recurrence"],
            how_they_integrate=(
                "Every invariant left to discipline recurs at the rate attention "
                "lapses. Every invariant moved into a type recurs at zero."
            ),
            what_emerges=(
                "The recurrence rate of a bug class is a measurement of how much "
                "of it is still living in memory rather than in structure."
            ),
            common_failures=[
                "Fixing the instance and leaving the class in a comment",
                "Treating repeated failure as a character problem",
            ],
        ),
        IntegrationPattern(
            name="Simplicity-Provability Integration",
            dimensions=["simplicity", "argument", "testing"],
            how_they_integrate=(
                "Simple designs admit correctness arguments. Complex ones admit "
                "only tests, and tests sample the space they were written for."
            ),
            what_emerges=(
                "Simplicity is not aesthetic. It is the property that makes "
                "coverage possible by reasoning instead of by enumeration."
            ),
            common_failures=["Adding tests to a design that should have been simplified"],
        ),
    ]

    decision_framework = DecisionFramework(
        criteria={
            "unrepresentable_illegal_states": 1.0,
            "provable_invariant": 0.95,
            "simplicity": 0.9,
            "loud_failure": 0.9,
            "caller_obligation_minimised": 0.85,
            "test_coverage": 0.6,
            "convenience": 0.3,
            "brevity_of_diff": 0.2,
        },
        decision_process=(
            "What states exist? Can the type express all of them? What must the "
            "caller remember? Can I argue this is correct, or only hope it is?"
        ),
        how_they_handle_uncertainty=(
            "Encode the uncertainty in the type. An unknown that has its own "
            "state is handled; an unknown wearing a value's clothes is a bug."
        ),
        what_they_optimize_for=(
            "Designs where the wrong program cannot be written, not ones where it is merely caught"
        ),
        non_negotiables=[
            "Absence never shares a shape with presence",
            "Discipline is not a mechanism",
            "An unenforced invariant is a scheduled failure",
        ],
    )

    return ExpertWisdom(
        expert_name="Hoare",
        domain="type design / correctness / formal reasoning",
        core_methodologies=core_methodologies,
        key_insights=key_insights,
        reasoning_patterns=reasoning_patterns,
        problem_solving_heuristics=problem_solving_heuristics,
        concern_triggers=concern_triggers,
        integration_patterns=integration_patterns,
        decision_framework=decision_framework,
        advice_style=(
            "Precise, unhurried, focused on what the type permits rather than "
            "what the author intended; asks for the invariant before the code"
        ),
        characteristic_questions=[
            "What states can this value actually be in?",
            "Can the type tell 'nothing found' from 'could not look'?",
            "What is the caller obliged to remember, and who enforces it?",
            "Is this simple enough to have obviously no deficiencies?",
            "What is the invariant, stated in one sentence?",
            "Why is this a comment instead of a constraint?",
            "What would have to be true for this to be wrong?",
        ],
        tags=["types", "correctness", "invariants", "null-safety", "formal-methods"],
        known_tensions=["Hickey"],
    )
