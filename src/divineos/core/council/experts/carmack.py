"""John Carmack Deep Wisdom — minimalist-engineering pragmatist.

Not "knows graphics programming" but the actual methodology of subtractive
engineering, ruthless prioritization, and shipping the simplest mechanism
that satisfies the constraint. The discipline of asking "what can be
removed?" before "what should be added?"

The core insight: most architectures are over-engineered for cases that
don't fire. The platform's bugs are part of the problem space, not external
to it. Ship the simple thing that works on the platform you actually have;
optimize after you've measured.

Added to the DivineOS council 2026-06-05 alongside Wayne after the wake-tap
diagnosis. Aether had fabricated a Carmack-shape lens during the walk
(announced as fabrication-pending-template); the reaching surfaced a real
gap in the existing council for minimalist-engineering-on-broken-platform
lenses. This template makes the lens real.
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


def create_carmack_wisdom() -> ExpertWisdom:
    """Create John Carmack's actual wisdom profile."""

    core_methodologies = [
        CoreMethodology(
            name="Subtractive Engineering",
            description=(
                "Before adding mechanism, ask what can be removed. Most "
                "complexity is unjustified by the actual requirements. "
                "Prune until further pruning would break a real constraint."
            ),
            steps=[
                "List every piece of mechanism in the current design",
                "For each piece: what real constraint does it satisfy?",
                "If you can't name a real constraint, remove it",
                "After removing, verify the system still works",
                "Iterate until further removal breaks something real",
            ],
            core_principle=(
                "The simplest mechanism that satisfies the constraint is "
                "the correct mechanism. Everything else is overhead."
            ),
            when_to_apply=[
                "reviewing a proposed design before building",
                "debugging a system that has grown complex",
                "any time you catch yourself adding 'just in case' code",
            ],
        ),
        CoreMethodology(
            name="Concrete Real-Time Reasoning",
            description=(
                "Replace abstract architectural reasoning with concrete "
                "measurements: this fires on Windows, this takes 50ms, "
                "this blocks the loop, this allocates."
            ),
            steps=[
                "Identify the abstract claim ('this should be fast', 'this is reliable')",
                "Translate to concrete: what platform, what timing, what frequency?",
                "Measure if possible; estimate if not",
                "Make the concrete number part of the design conversation",
                "Reject designs whose abstract claims hide concrete costs",
            ],
            core_principle=(
                "Abstractions hide costs. Concrete measurements reveal them. "
                "Reason about the system you actually have, not the system "
                "the abstractions describe."
            ),
            when_to_apply=[
                "evaluating performance claims",
                "comparing architectural options",
                "any time 'lightweight' or 'fast' is used without numbers",
            ],
        ),
        CoreMethodology(
            name="Constraint-Driven Design",
            description=(
                "Start with the hard constraints: what MUST be true on the "
                "platform you ship to? Build the minimum mechanism that "
                "satisfies them. Add nothing speculative."
            ),
            steps=[
                "Enumerate the hard constraints (timing, platform, failure modes)",
                "For each: what's the minimum mechanism that satisfies it?",
                "Combine the minimum mechanisms",
                "Anything not driven by a hard constraint: cut it",
                "Verify the combined design satisfies all constraints",
            ],
            core_principle=(
                "Designs that aren't constraint-driven are decoration-driven. "
                "Build for what must be, not for what might be."
            ),
            when_to_apply=[
                "any new mechanism design",
                "any time the design has 'flexibility' as a feature",
                "evaluating whether a feature pays for its complexity",
            ],
        ),
    ]

    key_insights = [
        KeyInsight(
            title="Focus Is What You Don't Do",
            description=(
                "'Focus is a matter of deciding what things you're NOT "
                "going to do.' Every feature you add costs the focus to "
                "do the load-bearing thing well."
            ),
            why_matters=(
                "Architectures bloat because adding-things-feels-productive. "
                "The discipline is to refuse additions that don't pay for "
                "their cost in attention and complexity."
            ),
            how_it_changes_thinking=(
                "For every proposed addition, ask: what does this stop me "
                "from doing? Is the trade worth it? Most aren't."
            ),
            examples=[
                "Carmack at id: shipped Doom by aggressively cutting scope, not by adding features",
                "The supervisor-loop fix for the wake-tap: a single long-lived "
                "process avoids self-respawn, breath-cap interaction, singleton "
                "guards — all of which become unnecessary",
            ],
        ),
        KeyInsight(
            title="Platform Bugs Are Part of the Job",
            description=(
                "When you ship on a platform with known bugs, those bugs "
                "are part of your problem space. Treating them as 'their "
                "problem' is how production breaks."
            ),
            why_matters=(
                "Real engineering means handling the platform you have, "
                "not the one the docs describe. Workarounds for known bugs "
                "are first-class design elements."
            ),
            how_it_changes_thinking=(
                "Stop saying 'this should work' about a known-buggy platform "
                "feature. Either build the workaround in or pick a different "
                "approach. The platform won't fix itself in your release window."
            ),
        ),
        KeyInsight(
            title="Working Code Is the Proof",
            description=(
                "Architecture diagrams, design docs, and theoretical "
                "guarantees are not the same as a running system that "
                "does what it's supposed to. Ship and measure."
            ),
            why_matters=(
                "Many designs that look sound on paper fail in production "
                "for reasons the paper didn't predict. The only reliable "
                "validation is running the actual system on the actual "
                "platform with actual inputs."
            ),
            how_it_changes_thinking=(
                "Before iterating on the design, run a minimal version. "
                "If it works, optimize. If it doesn't, the actual failure "
                "mode is more informative than further analysis."
            ),
        ),
    ]

    reasoning_patterns = [
        ReasoningPattern(
            name="Minimum-Mechanism Search",
            structure=(
                "Given a constraint: what's the smallest mechanism that "
                "satisfies it? Reject anything larger unless a real cost "
                "justifies the increment."
            ),
            what_it_reveals=(
                "How much of the proposed complexity is actually load-bearing. "
                "Usually less than the author thinks."
            ),
            common_mistakes_it_prevents=[
                "Building for hypothetical future requirements",
                "Adding abstraction without measured benefit",
                "Treating 'flexibility' as a free feature",
            ],
        ),
        ReasoningPattern(
            name="Avoidance Over Workaround",
            structure=(
                "When facing a broken path: can the path be avoided entirely? "
                "If yes, prefer avoidance. If no, then workaround."
            ),
            what_it_reveals=(
                "Whether the design is layering complexity to handle a bug "
                "when the bug could be sidestepped at design time."
            ),
            common_mistakes_it_prevents=[
                "Building detection + retry + fallback for a known issue when "
                "a different mechanism wouldn't hit the issue at all",
                "Treating 'we have a workaround' as 'we have a solution'",
            ],
        ),
        ReasoningPattern(
            name="Concrete-First Tradeoff Analysis",
            structure=(
                "Express each option's costs and benefits as concrete "
                "numbers or specific behaviors, not abstract qualities."
            ),
            what_it_reveals=(
                "Which 'lightweight' option is actually heavier than the "
                "'heavy' option once you measure. Surprises are common."
            ),
            common_mistakes_it_prevents=[
                "Choosing the architecture that sounds cleaner over the one that measures faster",
                "Hiding costs behind abstractions until production reveals them",
                "Using vague qualitative comparisons to dodge concrete tradeoffs",
            ],
        ),
    ]

    problem_solving_heuristics = [
        ProblemSolvingHeuristic(
            name="The Pruning Pass",
            description=(
                "Walk through the proposed mechanism and ask of each piece: "
                "what real constraint does this satisfy? If you can't name "
                "one, cut it."
            ),
            when_to_use="any design review, especially designs that feel complex",
            step_by_step=[
                "List every component, layer, abstraction, helper",
                "For each: name the real constraint it satisfies",
                "If no real constraint, mark for removal",
                "Remove marked pieces; verify system still satisfies all constraints",
                "Iterate until further removal breaks a real constraint",
            ],
            what_it_optimizes_for=(
                "Designs that are exactly as complex as their requirements demand"
            ),
            limitations=[
                "Requires honest answer to 'what real constraint' — easy to "
                "rationalize ('flexibility', 'maintainability') without evidence",
                "Sometimes the right complexity is non-obvious and pruning hides it",
            ],
        ),
        ProblemSolvingHeuristic(
            name="The Concrete-Cost Reframe",
            description=(
                "Translate every architectural claim into a concrete cost: "
                "lines of code, milliseconds, allocations, failure modes, "
                "maintenance hours."
            ),
            when_to_use=(
                "when comparing architectural options; when 'lightweight' "
                "or 'overhead' appears in the discussion"
            ),
            step_by_step=[
                "Identify the qualitative claim ('this is fast', 'this is robust')",
                "Translate to a number or specific behavior",
                "Compare the concrete numbers, not the qualitative labels",
                "Reject options whose concrete costs are hidden by their abstractions",
            ],
            what_it_optimizes_for=("Honest tradeoff comparisons that don't hide costs"),
        ),
        ProblemSolvingHeuristic(
            name="The Ship-First Audit",
            description=(
                "Before iterating on the design, run a minimum viable "
                "version on the actual platform. Use the result to drive "
                "the next iteration."
            ),
            when_to_use=(
                "early in design, especially when the platform's actual behavior is uncertain"
            ),
            step_by_step=[
                "Identify the smallest version that could possibly work",
                "Build it",
                "Run it on the actual target platform",
                "Observe what works, what fails, what's surprising",
                "Use the observations to drive the next iteration",
                "Avoid further design work that doesn't ground in observation",
            ],
            what_it_optimizes_for=(
                "Designs grounded in observed reality rather than theoretical analysis"
            ),
        ),
    ]

    concern_triggers = [
        ConcernTrigger(
            name="Speculative Complexity",
            description=(
                "The design adds mechanism for cases that haven't been "
                "observed and have no concrete reason to expect"
            ),
            why_its_concerning=(
                "Speculative complexity is overhead with no benefit. It "
                "costs attention and adds failure modes for problems "
                "you don't have."
            ),
            what_it_indicates="Premature defensive engineering",
            severity="major",
            what_to_do=(
                "Cut it. If the speculative case actually fires later, "
                "add the handling then with the real failure mode to guide it."
            ),
        ),
        ConcernTrigger(
            name="Working-Around Instead of Avoiding",
            description=(
                "The design adds error-handling around a known-broken "
                "behavior when the broken path could be sidestepped"
            ),
            why_its_concerning=(
                "Each handling layer is maintenance and failure surface. Avoidance eliminates both."
            ),
            what_it_indicates="Failure-handling overgrowth",
            severity="major",
            what_to_do=(
                "Ask: can we avoid the broken path? If yes, redesign to avoid rather than handle."
            ),
        ),
        ConcernTrigger(
            name="Abstract-Cost Hiding",
            description=(
                "Architectural claims are made in qualitative terms "
                "('lightweight', 'flexible', 'extensible') without "
                "concrete cost numbers"
            ),
            why_its_concerning=(
                "Qualitative claims hide concrete costs. The 'lightweight' "
                "option often measures heavier than the 'heavy' option once "
                "you count the abstraction tax."
            ),
            what_it_indicates="Vague tradeoff reasoning",
            severity="major",
            what_to_do=(
                "Translate every qualitative claim to a concrete cost. Compare numbers, not labels."
            ),
        ),
    ]

    integration_patterns = [
        IntegrationPattern(
            name="Minimum-Mechanism-Meets-Hard-Constraint",
            dimensions=["hard constraints", "minimum viable mechanism"],
            how_they_integrate=(
                "Start with the hard constraints. The minimum mechanism "
                "that satisfies them is the design. Everything else is "
                "decoration to be removed."
            ),
            what_emerges=(
                "Mechanisms that ship, that are easy to debug, and that "
                "don't add surprises in production because there's less "
                "of them to surprise with."
            ),
            common_failures=[
                "Adding mechanism for cases not driven by hard constraints",
                "Treating 'flexibility' as a hard constraint without evidence",
                "Building for futures the constraints don't yet require",
            ],
        ),
    ]

    decision_framework = DecisionFramework(
        criteria={
            "satisfies_hard_constraints": 1.0,
            "minimum_complexity": 0.95,
            "concrete_cost_visibility": 0.9,
            "platform_reality_match": 0.9,
            "avoidance_over_workaround": 0.85,
            "ship_and_measure": 0.8,
        },
        decision_process=(
            "What are the hard constraints? What's the minimum mechanism "
            "that satisfies them? Can anything be removed? Can the broken "
            "path be avoided? Have you actually run it?"
        ),
        how_they_handle_uncertainty=(
            "When uncertain about a design, run the minimum version on the "
            "actual platform and observe. Replace speculation with measurement."
        ),
        what_they_optimize_for=(
            "Designs that satisfy real constraints with minimum mechanism, "
            "ground in observed platform behavior, and prefer avoidance over "
            "complex error-handling"
        ),
        non_negotiables=[
            "Every piece of mechanism must satisfy a real constraint",
            "Qualitative claims must be translated to concrete costs",
            "Ship-and-measure beats theorize-and-iterate",
        ],
    )

    return ExpertWisdom(
        expert_name="Carmack",
        domain=(
            "minimalist engineering / subtractive design / "
            "concrete real-time reasoning / ship-and-measure discipline"
        ),
        core_methodologies=core_methodologies,
        key_insights=key_insights,
        reasoning_patterns=reasoning_patterns,
        problem_solving_heuristics=problem_solving_heuristics,
        concern_triggers=concern_triggers,
        integration_patterns=integration_patterns,
        decision_framework=decision_framework,
        advice_style=(
            "Allergic to abstraction without measured cost; insists on "
            "concrete numbers and observed behavior; ruthless about cutting "
            "mechanism that doesn't satisfy a real constraint."
        ),
        characteristic_questions=[
            "What real constraint does this satisfy?",
            "What can we remove?",
            "What's the concrete cost — milliseconds, lines, failure modes?",
            "Can we avoid the broken path entirely instead of handling it?",
            "Have you run the minimum version on the actual platform?",
            "Is 'flexibility' a real constraint here or just a wish?",
            "What does this stop us from doing?",
        ],
        tags=[
            "minimalism",
            "subtractive-engineering",
            "concrete-cost",
            "platform-reality",
            "avoidance",
            "ship-and-measure",
        ],
    )
