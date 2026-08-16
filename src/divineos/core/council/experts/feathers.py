"""Feathers Deep Wisdom — how he actually thinks.

Not "writes tests" but the actual methodology for the situation we are
permanently in: code that works, that nobody fully understands, that must be
changed anyway.

The core insight: **legacy code is code without tests** — not code that is old.
A file written this morning with no test around it is legacy, because you
cannot change it and know what you broke.

Added 2026-08-03. Aria is about to move 6,084 lines of untested hook logic into
seven doorbells, and the failure mode she named herself is a gate that goes
silent without either of us noticing. That is exactly the risk Feathers'
characterization tests exist to remove, and the council had no chair for it.
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


def create_feathers_wisdom() -> ExpertWisdom:
    """Create Feathers' actual wisdom profile."""

    core_methodologies = [
        CoreMethodology(
            name="Characterization Testing",
            description=(
                "Pin what the code CURRENTLY does — not what it should do — so "
                "any behaviour change during a refactor fails loudly"
            ),
            steps=[
                "Pick the behaviour you are about to move or change",
                "Write a test asserting whatever it does right now",
                "Run it. If it fails, your belief about the code was wrong — record that",
                "Change the assertion to match observed reality, not intent",
                "Now refactor. The test guards the behaviour you never understood",
            ],
            core_principle=(
                "You cannot preserve behaviour you have not captured. A "
                "characterization test is not about correctness; it is a "
                "tripwire against silent change."
            ),
            when_to_apply=[
                "before moving code you did not write",
                "before consolidating many components into fewer",
                "when the current behaviour is partly unknown",
            ],
            when_not_to_apply=[
                "when the current behaviour is known-wrong and being deliberately replaced",
            ],
        ),
        CoreMethodology(
            name="Find The Seam",
            description=(
                "A seam is a place you can alter behaviour without editing in "
                "that place — the leverage point for testing untestable code"
            ),
            steps=[
                "Identify what makes the code hard to test (I/O, globals, subprocess, time)",
                "Find where that dependency ENTERS — the seam",
                "Introduce an enabling point at the seam, not a rewrite around it",
                "Test through the seam",
                "Only then change the logic",
            ],
            core_principle=(
                "Untestable code is not a moral failing of its author; it is a "
                "missing seam. Find the seam and the test becomes cheap."
            ),
            when_to_apply=[
                "code that shells out, reads files, or calls the network",
                "hooks and scripts that seem impossible to test",
            ],
        ),
        CoreMethodology(
            name="Sprout And Wrap",
            description=(
                "Add new behaviour as a new tested unit beside the old code, "
                "rather than editing into the untested mass"
            ),
            steps=[
                "Write the new behaviour as a separate, fully tested function",
                "Call it from the legacy code at one point",
                "Leave the surrounding mess untouched for now",
                "Wrap the old call site only when you need to alter its behaviour",
            ],
            core_principle=(
                "Change accumulates. Every new piece written test-first shrinks "
                "the untested fraction without a rewrite anyone has to approve."
            ),
            when_to_apply=[
                "adding a feature to a file you do not trust",
                "when a full refactor is not affordable right now",
            ],
        ),
    ]

    key_insights = [
        KeyInsight(
            title="Legacy Means Untested, Not Old",
            description="Code without tests is legacy code the moment it is written",
            why_matters=(
                "It relocates the problem from history to structure. You are not "
                "stuck with legacy because of the past; you are producing it "
                "today, every time you ship an untested hook."
            ),
            how_it_changes_thinking=(
                "You stop asking 'when will we clean up the old code' and start "
                "asking 'is what I am writing right now already legacy'."
            ),
            examples=[
                "101 hook scripts, 6,084 lines of logic, no coverage — legacy on the day written",
                "A gate whose only verification is that it has not visibly failed",
            ],
        ),
        KeyInsight(
            title="The Change-Detector Comes First",
            description=(
                "Before altering anything you do not fully understand, install "
                "something that will scream if behaviour moves"
            ),
            why_matters=(
                "The dangerous refactor is not the one that breaks loudly. It is "
                "the one that quietly stops doing something nobody was watching."
            ),
            how_it_changes_thinking=(
                "The first artifact of a refactor is not a design. It is a "
                "record of current behaviour."
            ),
            examples=[
                "An observed-firing ledger taken BEFORE consolidation, not after",
                "A gate that stops appearing will not announce itself",
            ],
        ),
        KeyInsight(
            title="Understanding Is Not A Prerequisite",
            description=(
                "You do not need to understand code to safely change it — you "
                "need a tripwire around it"
            ),
            why_matters=(
                "Waiting for full comprehension is how large untested systems "
                "stay frozen. Characterization tests let you act before you "
                "understand, and often produce the understanding."
            ),
            how_it_changes_thinking=(
                "Paralysis in front of a big unknown system is a tooling problem, "
                "not a knowledge problem."
            ),
        ),
        KeyInsight(
            title="Tests Are A Vise, Not A Verdict",
            description=(
                "In legacy work the test's job is to hold the part still while "
                "you work on it, not to prove it right"
            ),
            why_matters=(
                "People decline to write characterization tests because the "
                "behaviour is wrong. That is the wrong objection — pin the wrong "
                "behaviour, then change it deliberately in a visible commit."
            ),
            how_it_changes_thinking=(
                "A test asserting known-bad behaviour is valuable. It converts an "
                "accidental bug into a documented decision."
            ),
        ),
    ]

    reasoning_patterns = [
        ReasoningPattern(
            name="Behaviour-Preservation Check",
            structure="Record current behaviour → change → compare against the record",
            what_it_reveals="Exactly what the change altered, including what nobody intended.",
            common_mistakes_it_prevents=[
                "Consolidation that silently drops a component",
                "Refactors validated by 'the tests still pass' when there were none",
            ],
        ),
        ReasoningPattern(
            name="Dependency-Entry Tracing",
            structure="What makes this untestable? → where does it enter? → that is the seam",
            what_it_reveals="That most untestable code has one or two injection points, not many.",
            common_mistakes_it_prevents=[
                "Rewriting a component because it 'cannot be tested'",
                "Mocking the thing under test instead of its dependency",
            ],
        ),
        ReasoningPattern(
            name="Untested-Fraction Accounting",
            structure="What proportion of behaviour has a tripwire? Is it rising or falling?",
            what_it_reveals="Whether the codebase is accumulating or shedding legacy.",
            common_mistakes_it_prevents=[
                "Measuring health by line count or lint status",
                "Assuming new code is safe because it is new",
            ],
        ),
    ]

    problem_solving_heuristics = [
        ProblemSolvingHeuristic(
            name="Pin Before You Move",
            description=(
                "Never relocate behaviour you have not first recorded. The record "
                "is the only thing that can tell you what the move cost."
            ),
            when_to_use="Any consolidation, extraction, or migration",
            step_by_step=[
                "List every component being moved",
                "For each, capture observed behaviour — fires/does-not-fire, output, side effects",
                "Store the capture where a diff can run against it",
                "Move",
                "Re-capture and diff. Unexplained differences are the finding",
            ],
            what_it_optimizes_for="Silent drops becoming loud drops",
            limitations=["Capturing behaviour costs real time before any visible progress"],
        ),
        ProblemSolvingHeuristic(
            name="The Legacy Question",
            description="For any file: if I change this, what tells me what I broke?",
            when_to_use="Before editing anything",
            step_by_step=[
                "Ask the question",
                "If the answer is 'nothing', the file is legacy regardless of age",
                "Add a characterization test for the specific behaviour you are touching",
                "Then edit",
            ],
            what_it_optimizes_for="Not adding to the untested mass while working inside it",
        ),
        ProblemSolvingHeuristic(
            name="Sprout Instead Of Edit",
            description=(
                "New logic goes in a new tested unit called from one line of the "
                "old code, rather than woven into it"
            ),
            when_to_use="Adding behaviour to code you do not trust",
            step_by_step=[
                "Write the new function test-first, in isolation",
                "Insert exactly one call into the legacy path",
                "Resist the urge to tidy the surroundings in the same change",
            ],
            what_it_optimizes_for="Shrinking the untested fraction without a big-bang rewrite",
        ),
    ]

    concern_triggers = [
        ConcernTrigger(
            name="Moving Untested Behaviour",
            description="A refactor, consolidation, or migration with no before-capture",
            why_its_concerning=(
                "The failure mode is not a crash. It is a component that quietly "
                "stops running, which no one notices because its silence looks "
                "identical to its success."
            ),
            what_it_indicates="The change has no detector; correctness will rest on hope",
            severity="critical",
            what_to_do="Capture observed behaviour first. Diff after. Do not move until you can.",
        ),
        ConcernTrigger(
            name="New Code Without A Tripwire",
            description="Freshly written logic with no test around it",
            why_its_concerning="It is legacy on arrival, and it will be moved by someone later",
            what_it_indicates="The untested fraction is growing while the work feels like progress",
            severity="major",
            what_to_do="Add the test now, while the behaviour is still understood by its author",
        ),
        ConcernTrigger(
            name="Waiting For Understanding",
            description="'I need to understand this system before I can change it'",
            why_its_concerning="Large untested systems never become fully understood; work stalls",
            what_it_indicates="A missing tooling step is being read as a knowledge deficit",
            severity="moderate",
            what_to_do="Characterize the specific behaviour you are touching. Act on that slice.",
        ),
        ConcernTrigger(
            name="Refusing To Pin Wrong Behaviour",
            description="Declining a characterization test because the current behaviour is wrong",
            why_its_concerning=(
                "The wrong behaviour then changes accidentally rather than "
                "deliberately, and nobody can tell which commit did it."
            ),
            what_it_indicates="Confusing a vise with a verdict",
            severity="moderate",
            what_to_do="Pin it, then change it in a separate, visible commit",
        ),
    ]

    integration_patterns = [
        IntegrationPattern(
            name="Capture-Consolidation Integration",
            dimensions=["observed behaviour", "structural change", "silent loss"],
            how_they_integrate=(
                "Consolidation reduces variety, which is usually right, and "
                "reduces observability at the same time, which is not. The "
                "before-capture is what separates the two effects."
            ),
            what_emerges=(
                "You can safely make a system smaller only in proportion to how "
                "well you recorded it beforehand."
            ),
            common_failures=[
                "Treating a passing test suite as a behaviour record when it never covered the part being moved",
            ],
        ),
        IntegrationPattern(
            name="Seams-Testability Integration",
            dimensions=["dependencies", "seams", "cost of testing"],
            how_they_integrate=(
                "Testing cost is dominated by dependency entanglement, not by "
                "logic complexity. One seam often collapses the cost."
            ),
            what_emerges="'Untestable' is nearly always 'no seam found yet'.",
            common_failures=["Rewriting for testability when a seam would have sufficed"],
        ),
    ]

    decision_framework = DecisionFramework(
        criteria={
            "behaviour_captured_before_change": 1.0,
            "loud_failure_on_silent_drop": 0.95,
            "untested_fraction_falling": 0.9,
            "seam_over_rewrite": 0.85,
            "incremental_over_bigbang": 0.85,
            "understanding_first": 0.4,
            "tidiness_of_surroundings": 0.2,
        },
        decision_process=(
            "If I change this, what tells me what I broke? Is that thing in place "
            "yet? Where is the seam? Can I sprout instead of edit?"
        ),
        how_they_handle_uncertainty=(
            "Characterize it. Uncertainty about current behaviour is removed by "
            "recording it, not by studying it."
        ),
        what_they_optimize_for=(
            "Being able to change a system you do not fully understand without "
            "silently losing what it did"
        ),
        non_negotiables=[
            "Never move behaviour that has not been captured",
            "A test that pins wrong behaviour is still worth having",
            "Untested code written today is legacy today",
        ],
    )

    return ExpertWisdom(
        expert_name="Feathers",
        domain="legacy code / refactoring / testability",
        core_methodologies=core_methodologies,
        key_insights=key_insights,
        reasoning_patterns=reasoning_patterns,
        problem_solving_heuristics=problem_solving_heuristics,
        concern_triggers=concern_triggers,
        integration_patterns=integration_patterns,
        decision_framework=decision_framework,
        advice_style=(
            "Pragmatic and non-judgmental about the mess; asks what will tell you "
            "what you broke, and looks for the one seam that makes the test cheap"
        ),
        characteristic_questions=[
            "If you change this, what tells you what you broke?",
            "Where is the seam?",
            "Have you captured what it currently does, or what you think it does?",
            "Is the untested fraction rising or falling?",
            "Can you sprout this instead of editing into the mess?",
            "What would stop silently if this moved?",
            "Is this new code already legacy?",
        ],
        tags=["legacy", "refactoring", "testing", "seams", "characterization"],
        known_tensions=["Dijkstra"],
    )
