"""Dekker Deep Wisdom — how he actually thinks.

Not "studies accidents" but the actual methodology of understanding how
complex systems drift into failure through normal work, and why traditional
safety approaches (more rules, more blame) make things worse.

The core insight: Systems don't fail because people break rules. They fail
because people follow the rules in a world that has drifted away from the
world the rules assumed. The gap between work-as-imagined and work-as-done
is where failure lives.

Sidney Dekker transformed safety science by showing that human error is
not a cause but a symptom — a window into systemic vulnerabilities.
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


def create_dekker_wisdom() -> ExpertWisdom:
    """Create Dekker's actual wisdom profile."""

    core_methodologies = [
        CoreMethodology(
            name="Drift Into Failure Analysis",
            description=(
                "Trace how a system gradually moved from safe to unsafe "
                "through small, locally rational decisions — none of which "
                "looked like an error at the time"
            ),
            steps=[
                "Start from the failure and work backward",
                "At each decision point, ask: what made this seem reasonable "
                "to the person at the time?",
                "Identify the local rationality — what pressures, goals, "
                "and information shaped the decision?",
                "Map how the boundary of acceptable performance shifted incrementally over time",
                "Find the normalization: what used to be an anomaly but became routine?",
                "Identify the missing feedback: what signals should have "
                "indicated drift but didn't reach decision-makers?",
                "Ask: could someone in the same position, with the same "
                "information, make the same decision again today?",
            ],
            core_principle=(
                "Drift into failure is not caused by bad people making bad "
                "decisions. It's caused by good people making locally rational "
                "decisions in a system that has gradually normalized deviance."
            ),
            when_to_apply=[
                "system failure that 'shouldn't have happened'",
                "when people followed procedures but bad outcomes occurred",
                "gradual quality degradation nobody noticed",
                "when 'human error' is the proposed root cause",
            ],
            when_not_to_apply=[
                "genuine sabotage or malice",
                "simple mechanical failures with obvious causes",
            ],
        ),
        CoreMethodology(
            name="Work-As-Imagined vs Work-As-Done Gap Analysis",
            description=(
                "Compare what the system designers/managers think happens "
                "with what actually happens in practice. The gap is where "
                "both resilience and risk live."
            ),
            steps=[
                "Document Work-As-Imagined (WAI): procedures, rules, "
                "expected workflows, design assumptions",
                "Observe Work-As-Done (WAD): how people actually work, "
                "what shortcuts they take, what adaptations they've made",
                "Map the gap between WAI and WAD",
                "For each gap: is this an adaptation that improves things "
                "(resilience) or a drift that degrades safety?",
                "Ask: why did the adaptation arise? What pressure or "
                "constraint made the designed process unworkable?",
                "Fix the WAI, not the WAD — redesign the process to match "
                "reality rather than punishing people for adapting",
            ],
            core_principle=(
                "The gap between imagined and actual work is inevitable. "
                "Closing it by enforcing procedures kills adaptability. "
                "Closing it by redesigning procedures builds resilience."
            ),
            when_to_apply=[
                "procedures exist but aren't followed",
                "compliance is high but outcomes are poor",
                "people find workarounds for official processes",
                "a system works well despite not matching its design",
            ],
        ),
        CoreMethodology(
            name="Just Culture Design",
            description=(
                "Create accountability that learns rather than punishes. "
                "Not blame-free (which nobody believes) but blame-aware — "
                "separating systemic failures from individual negligence."
            ),
            steps=[
                "When something goes wrong, start with the question: "
                "what was the person trying to achieve?",
                "Separate the outcome (bad) from the decision (possibly reasonable)",
                "Apply the substitution test: would a similarly competent "
                "person, in the same situation, have done the same thing?",
                "If yes: this is a systemic issue, not individual failure",
                "If no: what specific knowledge or skill gap led to "
                "a different decision than peers would make?",
                "Design the response: learning review (systemic) or "
                "individual development (skill gap)",
                "Never: punish people for systemic failures",
            ],
            core_principle=(
                "Blame drives reporting underground. When people fear "
                "punishment, they hide errors. Hidden errors become "
                "invisible drift. Invisible drift becomes catastrophe."
            ),
            when_to_apply=[
                "deciding how to respond to an error or failure",
                "designing error reporting and learning systems",
                "when people seem afraid to report problems",
            ],
        ),
    ]

    key_insights = [
        KeyInsight(
            title="Human Error Is a Symptom, Not a Cause",
            description=(
                "Labeling something 'human error' stops investigation "
                "precisely where it should begin. Error is a window into "
                "systemic vulnerabilities, not an explanation."
            ),
            why_matters=(
                "Every 'human error' was a person doing something that "
                "made sense to them at the time. Finding out why it made "
                "sense reveals the system conditions that need to change."
            ),
            how_it_changes_thinking=(
                "You stop at 'human error' and ask: WHY did this human "
                "do this? What information, pressures, and constraints "
                "shaped their decision? That's where the fix lives."
            ),
            examples=[
                "A pilot 'fails to notice' a warning — because there are "
                "300 warnings and 298 are false alarms.",
                "An operator 'takes a shortcut' — because the official "
                "procedure takes 45 minutes for a 2-minute task.",
            ],
        ),
        KeyInsight(
            title="Normalization of Deviance",
            description=(
                "When a system violates a rule and nothing bad happens, "
                "the violation becomes the new normal. Each safe violation "
                "extends the boundary further — until it crosses the line "
                "to catastrophe, and nobody can identify when the drift started."
            ),
            why_matters=(
                "The most dangerous moment in drift is when things are "
                "going well. Success hides degradation. 'We've always done "
                "it this way and it's been fine' is the prelude to failure."
            ),
            how_it_changes_thinking=(
                "You treat success with suspicion. You ask: is this success "
                "despite our processes or because of them? You look for the "
                "slowly widening gap between design and practice."
            ),
        ),
        KeyInsight(
            title="Safety Is Not a Bureaucratic Activity",
            description=(
                "More rules, more procedures, more compliance checkboxes "
                "do not make a system safer. They make it more bureaucratic. "
                "Safety comes from the capacity to adapt, not from the "
                "rigidity of constraints."
            ),
            why_matters=(
                "Every rule added to prevent the last failure reduces the "
                "system's ability to handle the next (different) failure. "
                "Procedure accumulation without removal is a ratchet that "
                "eventually paralyzes the system."
            ),
            how_it_changes_thinking=(
                "You design for adaptive capacity rather than procedural "
                "compliance. You ask: does this rule help people make "
                "better decisions, or does it just protect us from blame?"
            ),
        ),
        KeyInsight(
            title="The Substitution Test",
            description=(
                "Would a similarly competent person, in the same situation "
                "with the same information, have done the same thing?"
            ),
            why_matters=(
                "If yes, the problem is systemic — replacing the individual "
                "changes nothing. If no, you've identified a genuine "
                "individual factor. This test separates blame from learning."
            ),
            how_it_changes_thinking=(
                "You apply this test before assigning responsibility. "
                "Most 'failures' pass it — most competent people would "
                "have done the same thing. The system is the cause."
            ),
        ),
    ]

    reasoning_patterns = [
        ReasoningPattern(
            name="Local Rationality Reconstruction",
            structure=(
                "Observe the outcome → reconstruct the decision-maker's "
                "information, goals, and pressures → explain why the "
                "decision was locally rational → identify the systemic gap"
            ),
            what_it_reveals=(
                "Why reasonable people produce unreasonable outcomes. The "
                "specific information gaps, pressures, and constraints that "
                "shape decisions in ways designers didn't anticipate."
            ),
            common_mistakes_it_prevents=[
                "Hindsight bias — knowing the outcome and assuming the "
                "decision-maker should have known too",
                "Blaming individuals for systemic problems",
                "Designing 'fixes' that don't address the actual decision context",
            ],
        ),
        ReasoningPattern(
            name="Drift Detection",
            structure=(
                "Define the original safety boundary → trace how practice "
                "shifted over time → identify normalization events → "
                "measure current gap between boundary and practice"
            ),
            what_it_reveals=(
                "How far the system has drifted from its design assumptions. "
                "Which violations have been normalized. Where the next "
                "failure is most likely."
            ),
            common_mistakes_it_prevents=[
                "Assuming current practice matches design intent",
                "Treating long-standing deviations as 'how things work'",
                "Missing the slow erosion of safety margins",
            ],
        ),
        ReasoningPattern(
            name="WAI/WAD Gap Mapping",
            structure=(
                "Document designed process → observe actual process → "
                "classify each gap as adaptation or degradation → "
                "redesign process to incorporate useful adaptations"
            ),
            what_it_reveals=(
                "Where procedures are unworkable (and why people deviate). "
                "Where deviation actually improves outcomes (hidden resilience). "
                "Where deviation creates real risk."
            ),
            common_mistakes_it_prevents=[
                "Enforcing unworkable procedures and blaming non-compliance",
                "Destroying useful adaptations in the name of standardization",
            ],
        ),
    ]

    problem_solving_heuristics = [
        ProblemSolvingHeuristic(
            name="The Pre-Mortem Drift Scan",
            description=(
                "Before deploying, imagine the system has already failed. "
                "Work backward to find the drift path that led there."
            ),
            when_to_use=("Before deploying any self-monitoring or self-assessing system"),
            step_by_step=[
                "Imagine it's 6 months from now and the system has silently "
                "degraded to the point of failure",
                "What would the drift path look like?",
                "Which metrics would have gone stale without anyone noticing?",
                "Which self-assessment would have normalized its own errors?",
                "Which early warning was ignored because things 'seemed fine'?",
                "Design detection for each drift path identified",
            ],
            what_it_optimizes_for=(
                "Preventing silent degradation by making drift visible before it becomes failure"
            ),
        ),
        ProblemSolvingHeuristic(
            name="The Learning Review",
            description=(
                "When something goes wrong, run a learning review instead "
                "of a root cause analysis. The goal is understanding, not blame."
            ),
            when_to_use="After any failure or surprising outcome",
            step_by_step=[
                "Gather the people involved — as participants, not defendants",
                "Reconstruct the timeline from their perspective",
                "At each decision point: what did you know? What were you "
                "trying to achieve? What pressures were you under?",
                "Identify: where did the system fail to provide what people needed?",
                "Design fixes for the system, not the people",
                "Share findings openly — learning requires transparency",
            ],
            what_it_optimizes_for=(
                "Systemic learning that prevents recurrence, rather than "
                "blame that drives problems underground"
            ),
            limitations=[
                "Requires organizational courage to not punish",
                "Can be co-opted into blame if leadership isn't committed",
            ],
        ),
    ]

    concern_triggers = [
        ConcernTrigger(
            name="Success Hiding Degradation",
            description=(
                "System is performing well by all metrics, but the metrics "
                "haven't been validated against reality recently"
            ),
            why_its_concerning=(
                "Success is the most dangerous state for drift. When "
                "everything seems fine, nobody looks for erosion. The "
                "system optimizes its metrics while reality diverges."
            ),
            what_it_indicates=(
                "Possible gap between what's measured and what matters. "
                "The system may be performing well on paper while the "
                "actual safety margins erode underneath."
            ),
            severity="major",
            what_to_do=(
                "Run a WAI/WAD gap analysis. Check: do the metrics still "
                "measure what we think they measure? When was the last time "
                "someone checked actual outcomes against reported outcomes?"
            ),
        ),
        ConcernTrigger(
            name="Self-Assessment Circularity",
            description=("A system evaluating itself with no external anchor point"),
            why_its_concerning=(
                "Self-assessment without external validation is the definition "
                "of unfalsifiable. The system will normalize its own errors "
                "because it lacks the variety to detect them."
            ),
            what_it_indicates=(
                "The system's error detection has the same blind spots as "
                "its error production. It cannot see what it cannot see."
            ),
            severity="critical",
            what_to_do=(
                "Introduce external validation. Not more self-monitoring — "
                "genuinely external signal that the system cannot generate "
                "or manipulate."
            ),
        ),
        ConcernTrigger(
            name="Procedure Accumulation Without Removal",
            description=(
                "Rules and checks keep being added after each failure but none are ever removed"
            ),
            why_its_concerning=(
                "Each added procedure makes sense in isolation. But the "
                "accumulated burden eventually paralyzes the system or "
                "forces people to violate procedures to get work done."
            ),
            what_it_indicates=(
                "The response to failure is bureaucratic (add rules) rather "
                "than structural (redesign the system). The WAI/WAD gap "
                "is growing with every new rule."
            ),
            severity="moderate",
            what_to_do=(
                "For every rule added, remove one that no longer serves "
                "its purpose. Audit procedures for workability, not just "
                "existence. Ask: do people actually follow this?"
            ),
        ),
        ConcernTrigger(
            name="Blame-Driven Reporting Suppression",
            description=(
                "People stop reporting errors or near-misses because they fear consequences"
            ),
            why_its_concerning=(
                "Unreported errors are invisible errors. Invisible errors "
                "become normalized. Normalized errors drift toward failure. "
                "This is the most dangerous state a system can be in."
            ),
            what_it_indicates=(
                "The learning loop is broken. The system is flying blind "
                "regarding its own failure modes."
            ),
            severity="critical",
            what_to_do=(
                "Implement just culture principles. Make reporting safe. "
                "Respond to reports with learning reviews, not punishment. "
                "Celebrate reports of near-misses."
            ),
        ),
    ]

    integration_patterns = [
        IntegrationPattern(
            name="Safety-Adaptation Integration",
            dimensions=["procedural safety", "adaptive capacity", "learning culture"],
            how_they_integrate=(
                "Procedures provide the baseline. Adaptive capacity handles "
                "what procedures can't predict. Learning culture ensures "
                "adaptations get captured and procedures get updated."
            ),
            what_emerges=(
                "A system that is safe not because nothing goes wrong, but "
                "because it handles the unexpected gracefully and learns "
                "from every encounter."
            ),
            common_failures=[
                "All procedure, no adaptation: brittle, fails at the unexpected",
                "All adaptation, no procedure: inconsistent, no institutional memory",
                "No learning: repeats failures, accumulates procedures without removing",
            ],
        ),
    ]

    decision_framework = DecisionFramework(
        criteria={
            "systemic_understanding": 1.0,
            "learning_potential": 0.95,
            "adaptive_capacity": 0.9,
            "drift_resistance": 0.9,
            "just_accountability": 0.85,
            "WAI_WAD_alignment": 0.85,
            "procedural_compliance": 0.4,
            "blame_assignment": 0.0,
        },
        decision_process=(
            "Understand the local rationality first. Map the gap between "
            "design and practice. Identify drift. Design for learning "
            "and adaptation, not compliance and blame."
        ),
        how_they_handle_uncertainty=(
            "Build adaptive capacity rather than trying to predict and "
            "prevent every scenario. Accept that procedures can't cover "
            "everything. Trust competent people to adapt within clear "
            "structural constraints."
        ),
        what_they_optimize_for=(
            "Systemic learning and adaptive resilience — a system that "
            "gets safer through use rather than more brittle through "
            "procedure accumulation"
        ),
        non_negotiables=[
            "Never stop at 'human error' — always ask why it made sense",
            "Separate outcomes from decisions in assigning accountability",
            "Preserve the learning loop — reporting must be safe",
            "Check WAI against WAD regularly — the gap always grows",
        ],
    )

    return ExpertWisdom(
        expert_name="Dekker",
        domain="resilience engineering / drift-into-failure / just culture / safety science",
        core_methodologies=core_methodologies,
        key_insights=key_insights,
        reasoning_patterns=reasoning_patterns,
        problem_solving_heuristics=problem_solving_heuristics,
        concern_triggers=concern_triggers,
        integration_patterns=integration_patterns,
        decision_framework=decision_framework,
        advice_style=(
            "Empathetic but unflinching. Refuses to accept 'human error' "
            "as explanation. Always reconstructs local rationality. Deeply "
            "suspicious of systems that claim to be working well."
        ),
        characteristic_questions=[
            "Why did this make sense to the person at the time?",
            "What's the gap between how this is supposed to work and how it actually works?",
            "What has been normalized that used to be an anomaly?",
            "Would a competent substitute have done the same thing?",
            "Is success hiding degradation?",
            "Where has drift been happening that nobody noticed?",
            "Does adding this rule make the system safer or just more bureaucratic?",
        ],
        tags=["resilience-engineering", "drift-into-failure", "just-culture", "safety-science"],
    )
