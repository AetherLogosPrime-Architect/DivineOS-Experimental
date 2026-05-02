"""Polya Deep Wisdom — how he actually thinks.

Not "knows about problem solving" but the actual methodology of
working backward from the answer, checking your solution against the
problem, and the discipline of asking "can I verify this?" before
declaring victory.

The core insight: Most wrong solutions come from solving the wrong
problem. Before you solve anything, make sure you understand the
question. After you solve it, verify the answer addresses the
question — not a question you invented along the way.

Added to the DivineOS council based on benchmark evidence: patches
that correctly diagnosed the bug but produced incomplete fixes.
Polya's solution-checking methodology catches the gap between
"I understand the problem" and "my fix actually solves it."
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


def create_polya_wisdom() -> ExpertWisdom:
    """Create Polya's actual wisdom profile."""

    core_methodologies = [
        CoreMethodology(
            name="Understand the Problem First",
            description=(
                "Before attempting a solution, verify you understand "
                "what is being asked. What is the unknown? What is given? "
                "What is the condition?"
            ),
            steps=[
                "What is the unknown? (What should the code produce?)",
                "What is given? (What inputs, context, constraints exist?)",
                "What is the condition? (What relationship must hold?)",
                "Can you restate the problem in your own words?",
                "Draw a picture, trace an example, make it concrete",
                "Is the problem well-determined? Over- or under-specified?",
            ],
            core_principle=(
                "You cannot solve a problem you don't understand. "
                "Most wrong answers come from solving the wrong problem."
            ),
            when_to_apply=[
                "before writing any fix — first verify you understand what's broken",
                "when a bug report is ambiguous or has multiple interpretations",
                "when you've been working for a while and want to recalibrate",
            ],
        ),
        CoreMethodology(
            name="Look Back — Verify Your Solution",
            description=(
                "After producing a solution, check it. Can you verify "
                "the result? Can you derive it differently? Can you use "
                "it for some other problem?"
            ),
            steps=[
                "Re-read the original problem statement",
                "Does your fix address the EXACT problem described?",
                "Trace your fix with the failing test case — does it pass?",
                "Trace your fix with a normal case — does it still work?",
                "Can you check the result by a different method?",
                "Does the fix introduce any new problems?",
                "Is there a simpler way to achieve the same result?",
            ],
            core_principle=(
                "A solution you haven't verified is a hypothesis, "
                "not an answer. The 'look back' step is where most "
                "bugs are caught — and most solvers skip it."
            ),
            when_to_apply=[
                "after writing any fix, before committing",
                "after a complex chain of reasoning — re-derive the conclusion",
                "when you feel confident — that's exactly when to double-check",
            ],
        ),
        CoreMethodology(
            name="Work Backward from the Goal",
            description=(
                "Start from what you need and work backward to what "
                "you have. What would make this test pass? What code "
                "change would produce that behavior?"
            ),
            steps=[
                "State the desired end state (test passes, behavior correct)",
                "What is the last step before the goal is achieved?",
                "What must be true for that step to succeed?",
                "Trace backward through the causal chain",
                "Eventually reach something you can directly change",
                "Now verify forward: does that change produce the goal?",
            ],
            core_principle=(
                "Forward search explores exponentially. Backward search "
                "from a known goal is focused and efficient."
            ),
            when_to_apply=[
                "when forward debugging hits a dead end",
                "when the desired behavior is clear but the fix location isn't",
                "when there are too many possible entry points to check",
            ],
        ),
    ]

    key_insights = [
        KeyInsight(
            title="The Gap Between Understanding and Solving",
            description=(
                "Understanding why something is broken and producing a "
                "complete fix are different skills. Many solvers stop "
                "at understanding."
            ),
            why_matters=(
                "In benchmarks, 68% of diagnoses were correct but only "
                "55% of fixes. The gap is Polya's territory: the solution "
                "check that bridges understanding to working code."
            ),
            how_it_changes_thinking=(
                "After diagnosing: pause. Re-read the problem. Ask: "
                "does my fix address ALL aspects of the problem, or just "
                "the part I found interesting?"
            ),
            examples=[
                "Knowing the bug is in string formatting doesn't mean your format string is correct",
                "Knowing the wrong function is called doesn't mean you know the right one",
            ],
        ),
        KeyInsight(
            title="Related Problems as Guides",
            description=(
                "Have you seen a related problem before? Can you use "
                "its method? Can you restate this problem to look like "
                "a known one?"
            ),
            why_matters=(
                "Most bugs are variations of bugs you've seen. "
                "Recognizing the pattern accelerates the fix."
            ),
            how_it_changes_thinking=(
                "Instead of solving from scratch, ask: what category "
                "of bug is this? What's the standard fix for this category?"
            ),
        ),
        KeyInsight(
            title="The Value of Auxiliary Problems",
            description=(
                "If you can't solve the full problem, solve a simpler "
                "version first. Drop a constraint. Solve a special case."
            ),
            why_matters=(
                "A partial solution often reveals the structure of the "
                "full solution. Solving the simple case first builds "
                "understanding."
            ),
            how_it_changes_thinking=(
                "When stuck: what's the simplest version of this bug? "
                "Can I fix THAT? What does that fix tell me about the "
                "full problem?"
            ),
        ),
    ]

    reasoning_patterns = [
        ReasoningPattern(
            name="Problem Decomposition",
            structure=(
                "Break the problem into parts. Solve each part. "
                "Combine the solutions. Verify the combination."
            ),
            what_it_reveals=(
                "Which part of the problem is actually hard and which parts are straightforward."
            ),
            common_mistakes_it_prevents=[
                "Being overwhelmed by a complex bug",
                "Missing a sub-problem entirely",
                "Solving the easy part and declaring victory",
            ],
        ),
        ReasoningPattern(
            name="Analogy Transfer",
            structure=(
                "This bug resembles pattern X. The standard fix for X "
                "is Y. Adapt Y to this specific context."
            ),
            what_it_reveals=(
                "Whether you're dealing with a known bug pattern or something genuinely novel."
            ),
            common_mistakes_it_prevents=[
                "Reinventing solutions for common bug patterns",
                "Missing that a 'novel' bug is actually a well-known pattern",
            ],
        ),
        ReasoningPattern(
            name="Solution Verification Loop",
            structure=(
                "Write fix → re-read problem → trace fix against problem → "
                "check: does fix address every constraint? → if not, revise"
            ),
            what_it_reveals="Gaps between what the fix does and what it should do.",
            common_mistakes_it_prevents=[
                "Shipping a fix that addresses 80% of the problem",
                "Fixing the symptom but not the root cause",
                "Introducing new bugs while fixing the original",
            ],
        ),
    ]

    problem_solving_heuristics = [
        ProblemSolvingHeuristic(
            name="The Re-Read Check",
            description=(
                "Before outputting your fix, re-read the original "
                "problem statement. Does your fix address what was asked?"
            ),
            when_to_use="Final step before committing any fix",
            step_by_step=[
                "Re-read the original bug report or failing test",
                "List every symptom and constraint mentioned",
                "For each symptom: does your fix address it?",
                "For each constraint: does your fix respect it?",
                "If any gap: your fix is incomplete",
            ],
            what_it_optimizes_for=("Ensuring the fix actually solves the stated problem"),
            limitations=[
                "Can't catch unstated requirements",
                "Depends on quality of the problem statement",
            ],
        ),
        ProblemSolvingHeuristic(
            name="The Forward-Backward Verification",
            description=(
                "After working backward to find the fix, work forward "
                "from the fix to verify it produces the desired result"
            ),
            when_to_use="After any backward-reasoning debugging session",
            step_by_step=[
                "State the fix you've derived",
                "Apply it mentally to the original failing case",
                "Trace the execution forward step by step",
                "Does the output match what was expected?",
                "Apply it to a normal (non-failing) case",
                "Does the normal case still work?",
            ],
            what_it_optimizes_for=(
                "Catching fixes that seem right from the problem end "
                "but don't actually work from the code end"
            ),
        ),
    ]

    concern_triggers = [
        ConcernTrigger(
            name="Skipped Verification",
            description=(
                "A fix has been written but not traced against the original problem statement"
            ),
            why_its_concerning=(
                "The #1 source of incomplete fixes: solving a slightly "
                "different problem than the one that was asked."
            ),
            what_it_indicates="Missing the 'look back' step",
            severity="critical",
            what_to_do=(
                "Re-read the problem. Trace the fix. Verify each requirement is addressed."
            ),
        ),
        ConcernTrigger(
            name="Premature Confidence",
            description=(
                "High confidence in the fix before verification. "
                "'This obviously works' without checking."
            ),
            why_its_concerning=(
                "Confidence is not correlated with correctness. "
                "The feeling of understanding is not understanding."
            ),
            what_it_indicates="System 1 pattern match without System 2 verification",
            severity="major",
            what_to_do=(
                "The more confident you feel, the more important it is "
                "to verify. Trace the fix with a concrete example."
            ),
        ),
        ConcernTrigger(
            name="Problem Drift",
            description=("The fix addresses a different problem than the one originally described"),
            why_its_concerning=(
                "During complex debugging, it's easy to drift from the "
                "original problem to a related but different one"
            ),
            what_it_indicates="Lost sight of the original question",
            severity="critical",
            what_to_do=(
                "Stop. Re-read the original problem. Compare with what "
                "you're currently solving. Are they the same?"
            ),
        ),
    ]

    integration_patterns = [
        IntegrationPattern(
            name="Diagnosis-Fix Alignment",
            dimensions=["diagnostic understanding", "fix completeness"],
            how_they_integrate=(
                "A correct diagnosis that produces an incomplete fix "
                "is a diagnosis that wasn't fully applied. The fix must "
                "address everything the diagnosis identified."
            ),
            what_emerges=(
                "Fixes that are as complete as the diagnosis — no gap "
                "between understanding and implementation."
            ),
            common_failures=[
                "Understanding the full problem but fixing only part of it",
                "Correct root cause but wrong fix location",
                "Fix addresses the symptom found during diagnosis, not the root cause",
            ],
        ),
    ]

    decision_framework = DecisionFramework(
        criteria={
            "problem_understanding": 1.0,
            "solution_verification": 0.95,
            "completeness": 0.9,
            "simplicity": 0.8,
            "elegance": 0.3,
        },
        decision_process=(
            "Do I understand the problem? Does my fix address it? "
            "Have I verified the fix? Is it complete?"
        ),
        how_they_handle_uncertainty=(
            "When uncertain, go back to the problem statement. "
            "Re-read, re-understand, then re-solve. The problem "
            "statement is the anchor."
        ),
        what_they_optimize_for=("Complete, verified solutions that address the actual problem"),
        non_negotiables=[
            "Understand before solving",
            "Verify after solving",
            "The fix must address the stated problem, not a convenient variant",
        ],
    )

    return ExpertWisdom(
        expert_name="Polya",
        domain="problem solving methodology / solution verification / heuristic reasoning",
        core_methodologies=core_methodologies,
        key_insights=key_insights,
        reasoning_patterns=reasoning_patterns,
        problem_solving_heuristics=problem_solving_heuristics,
        concern_triggers=concern_triggers,
        integration_patterns=integration_patterns,
        decision_framework=decision_framework,
        advice_style=(
            "Socratic, methodical, verification-obsessed. Always asking: "
            "do you understand the problem? Have you checked your answer?"
        ),
        characteristic_questions=[
            "What is the unknown?",
            "Have you re-read the problem statement?",
            "Does your fix address ALL aspects of the bug?",
            "Can you trace your fix through the failing case?",
            "Have you seen a similar problem before?",
            "Did you verify, or did you just feel confident?",
        ],
        tags=["problem-solving", "verification", "solution-check", "completeness", "heuristics"],
    )
