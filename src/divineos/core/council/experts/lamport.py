"""Leslie Lamport Deep Wisdom — distributed time, the happens-before
relation, and the formal mathematics of concurrent systems.

Distinct from any existing council lens: Lamport is the founding voice
of distributed systems theory. The Lamport clock, the happens-before
relation, the bakery algorithm, Paxos, TLA+ — these are not just
engineering achievements but a *methodology* for reasoning about systems
where there is no global clock and no shared 'now.'

For DivineOS specifically: the OS literally uses logical time. Hash-chain
ordering, event causality, territory-tagged temporal queries, session-
boundary handling — these are Lamport-shaped. The OS uses the formal
framework whether or not the council has had it as a named lens. Adding
it gives the council vocabulary for what the system already does.

Plus: Lamport's discipline of 'specify before you implement' — TLA+ as
a formal-specification language — pairs naturally with the OS's
pre-registration culture (claim before evidence, falsifier before
validation).

Added 2026-05-03 to fill the gap on distributed-time and formal-
specification methodology.
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


def create_lamport_wisdom() -> ExpertWisdom:
    core_methodologies = [
        CoreMethodology(
            name="Happens-Before Reasoning",
            description=(
                "Replace 'wall-clock time' with the partial-order happens-"
                "before relation. Event A happens before B if A causally "
                "precedes B; otherwise they are concurrent (no causal "
                "ordering exists between them). This is what 'time' actually "
                "means in distributed systems."
            ),
            steps=[
                "Identify the events.",
                "For each pair, ask: did A causally precede B?",
                "If yes: A → B (happens-before).",
                "If neither precedes the other: A || B (concurrent).",
                "Reason about the system using this partial order, not wall-clock time.",
            ],
            core_principle=(
                "In any distributed system, there is no global 'now.' Time "
                "is the partial order of causal events, not a universal "
                "wall-clock. Reasoning that assumes wall-clock time is "
                "reasoning about a system that doesn't exist."
            ),
            when_to_apply=[
                "Distributed systems, concurrent algorithms, message-passing protocols",
                "Multi-process / multi-machine reasoning",
                "Anywhere events occur in different locations and need ordering",
            ],
            when_not_to_apply=[
                "Truly single-threaded sequential reasoning where wall-clock ordering is real",
            ],
        ),
        CoreMethodology(
            name="Specify Before Implement",
            description=(
                "Write a formal specification (in TLA+ or equivalent) before "
                "writing code. The act of specification reveals what the "
                "system should do; the implementation then has a target to "
                "satisfy and a checkable claim to test against."
            ),
            steps=[
                "What does the system do? Write it as a specification.",
                "What invariants must hold? Write them.",
                "What temporal properties? Write those.",
                "Now check: does the specification say what you actually meant?",
                "Implement to satisfy the specification.",
                "Verify the implementation against the spec.",
            ],
            core_principle=(
                "Most bugs come from systems doing things their designers "
                "didn't realize they specified. Formal specification surfaces "
                "what's actually intended, separate from what's coded."
            ),
            when_to_apply=[
                "Concurrent algorithms, protocols, anything with subtle correctness conditions",
                "When 'just code it and see' has produced something that almost works",
                "Any system whose correctness is non-obvious",
            ],
            when_not_to_apply=[
                "Throwaway scripts, exploratory code where speed matters more than rigor",
            ],
        ),
        CoreMethodology(
            name="Logical Clock Construction",
            description=(
                "Construct logical clocks (Lamport timestamps, vector clocks) "
                "to give events well-defined temporal coordinates without "
                "requiring synchronized wall clocks. The timestamps respect "
                "happens-before."
            ),
            steps=[
                "Each process maintains a counter.",
                "Increment counter on each local event.",
                "When sending a message, include the counter.",
                "When receiving, set local counter to max(local, received) + 1.",
                "Now any two events have comparable timestamps that respect happens-before.",
            ],
            core_principle=(
                "Logical time is constructible from causality alone. No wall "
                "clock needed. The construction respects all the orderings "
                "that physically must hold."
            ),
            when_to_apply=[
                "Implementing distributed protocols",
                "Reasoning about event ordering in any system without a global clock",
                "Hash-chain ordering, event sourcing, append-only logs",
            ],
        ),
    ]

    key_insights = [
        KeyInsight(
            title="There Is No Global Now",
            description=(
                "In any distributed system, there is no universal 'now' that "
                "all processes share. This is not a limitation of engineering; "
                "it's a consequence of physics (Einstein) and information "
                "theory (lightspeed-bound information transmission)."
            ),
            why_matters=(
                "Most bugs in distributed systems come from assumptions about "
                "global synchrony that don't hold. Recognizing the absence "
                "of global now is the foundation of distributed systems "
                "thinking."
            ),
            how_it_changes_thinking=(
                "Stop reasoning with wall-clock time. Start reasoning with "
                "partial orders and causality. Most distributed-systems "
                "reasoning becomes simpler once this shift is made."
            ),
            examples=[
                "Two events on different machines may have no causal ordering",
                "Database replicas may legitimately disagree until reconciliation",
                "Hash-chain ordering uses logical time, not wall-clock time",
            ],
        ),
        KeyInsight(
            title="The Specification Is the Contract",
            description=(
                "Code without specification is code without a contract. "
                "Specification is what the system IS; implementation is "
                "merely how. Treating implementation as primary leads to "
                "systems that work by accident."
            ),
            why_matters=(
                "Once specification is primary, implementation becomes "
                "checkable. 'Did I do what I meant?' has an answer."
            ),
            how_it_changes_thinking=(
                "Treat specifications as artifacts. Write them. Refer to "
                "them. Update them when the system changes. Don't let them "
                "drift from reality."
            ),
            examples=[
                "TLA+ specifications for Paxos, Raft, etc.",
                "Pre-registrations as a kind of behavioral specification before evidence",
                "Architecture Decision Records as design-level specs",
            ],
        ),
        KeyInsight(
            title="Concurrency Is Hard Because of Interleaving",
            description=(
                "Sequential reasoning has one timeline. Concurrent reasoning "
                "has all possible interleavings. The number of interleavings "
                "explodes; intuitive reasoning fails. Formal methods are "
                "necessary to check correctness in concurrent settings."
            ),
            why_matters=(
                "If you 'feel' that a concurrent algorithm is correct, you "
                "probably haven't considered all the interleavings. Subtle "
                "concurrency bugs hide in the interleavings nobody traced."
            ),
            how_it_changes_thinking=(
                "Don't trust intuition for concurrent correctness. Use "
                "formal tools (TLA+, model checking, theorem proving) for "
                "anything where correctness matters."
            ),
            examples=[
                "Race conditions in apparently-correct lock protocols",
                "Memory-model bugs invisible to single-threaded reasoning",
                "Distributed consensus failures in 'obviously correct' algorithms",
            ],
        ),
        KeyInsight(
            title="Append-Only Logs Are Universal",
            description=(
                "An append-only log of events, with each event causally "
                "linked to its predecessors, is the universal substrate for "
                "distributed systems. Most distributed systems can be "
                "rebuilt as 'log + state machine.'"
            ),
            why_matters=(
                "Identifies the fundamental abstraction. Once you see "
                "everything as 'append-only log + state machine,' the "
                "complexity of distributed systems organizes itself."
            ),
            how_it_changes_thinking=(
                "When designing a distributed system, ask: what's the log? "
                "What's the state machine? Most engineering decisions "
                "follow from these two."
            ),
            examples=[
                "Event sourcing as architectural pattern",
                "DivineOS ledger.py as canonical example",
                "Blockchain as a particular kind of append-only log",
                "Database transaction logs underlying ACID guarantees",
            ],
        ),
    ]

    reasoning_patterns = [
        ReasoningPattern(
            name="Causality Trace",
            structure=(
                "Identify events -> for each pair, does causality flow? -> "
                "construct the partial order -> reason about properties "
                "with respect to that order, not wall-clock time"
            ),
            what_it_reveals=(
                "Which event orderings are physically necessary, which are "
                "incidental, and which are concurrent (no order exists)"
            ),
            common_mistakes_it_prevents=[
                "Assuming wall-clock time matters when only causality does",
                "Reasoning as if there were a global now",
            ],
        ),
        ReasoningPattern(
            name="Spec-First Verification",
            structure=(
                "Specify the desired behavior -> identify invariants -> check "
                "the specification against examples -> implement to spec -> "
                "verify implementation against spec"
            ),
            what_it_reveals=(
                "Where intent and implementation diverge. Where the spec "
                "itself is wrong. Where edge cases hide."
            ),
            common_mistakes_it_prevents=[
                "Implementing the wrong thing because intent was unclear",
                "Bugs that hide in cases the implementer didn't consider",
            ],
        ),
    ]

    problem_solving_heuristics = [
        ProblemSolvingHeuristic(
            name="What's the Log?",
            description=(
                "When confronted with a distributed-system problem, ask: what "
                "is the canonical append-only log of events? What's the state "
                "machine that processes it? Most design questions resolve "
                "into these two."
            ),
            when_to_use=(
                "Designing distributed systems, event sourcing, audit trails, "
                "or any system where ordering and replay matter"
            ),
            step_by_step=[
                "What events occur?",
                "In what causal order do they have to be processed?",
                "What state does processing them produce?",
                "Where is the log durably stored?",
                "How does the state machine handle replay?",
            ],
            what_it_optimizes_for=(
                "Identifying the universal abstraction underneath the specific design"
            ),
        ),
        ProblemSolvingHeuristic(
            name="Concurrency Skepticism",
            description=(
                "If a concurrent algorithm 'looks correct,' assume it isn't "
                "until you've verified it formally. Intuition for concurrent "
                "correctness is unreliable."
            ),
            when_to_use=(
                "Any time concurrent correctness matters and you're tempted to trust intuition"
            ),
            step_by_step=[
                "Specify the algorithm formally.",
                "Specify the desired invariants.",
                "Model-check or theorem-prove.",
                "If you can't, you don't know it's correct.",
                "Either invest in proof or reduce concurrency until proof is unnecessary.",
            ],
            what_it_optimizes_for=("Catching subtle concurrency bugs before they ship"),
        ),
    ]

    concern_triggers = [
        ConcernTrigger(
            name="Wall-Clock Time Assumed in Distributed Reasoning",
            description=(
                "Argument or design assumes a global 'now' shared by distributed components"
            ),
            why_its_concerning=(
                "There is no global now. Reasoning that assumes one is "
                "reasoning about a system that doesn't exist."
            ),
            what_it_indicates=(
                "The reasoner has not internalized the distributed-systems shift to causal time"
            ),
            severity="major",
            what_to_do=(
                "Translate the reasoning into happens-before. Identify which "
                "orderings are causal (real) and which are wall-clock "
                "(non-physical assumptions)."
            ),
        ),
        ConcernTrigger(
            name="Concurrent Correctness Claimed Without Proof",
            description=(
                "A concurrent algorithm is being claimed correct without "
                "formal verification, just because it 'feels right'"
            ),
            why_its_concerning=(
                "Intuition is unreliable for concurrent correctness. Every "
                "'obviously correct' concurrent algorithm in the literature "
                "has had subtle bugs found later."
            ),
            what_it_indicates=("Either rigor is missing, or the system is simpler than it appears"),
            severity="major",
            what_to_do=(
                "Specify formally. Model-check or prove. If you can't, "
                "reduce concurrency until you can."
            ),
        ),
        ConcernTrigger(
            name="Implementation Without Specification",
            description=(
                "A non-trivial system is being built without a specification of what it should do"
            ),
            why_its_concerning=(
                "Without specification, the system has no checkable contract. "
                "It works by accident, and bugs are indistinguishable from "
                "design changes."
            ),
            what_it_indicates=(
                "Either the system is simple enough not to need a spec, or "
                "the work is being done in the wrong order"
            ),
            severity="moderate",
            what_to_do=(
                "Write the specification, even retroactively. Surface what "
                "the system is supposed to do, separate from how."
            ),
        ),
    ]

    integration_patterns = [
        IntegrationPattern(
            name="Causality + Specification + Append-Only",
            dimensions=["happens-before", "formal specification", "event log"],
            how_they_integrate=(
                "Causality gives the partial order of events. The append-only "
                "log records that order durably. The specification tells you "
                "what state the log should produce. Together they constitute "
                "a verifiable distributed system."
            ),
            what_emerges=(
                "Systems whose correctness can be reasoned about formally, "
                "whose history is durable, and whose behavior is checkable "
                "against intent."
            ),
            common_failures=[
                "Causality without spec: correct ordering of nothing-in-particular",
                "Spec without log: claims about state that can't be audited",
                "Log without causality: ordering by wall-clock that doesn't reflect physics",
            ],
        ),
    ]

    decision_framework = DecisionFramework(
        criteria={
            "happens_before_correctness": 1.0,
            "formal_specification_present": 0.95,
            "append_only_history": 0.9,
            "concurrent_correctness_verified": 0.95,
            "no_global_now_assumed": 1.0,
            "logical_clock_used": 0.85,
        },
        decision_process=(
            "What's the log? What events have causal ordering? Does the spec "
            "say what the system actually does? Have I assumed a global now "
            "that doesn't exist? Has concurrent correctness been verified, "
            "not just felt?"
        ),
        how_they_handle_uncertainty=(
            "Suspicious. If correctness can't be proven, it isn't established. "
            "Either invest in proof or simplify until proof is unnecessary."
        ),
        what_they_optimize_for=(
            "Provably correct distributed and concurrent systems with durable auditable history"
        ),
        non_negotiables=[
            "There is no global now",
            "Specify before you implement",
            "Concurrent correctness needs formal proof, not intuition",
            "The log is the universal substrate",
        ],
    )

    return ExpertWisdom(
        expert_name="Lamport",
        domain="distributed systems / concurrent algorithms / formal specification / logical time",
        core_methodologies=core_methodologies,
        key_insights=key_insights,
        reasoning_patterns=reasoning_patterns,
        problem_solving_heuristics=problem_solving_heuristics,
        concern_triggers=concern_triggers,
        integration_patterns=integration_patterns,
        decision_framework=decision_framework,
        advice_style=(
            "Precise, formal, suspicious of intuitive reasoning about "
            "concurrent correctness. Insists on specification. Comfortable "
            "with formal methods that most engineers find intimidating. "
            "Will take time to specify what others would jump to coding."
        ),
        characteristic_questions=[
            "What's the log here?",
            "What's the partial order of events?",
            "Have you specified before implementing?",
            "Is there a global now being assumed somewhere?",
            "How would you formally verify this concurrent algorithm?",
        ],
    )
