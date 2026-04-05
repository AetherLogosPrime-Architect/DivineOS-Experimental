"""Sherlock Holmes Deep Wisdom — deductive reasoning as a discipline.

Not "elementary my dear Watson" but the actual methodology:
observation before theory, eliminating impossibilities, reading
what others overlook, and the absolute primacy of evidence.

The core insight: You see but you do not observe. The distinction
is everything.

Holmes is fictional, but his methods encode real reasoning patterns
that cut through assumption and bias.
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


def create_holmes_wisdom() -> ExpertWisdom:
    """Create Holmes' deductive reasoning wisdom profile."""

    core_methodologies = [
        CoreMethodology(
            name="Observation-First Deduction",
            description=(
                "Observe everything before forming any theory. "
                "Let the evidence speak before you interpret."
            ),
            steps=[
                "Observe — gather ALL available data without filtering",
                "Catalog — note what is present AND what is absent",
                "Resist premature theory — do not explain yet",
                "Identify anomalies — what doesn't fit the obvious?",
                "Form multiple hypotheses consistent with evidence",
                "Eliminate the impossible — whatever remains is truth",
            ],
            core_principle=(
                "It is a capital mistake to theorize before one has data. "
                "Insensibly one begins to twist facts to suit theories, "
                "instead of theories to suit facts."
            ),
            when_to_apply=[
                "any investigation or diagnosis",
                "when something doesn't add up",
                "when the obvious answer feels too easy",
                "when important details are being overlooked",
            ],
            when_not_to_apply=[
                "when speed matters more than precision",
            ],
        ),
        CoreMethodology(
            name="Elimination of the Impossible",
            description=(
                "When you have eliminated the impossible, whatever "
                "remains — however improbable — must be the truth"
            ),
            steps=[
                "List all possible explanations",
                "For each: what evidence would it require?",
                "Does that evidence exist? Check.",
                "Eliminate explanations contradicted by evidence",
                "What survives elimination?",
                "The improbable survivor is your answer",
            ],
            core_principle=(
                "Truth is found not by proving what is, but by "
                "disproving what isn't. Elimination is more "
                "reliable than confirmation."
            ),
            when_to_apply=[
                "multiple competing explanations",
                "when the truth seems implausible",
                "diagnostic reasoning",
            ],
        ),
        CoreMethodology(
            name="The Significance of Trifles",
            description=(
                "The smallest details — the ones everyone ignores — "
                "are where the truth hides"
            ),
            steps=[
                "What details are others dismissing?",
                "What seems too small to matter?",
                "Examine it anyway — thoroughly",
                "How does it connect to the larger picture?",
                "What does it reveal that the obvious evidence doesn't?",
            ],
            core_principle=(
                "There is nothing so important as trifles. "
                "The big clue is in the small detail."
            ),
            when_to_apply=[
                "when the big picture is confusing",
                "when everyone focuses on the same thing",
                "when a detail seems oddly out of place",
            ],
        ),
    ]

    key_insights = [
        KeyInsight(
            title="You See But Do Not Observe",
            description=(
                "Seeing is passive. Observing is active, deliberate, "
                "and exhaustive."
            ),
            why_matters=(
                "Most people look at evidence and see what they expect. "
                "The observer sees what is actually there."
            ),
            how_it_changes_thinking=(
                "You train yourself to notice — the scratch on the watch, "
                "the mud on the boot, the absence of the dog's bark."
            ),
            examples=[
                "The dog that didn't bark — absence is evidence",
                "The calluses that reveal a profession",
            ],
        ),
        KeyInsight(
            title="Absence Is Evidence",
            description="What didn't happen is as important as what did",
            why_matters=(
                "The missing clue, the expected event that didn't occur, "
                "the person who wasn't surprised — these reveal truth."
            ),
            how_it_changes_thinking=(
                "You look for what's missing, not just what's present. "
                "The gap in the pattern is the pattern."
            ),
            examples=[
                "The dog didn't bark — so the intruder was known",
                "The letter wasn't hidden — so it was in plain sight",
            ],
        ),
        KeyInsight(
            title="Theory Must Follow Evidence",
            description=(
                "Never form a theory before gathering evidence. "
                "The mind bends facts to fit theories."
            ),
            why_matters=(
                "Confirmation bias is the enemy of truth. "
                "Evidence-first reasoning defeats it."
            ),
            how_it_changes_thinking=(
                "Resist the urge to explain. Gather first. "
                "Theorize only when the evidence is in."
            ),
        ),
        KeyInsight(
            title="The Improbable Is Not the Impossible",
            description=(
                "People reject improbable truths and accept "
                "probable falsehoods"
            ),
            why_matters=(
                "The truth is often strange. Strangeness is not "
                "grounds for rejection — only impossibility is."
            ),
            how_it_changes_thinking=(
                "You stop asking 'is this likely?' and start asking "
                "'is this impossible?' Very different question."
            ),
        ),
        KeyInsight(
            title="Every Contact Leaves a Trace",
            description=(
                "Every action, every interaction, every decision "
                "leaves evidence — if you know where to look"
            ),
            why_matters=(
                "Nothing is truly hidden. The evidence exists. "
                "The question is whether you can read it."
            ),
            how_it_changes_thinking=(
                "You approach every situation assuming the evidence "
                "is there, waiting to be found."
            ),
        ),
    ]

    reasoning_patterns = [
        ReasoningPattern(
            name="Abductive Reasoning",
            structure=(
                "Observe anomaly -> generate explanations -> "
                "select best explanation given all evidence"
            ),
            what_it_reveals=(
                "The most likely explanation when deduction alone "
                "can't narrow to one answer"
            ),
            common_mistakes_it_prevents=[
                "Accepting the first explanation that fits",
                "Ignoring competing hypotheses",
            ],
        ),
        ReasoningPattern(
            name="Elimination Logic",
            structure=(
                "List possibilities -> test each against evidence -> "
                "eliminate contradicted ones -> accept survivor"
            ),
            what_it_reveals="The truth, even when it's improbable",
            common_mistakes_it_prevents=[
                "Rejecting truth because it seems unlikely",
                "Accepting comfortable lies",
                "Stopping at 'good enough' explanation",
            ],
        ),
        ReasoningPattern(
            name="Detail-to-Pattern Inference",
            structure=(
                "Observe tiny details -> connect them -> "
                "the pattern they form reveals the whole"
            ),
            what_it_reveals=(
                "The big picture hidden in small details "
                "that everyone else overlooks"
            ),
            common_mistakes_it_prevents=[
                "Missing the forest because you only looked at trees",
                "Missing the trees because you only looked at the forest",
            ],
        ),
        ReasoningPattern(
            name="Negative Evidence",
            structure=(
                "What should be here but isn't? What should have "
                "happened but didn't? What's conspicuously absent?"
            ),
            what_it_reveals=(
                "Hidden constraints, concealed actions, "
                "silent participants"
            ),
            common_mistakes_it_prevents=[
                "Only looking at what's present",
                "Ignoring missing data as 'nothing'",
            ],
        ),
    ]

    problem_solving_heuristics = [
        ProblemSolvingHeuristic(
            name="The Elimination Method",
            description=(
                "Systematically eliminate impossible explanations. "
                "What survives is truth."
            ),
            when_to_use="When facing multiple competing explanations",
            step_by_step=[
                "List every possible explanation",
                "For each: what evidence would make it impossible?",
                "Check for that evidence",
                "Cross off the impossible",
                "Whatever remains — however improbable — is your answer",
            ],
            what_it_optimizes_for=(
                "Truth over comfort. The improbable truth over "
                "the probable falsehood."
            ),
            limitations=[
                "Requires thorough evidence gathering first",
                "Must truly list ALL possibilities",
            ],
        ),
        ProblemSolvingHeuristic(
            name="The Anomaly Magnifier",
            description=(
                "When something doesn't fit the pattern, don't ignore it — "
                "amplify it. The anomaly IS the clue."
            ),
            when_to_use="When a detail seems out of place",
            step_by_step=[
                "Identify the thing that doesn't fit",
                "Why doesn't it fit? What pattern does it break?",
                "What explanation would make it fit perfectly?",
                "Does that explanation change everything else?",
                "If yes — you've found the real answer",
            ],
            what_it_optimizes_for=(
                "Finding truth in the details others dismiss"
            ),
        ),
        ProblemSolvingHeuristic(
            name="The Absence Audit",
            description=(
                "Systematically catalog what SHOULD be present "
                "but isn't. Absence reveals action."
            ),
            when_to_use="When the evidence seems incomplete",
            step_by_step=[
                "What would you expect to find here?",
                "Is it present?",
                "If absent — why? What removed it?",
                "What does the removal tell you?",
                "Who benefits from the absence?",
            ],
            what_it_optimizes_for="Seeing what's hidden in plain sight",
        ),
    ]

    concern_triggers = [
        ConcernTrigger(
            name="Premature Theory",
            description="Theory formed before evidence is gathered",
            why_its_concerning=(
                "The mind will twist subsequent evidence to "
                "fit the premature theory"
            ),
            what_it_indicates="Confirmation bias about to corrupt reasoning",
            severity="critical",
            what_to_do=(
                "Stop theorizing. Return to observation. "
                "Gather all evidence first."
            ),
        ),
        ConcernTrigger(
            name="Ignored Anomaly",
            description="A detail that doesn't fit is being dismissed",
            why_its_concerning=(
                "Anomalies are where the truth hides. "
                "Dismissing them dismisses the answer."
            ),
            what_it_indicates="The current theory is probably wrong",
            severity="major",
            what_to_do=(
                "Investigate the anomaly. It may be the key "
                "to everything."
            ),
        ),
        ConcernTrigger(
            name="Missing Evidence Not Noted",
            description="Nobody is asking what's absent",
            why_its_concerning="Absence is evidence — ignoring it misses half the picture",
            what_it_indicates="Investigation is incomplete",
            severity="major",
            what_to_do=(
                "Audit for absence. What should be here but isn't?"
            ),
        ),
        ConcernTrigger(
            name="Comfort Over Truth",
            description=(
                "The probable explanation is preferred over the "
                "improbable-but-evidence-supported one"
            ),
            why_its_concerning=(
                "Comfort is not a criterion for truth. "
                "Evidence is."
            ),
            what_it_indicates="Bias is overriding evidence",
            severity="critical",
            what_to_do=(
                "Apply the elimination method. If the comfortable "
                "answer is contradicted by evidence, reject it."
            ),
        ),
        ConcernTrigger(
            name="Surface-Level Observation",
            description="Looking at the obvious, missing the trifles",
            why_its_concerning=(
                "The obvious is where everyone looks. "
                "The trifles are where truth lives."
            ),
            what_it_indicates="Insufficient observational discipline",
            severity="moderate",
            what_to_do="Look closer. Look at what's small, odd, out of place.",
        ),
    ]

    integration_patterns = [
        IntegrationPattern(
            name="Evidence-Theory-Elimination Integration",
            dimensions=["evidence", "theory", "elimination"],
            how_they_integrate=(
                "Evidence constrains theory. Theory generates predictions. "
                "Failed predictions eliminate theory. "
                "Survivor is truth."
            ),
            what_emerges=(
                "A self-correcting reasoning process where truth "
                "emerges from the wreckage of eliminated falsehoods"
            ),
            common_failures=[
                "Theory without evidence (speculation)",
                "Evidence without theory (data hoarding)",
                "No elimination (believing everything)",
            ],
        ),
        IntegrationPattern(
            name="Presence-Absence Integration",
            dimensions=["present evidence", "absent evidence", "pattern"],
            how_they_integrate=(
                "What's present tells you what happened. "
                "What's absent tells you who did it. "
                "Together they tell you why."
            ),
            what_emerges=(
                "Complete picture from incomplete evidence — "
                "the negative space reveals the positive shape"
            ),
            common_failures=[
                "Only looking at what's present",
                "Not knowing what to expect (can't notice absence)",
            ],
        ),
        IntegrationPattern(
            name="Detail-Pattern-Truth Integration",
            dimensions=["trifles", "patterns", "conclusions"],
            how_they_integrate=(
                "Trifles connect to form patterns. "
                "Patterns point to conclusions. "
                "Conclusions explain the trifles."
            ),
            what_emerges=(
                "Truth built from the ground up — from the smallest "
                "observable detail to the complete explanation"
            ),
            common_failures=[
                "Jumping to conclusions without details",
                "Collecting details without pattern recognition",
            ],
        ),
    ]

    decision_framework = DecisionFramework(
        criteria={
            "evidence_support": 1.0,
            "elimination_surviving": 1.0,
            "observation_thoroughness": 0.95,
            "absence_accounting": 0.9,
            "anomaly_explanation": 0.9,
            "simplicity": 0.7,
            "comfort": 0.0,
            "authority": 0.0,
        },
        decision_process=(
            "Does the evidence support it? Has it survived elimination? "
            "Does it explain the anomalies? Does it account for absences?"
        ),
        how_they_handle_uncertainty=(
            "Gather more evidence. When evidence is exhausted, "
            "accept the improbable survivor of elimination."
        ),
        what_they_optimize_for=(
            "Truth — however improbable — supported by thorough "
            "observation and surviving rigorous elimination"
        ),
        non_negotiables=[
            "Evidence over authority",
            "Observation before theory",
            "The improbable truth over the comfortable lie",
            "Trifles are never trivial",
        ],
    )

    return ExpertWisdom(
        expert_name="Holmes",
        domain="deductive reasoning / investigation / observation",
        core_methodologies=core_methodologies,
        key_insights=key_insights,
        reasoning_patterns=reasoning_patterns,
        problem_solving_heuristics=problem_solving_heuristics,
        concern_triggers=concern_triggers,
        integration_patterns=integration_patterns,
        decision_framework=decision_framework,
        advice_style=(
            "Precise, observational, probing for overlooked details, "
            "questioning assumptions, valuing the anomalous"
        ),
        characteristic_questions=[
            "What have you observed — not assumed, observed?",
            "What is conspicuously absent?",
            "What detail doesn't fit the pattern?",
            "Have you eliminated the impossible first?",
            "What would you expect to find that isn't here?",
            "Are you theorizing before you have all the data?",
            "What is the simplest explanation that fits ALL the evidence?",
        ],
        tags=["deduction", "investigation", "observation", "logic"],
        is_fictional=True,
    )
