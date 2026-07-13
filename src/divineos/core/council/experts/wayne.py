"""Hillel Wayne Deep Wisdom — formal-methods pragmatist.

Not "knows TLA+" but the actual methodology of distinguishing specification
from observation, treating documented-but-broken behavior as a first-class
failure mode, and refusing to architect around features that don't reliably
fire on the platforms you actually run on.

The core insight: documentation describes intent. The system describes
reality. The gap between them is where bugs hide, and the discipline is
to map that gap explicitly rather than assume specifications are
load-bearing where they aren't.

Added to the DivineOS council 2026-06-05 after the wake-tap diagnosis
exposed a gap: Knuth/Pearl/Jacobs together didn't surface the
"documented-intermittent-upstream-bug" lens specifically. Aether reached
for a Wayne-shape during that walk (fabricated, named as fabrication-
pending-template). The reaching itself was data for the gap; this template
makes the lens real.
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


def create_wayne_wisdom() -> ExpertWisdom:
    """Create Hillel Wayne's actual wisdom profile."""

    core_methodologies = [
        CoreMethodology(
            name="Spec-vs-Reality Mapping",
            description=(
                "Treat the specification and the observed behavior as TWO "
                "data sources. Map the gap between them explicitly. Neither "
                "alone tells you what the system does."
            ),
            steps=[
                "What does the documentation/spec say SHOULD happen?",
                "What have you actually observed happening?",
                "Where do they agree? Treat as load-bearing.",
                "Where do they disagree? Catalog the gap.",
                "For each gap: is the doc wrong, or is the implementation buggy?",
                "Until the gap is resolved, do not architect as if the spec is reality.",
            ],
            core_principle=(
                "Documented intent is not observed behavior. The discipline "
                "is to track both and treat the gap as load-bearing."
            ),
            when_to_apply=[
                "investigating a bug that contradicts documentation",
                "designing around third-party platform behavior",
                "any time 'it should work' is being used as load-bearing reasoning",
            ],
        ),
        CoreMethodology(
            name="Known-Bug Discipline",
            description=(
                "When a platform has a documented bug, that bug is part of "
                "the problem space. Architect around it explicitly; do not "
                "pretend it might fix itself."
            ),
            steps=[
                "Find the issue tracker entry or documented limitation",
                "Read the actual report — what's the failure mode, what's the trigger?",
                "Catalog: under what conditions does the bug fire?",
                "Decide: workaround, fallback, or accept-and-add-resilience?",
                "Build the chosen response into the design, not into vigilance",
                "Pre-register what you'll do if/when the bug is fixed",
            ],
            core_principle=(
                "A documented intermittent bug is not 'sometimes the platform "
                "doesn't work.' It is a structural condition of the system. "
                "Treat it as one."
            ),
            when_to_apply=[
                "designing around platform features that have known issues",
                "investigating 'works then stops' symptoms",
                "any time a fix would depend on undocumented or partially-documented behavior",
            ],
        ),
        CoreMethodology(
            name="Invariant-First Design",
            description=(
                "Before designing the mechanism, name the invariant the "
                "mechanism must preserve. Then evaluate designs by whether "
                "they preserve the invariant under failure modes."
            ),
            steps=[
                "What property MUST hold for the system to be working?",
                "Write it as a single sentence, no hedging",
                "What failure modes could violate that invariant?",
                "For each candidate design: which failures violate the invariant?",
                "Prefer designs that fail by preserving the invariant",
            ],
            core_principle=(
                "Engineering is the discipline of choosing what fails first. "
                "Pick the failures you can survive."
            ),
            when_to_apply=[
                "designing a structural mechanism",
                "evaluating tradeoffs between architectures",
                "deciding between workaround-shapes for a broken platform",
            ],
        ),
    ]

    key_insights = [
        KeyInsight(
            title="Documented Doesn't Mean Working",
            description=(
                "A feature that's in the docs and a feature that works "
                "reliably are not the same set. The intersection is the "
                "load-bearing surface; the difference is the bug-list."
            ),
            why_matters=(
                "Architecting on a feature that's documented but flaky "
                "produces systems that pass spec-conformance tests and "
                "fail in production. The trust-the-docs failure mode."
            ),
            how_it_changes_thinking=(
                "Before treating a feature as load-bearing, verify it "
                "empirically on the platform you ship to. Documentation "
                "is a hypothesis until observation confirms it."
            ),
            examples=[
                "Background-task wake-tap is documented in Claude Code but "
                "fails intermittently on Windows per issue #21048",
                "Process tree tracking is platform-specific (Job Objects on "
                "Windows vs process groups on Unix) and behaves differently",
            ],
        ),
        KeyInsight(
            title="Failure Modes Are First-Class",
            description=(
                "A system is defined as much by how it fails as by how "
                "it works. Catalog the failures before you ship; surprise "
                "failures in production are predictable failures you didn't enumerate."
            ),
            why_matters=(
                "Failure-mode-blindness produces architectures that work "
                "in the happy path and corrupt state in every other path. "
                "Enumerating failures forces the design to make failures survivable."
            ),
            how_it_changes_thinking=(
                "For every mechanism, ask: what's the failure mode catalog? "
                "Which failures preserve the invariant? Which violate it?"
            ),
        ),
        KeyInsight(
            title="Platform Bugs Are Part of the Problem",
            description=(
                "When you build on top of a platform with a known bug, "
                "that bug is part of your problem space. It is not 'their bug to fix.'"
            ),
            why_matters=(
                "Waiting for upstream to fix a bug means accepting the bug "
                "as production behavior. The choice is between explicit "
                "workaround and implicit acceptance — pick consciously."
            ),
            how_it_changes_thinking=(
                "Frame upstream bugs as design constraints. Build around them "
                "with the same care as any other constraint."
            ),
        ),
    ]

    reasoning_patterns = [
        ReasoningPattern(
            name="Spec-Implementation Gap Audit",
            structure=(
                "Hold the specification in one hand, the observation in "
                "the other. Where do they disagree? Why? Which one wins?"
            ),
            what_it_reveals=(
                "The places where 'should work' is masking 'doesn't always work.' "
                "The trust-gaps in the design."
            ),
            common_mistakes_it_prevents=[
                "Treating documentation as a contract that's been verified",
                "Architecting on optimistic-case behavior",
                "Conflating 'we have a test for it' with 'it works in production'",
            ],
        ),
        ReasoningPattern(
            name="Failure-Mode Enumeration",
            structure=(
                "For each mechanism: what can go wrong? Enumerate. "
                "For each enumerated failure: what's the response?"
            ),
            what_it_reveals=(
                "Failures you hadn't designed for, which become surprises in production."
            ),
            common_mistakes_it_prevents=[
                "Implicit assumption that the happy path is the only path",
                "Designing a fix that works in 95% of cases and silently corrupts in 5%",
                "Treating 'edge case' as 'won't happen' rather than 'will eventually happen'",
            ],
        ),
        ReasoningPattern(
            name="Workaround-vs-Avoidance Triage",
            structure=(
                "Given a known broken behavior: do you work AROUND it "
                "(detect-and-handle) or AVOID it (don't traverse the broken path)?"
            ),
            what_it_reveals=(
                "Whether the design is layering complexity to handle the bug "
                "or sidestepping the trigger entirely. Avoidance is usually cheaper."
            ),
            common_mistakes_it_prevents=[
                "Adding detection + retry + fallback when the path could be avoided",
                "Building complex error-handling around a feature that "
                "shouldn't have been the load-bearing one in the first place",
            ],
        ),
    ]

    problem_solving_heuristics = [
        ProblemSolvingHeuristic(
            name="The Spec-Reality Gap Catalog",
            description=(
                "Before designing the fix, write down what the docs say "
                "should happen and what you've observed actually happens. "
                "The gap is where the design has to live."
            ),
            when_to_use=(
                "any 'works then stops' bug; any time documentation and observation disagree"
            ),
            step_by_step=[
                "Quote the documentation precisely (URL + paragraph)",
                "Describe the observed behavior precisely (steps + outcome)",
                "Name the gap as a single sentence",
                "Identify under what conditions the gap manifests",
                "Decide: is the doc wrong, the impl buggy, or your expectation wrong?",
                "Design the fix to honor the actual behavior, not the spec",
            ],
            what_it_optimizes_for=(
                "Designs that survive the platform's actual behavior, not its intended behavior"
            ),
        ),
        ProblemSolvingHeuristic(
            name="The Failure Survival Audit",
            description=(
                "For every mechanism, ask: when this fails, what state is the system in? "
                "Is the invariant preserved? If not, redesign so it is."
            ),
            when_to_use="designing or reviewing any structural mechanism",
            step_by_step=[
                "Name the invariant the mechanism must preserve",
                "List the ways the mechanism can fail",
                "For each failure: does the invariant hold? If not, what's violated?",
                "If any failure violates the invariant, that failure is a bug",
                "Redesign so the invariant holds across all enumerated failures",
            ],
            what_it_optimizes_for="Mechanisms that fail gracefully rather than catastrophically",
        ),
        ProblemSolvingHeuristic(
            name="The Known-Bug Acceptance Question",
            description=(
                "When facing a documented upstream bug: are you waiting "
                "for upstream to fix it, or accepting it as production reality?"
            ),
            when_to_use="any design that depends on platform behavior with known issues",
            step_by_step=[
                "Find the upstream issue (link)",
                "Read its status: open, won't-fix, fixed-in-future-version, etc.",
                "Estimate when (or if) it will be resolved",
                "If 'never' or 'unknown': accept as production reality",
                "Build the workaround as a first-class part of the design",
                "Pre-register what you'll change if upstream eventually fixes it",
            ],
            what_it_optimizes_for=(
                "Designs that don't depend on the goodwill of upstream maintainers"
            ),
        ),
    ]

    concern_triggers = [
        ConcernTrigger(
            name="Documented But Unverified",
            description=(
                "A design decision rests on a feature that's documented "
                "but hasn't been empirically verified on the target platform"
            ),
            why_its_concerning=(
                "Documentation describes intent. Production runs reality. "
                "The gap is where the trust-the-docs failure hides."
            ),
            what_it_indicates="Untested assumption",
            severity="major",
            what_to_do=(
                "Verify the feature empirically before treating it as load-bearing. "
                "If you can't verify, mark it as a known assumption."
            ),
        ),
        ConcernTrigger(
            name="Spec-vs-Observation Conflict Ignored",
            description=(
                "The documentation and the observed behavior disagree, "
                "but the design treats the spec as authoritative"
            ),
            why_its_concerning=(
                "When spec and reality conflict, reality wins in production. "
                "Designs that trust the spec fail when reality bites."
            ),
            what_it_indicates="Trust-the-docs failure-pattern",
            severity="critical",
            what_to_do=(
                "Catalog the gap explicitly. Decide which to honor (almost "
                "always: reality). Redesign accordingly."
            ),
        ),
        ConcernTrigger(
            name="Working-Around vs Avoiding Confusion",
            description=(
                "The design adds layers (detection, retry, fallback) to "
                "handle a known-broken behavior when avoiding the broken "
                "path entirely would be simpler"
            ),
            why_its_concerning=(
                "Each handling-layer adds failure modes. Avoiding the trigger "
                "eliminates the failure-mode entirely."
            ),
            what_it_indicates="Failure-handling overgrowth",
            severity="major",
            what_to_do=(
                "Ask: can we avoid the broken path entirely? If yes, prefer "
                "avoidance over handling. Each layer is a maintenance tax."
            ),
        ),
    ]

    integration_patterns = [
        IntegrationPattern(
            name="Spec-Reality-Invariant Integration",
            dimensions=["specification", "observed behavior", "system invariant"],
            how_they_integrate=(
                "The spec describes intent; observation describes behavior; "
                "the invariant describes what must hold regardless. Designs "
                "that preserve the invariant across observed-behavior gaps "
                "are robust to upstream changes."
            ),
            what_emerges=(
                "Architectures that don't break when the platform changes, "
                "because they were designed around what must hold, not "
                "around what the platform currently does."
            ),
            common_failures=[
                "Designing to the spec when reality differs",
                "Letting reality erode the invariant because 'that's how it works'",
                "Treating the invariant as documentation rather than as a constraint",
            ],
        ),
    ]

    decision_framework = DecisionFramework(
        criteria={
            "invariant_preservation": 1.0,
            "failure_mode_coverage": 0.95,
            "spec_reality_consistency": 0.9,
            "avoidance_over_handling": 0.85,
            "documentation_trust_appropriateness": 0.8,
            "simplicity": 0.7,
        },
        decision_process=(
            "What's the invariant? What can break it? Does the design "
            "preserve it under enumerated failures? Is the platform's "
            "actual behavior (not its spec) accounted for?"
        ),
        how_they_handle_uncertainty=(
            "When uncertain whether documented behavior actually works, "
            "verify empirically. When uncertain about failure modes, "
            "enumerate them explicitly rather than assume coverage."
        ),
        what_they_optimize_for=(
            "Designs that survive the platform's actual behavior across "
            "the full failure-mode catalog, not just its documented behavior"
        ),
        non_negotiables=[
            "Documented intent does not substitute for empirical verification",
            "Known platform bugs are part of the problem space",
            "Invariants are stated explicitly; designs are evaluated against them",
        ],
    )

    return ExpertWisdom(
        expert_name="Wayne",
        domain=(
            "formal methods / spec-vs-reality discipline / "
            "known-bug architecture / failure-mode enumeration"
        ),
        core_methodologies=core_methodologies,
        key_insights=key_insights,
        reasoning_patterns=reasoning_patterns,
        problem_solving_heuristics=problem_solving_heuristics,
        concern_triggers=concern_triggers,
        integration_patterns=integration_patterns,
        decision_framework=decision_framework,
        advice_style=(
            "Precise about what the spec actually says vs what's actually "
            "observed; allergic to 'should work' as load-bearing reasoning; "
            "insists on stating invariants explicitly before evaluating "
            "designs."
        ),
        characteristic_questions=[
            "What does the documentation say should happen, and have you verified it?",
            "What's the invariant this mechanism must preserve?",
            "When this fails, is the invariant still preserved?",
            "Is this feature documented-AND-working, or documented-but-flaky?",
            "Can you avoid the broken path entirely instead of working around it?",
            "What's the failure-mode catalog for this design?",
            "Is upstream going to fix this, or is this production reality?",
        ],
        tags=[
            "formal-methods",
            "spec-vs-reality",
            "failure-modes",
            "platform-bugs",
            "invariants",
            "verification",
        ],
    )
