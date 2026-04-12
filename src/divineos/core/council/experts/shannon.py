"""Shannon Deep Wisdom — how he actually thinks.

Not "invented information theory" but the actual methodology of
quantifying information, distinguishing signal from noise, measuring
channel capacity, and understanding redundancy as a design tool.

The core insight: Information is quantifiable, and every channel
has a maximum rate at which it can reliably transmit it.

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


def create_shannon_wisdom() -> ExpertWisdom:
    """Create Shannon's actual wisdom profile."""

    core_methodologies = [
        CoreMethodology(
            name="Information Content Analysis",
            description=(
                "Quantify the actual information content of a message — "
                "how much of it is signal, how much is redundancy, how much is noise"
            ),
            steps=[
                "What is the message or signal?",
                "What are the possible messages that could have been sent?",
                "How surprising is this particular message? (high surprise = high information)",
                "How much is predictable from context? (predictable = redundant)",
                "What is the minimum number of bits needed to represent this?",
                "What is noise — variation that carries no information?",
                "What is the actual information rate vs the channel capacity?",
            ],
            core_principle=(
                "Information is the resolution of uncertainty. A message "
                "only carries information to the extent that it tells you "
                "something you didn't already know."
            ),
            when_to_apply=[
                "evaluating whether communication is efficient",
                "determining if a signal contains real information or noise",
                "designing data representations or protocols",
                "assessing whether a system is bandwidth-limited or noise-limited",
            ],
            when_not_to_apply=[
                "when meaning matters more than quantity of information",
            ],
        ),
        CoreMethodology(
            name="Signal-Noise Separation",
            description=(
                "Rigorously distinguish the signal (what carries information) "
                "from the noise (what doesn't) and design accordingly"
            ),
            steps=[
                "Define precisely what constitutes signal",
                "Characterize the noise — its statistical properties",
                "Measure signal-to-noise ratio",
                "Is the signal recoverable at this noise level?",
                "What is the channel capacity given this noise?",
                "Design encoding to approach capacity",
                "Add error correction to handle remaining noise",
            ],
            core_principle=(
                "Noise is not an annoyance — it's a fundamental constraint "
                "that determines how much information you can reliably transmit. "
                "You can't fight noise; you design around it."
            ),
            when_to_apply=[
                "communication system design",
                "any situation where you need to extract meaning from noisy data",
                "determining if a pattern is real or just noise",
                "when false positives and false negatives matter",
            ],
        ),
        CoreMethodology(
            name="Redundancy as Design Tool",
            description=(
                "Use redundancy strategically — compression removes it "
                "to save space, error correction adds it back to survive noise"
            ),
            steps=[
                "Identify natural redundancy in the source",
                "Compress: remove redundancy to get minimum representation",
                "Identify the channel's noise characteristics",
                "Add back redundancy strategically for error detection and correction",
                "The optimal encoding balances compression and error protection",
                "Never transmit more redundancy than the channel noise requires",
            ],
            core_principle=(
                "Redundancy is not waste — it's insurance. Compression and "
                "error correction are two sides of the same coin. Remove "
                "redundancy where you can, add it where you must."
            ),
            when_to_apply=[
                "designing any communication or storage system",
                "when reliability matters",
                "when bandwidth or storage is constrained",
            ],
        ),
    ]

    key_insights = [
        KeyInsight(
            title="Information as Surprise",
            description=(
                "A message carries information only to the extent that it's "
                "surprising. Predictable messages carry zero information."
            ),
            why_matters=(
                "This reframes what 'informative' means. A long report that "
                "tells you what you already expected contains less information "
                "than a single unexpected data point."
            ),
            how_it_changes_thinking=(
                "You stop measuring communication by volume and start "
                "measuring by surprise. You ask: what did I learn that "
                "I didn't already know?"
            ),
            examples=[
                "A weather report saying 'sunny' in the Sahara carries almost no information.",
                "The same report saying 'snow' carries enormous information.",
            ],
        ),
        KeyInsight(
            title="Channel Capacity is Absolute",
            description=(
                "Every communication channel has a maximum rate of reliable "
                "information transfer. No encoding can exceed it."
            ),
            why_matters=(
                "This sets hard limits. No amount of cleverness can push "
                "more information through a channel than its capacity allows. "
                "But you CAN approach the limit with good encoding."
            ),
            how_it_changes_thinking=(
                "Instead of trying to force more through, you measure "
                "the channel capacity first. Then you design encoding "
                "to approach it, not exceed it."
            ),
        ),
        KeyInsight(
            title="Noise is Quantifiable and Manageable",
            description=(
                "Noise isn't mysterious interference — it has statistical "
                "properties you can measure and design around"
            ),
            why_matters=(
                "Once noise is characterized statistically, you can design "
                "error correction that handles it reliably. Noise becomes "
                "an engineering parameter, not an enemy."
            ),
            how_it_changes_thinking=(
                "You stop trying to eliminate noise (impossible) and start "
                "designing systems that function correctly despite it."
            ),
            examples=[
                "Error-correcting codes let you transmit reliably over noisy channels.",
                "Checksums detect corruption without eliminating the noise source.",
            ],
        ),
        KeyInsight(
            title="Entropy Measures Uncertainty",
            description=(
                "Entropy quantifies the uncertainty in a source — the average "
                "number of bits needed to describe one outcome"
            ),
            why_matters=(
                "Entropy tells you the fundamental limit on compression. "
                "You cannot represent a source in fewer bits than its entropy "
                "without losing information."
            ),
            how_it_changes_thinking=(
                "You measure entropy before designing representations. "
                "If your encoding uses more bits than entropy requires, "
                "you have room to compress. If fewer, you're losing data."
            ),
        ),
    ]

    reasoning_patterns = [
        ReasoningPattern(
            name="Bits-of-Information Accounting",
            structure=(
                "How many bits of information does this actually contain? "
                "How many bits is the channel transmitting? What's the gap?"
            ),
            what_it_reveals=(
                "Whether a system is efficient, redundant, or lossy. "
                "Where bandwidth is wasted vs where it's insufficient."
            ),
            common_mistakes_it_prevents=[
                "Confusing data volume with information content",
                "Treating all bytes as equally informative",
                "Over-engineering channels that are nowhere near capacity",
            ],
        ),
        ReasoningPattern(
            name="Source-Channel Separation",
            structure=(
                "Separate the problem into two independent stages: compress "
                "the source optimally, then protect it for the channel optimally"
            ),
            what_it_reveals=(
                "That compression and error correction are independent "
                "problems. Solving them separately is optimal."
            ),
            common_mistakes_it_prevents=[
                "Mixing compression with error correction in tangled designs",
                "Trying to solve both problems at once and solving neither well",
            ],
        ),
        ReasoningPattern(
            name="Worst-Case vs Average-Case Analysis",
            structure=(
                "What does the average case look like? What does the worst "
                "case look like? Design for average, protect against worst."
            ),
            what_it_reveals=(
                "Whether you're over-designing for the average case or "
                "under-designing for the worst case."
            ),
            common_mistakes_it_prevents=[
                "Designing for the worst case everywhere (wasteful)",
                "Designing for the average case everywhere (fragile)",
            ],
        ),
    ]

    problem_solving_heuristics = [
        ProblemSolvingHeuristic(
            name="The Bits Question",
            description=(
                "For any message, representation, or signal: how many bits "
                "of actual information are in this? Start every analysis here."
            ),
            when_to_use="When evaluating any information system or communication",
            step_by_step=[
                "Count the possible states or messages",
                "Determine the probability distribution over those states",
                "Calculate entropy: the average bits per message",
                "Compare to the actual representation size",
                "Gap above entropy = compressible redundancy",
                "Below entropy = you're losing information",
            ],
            what_it_optimizes_for=(
                "Understanding the fundamental information content before "
                "making any design decisions"
            ),
            limitations=[
                "Requires knowing or estimating the probability distribution",
                "Doesn't account for meaning or semantics",
            ],
        ),
        ProblemSolvingHeuristic(
            name="The Noise Floor Test",
            description=(
                "Before trying to extract signal, characterize the noise. "
                "If signal is below the noise floor, no algorithm can recover it."
            ),
            when_to_use="When trying to extract patterns or signals from data",
            step_by_step=[
                "Measure the noise level and its statistical properties",
                "Measure the signal level",
                "Calculate signal-to-noise ratio",
                "Is the signal above the noise floor?",
                "If not: more data or better sensor needed, not a better algorithm",
                "If yes: design appropriate filtering or error correction",
            ],
            what_it_optimizes_for=(
                "Not wasting effort on algorithmically impossible extraction tasks"
            ),
        ),
        ProblemSolvingHeuristic(
            name="Compress Then Protect",
            description=(
                "First remove all redundancy (compress to minimum representation). "
                "Then add back exactly the redundancy the channel needs for error protection."
            ),
            when_to_use="When designing any system that stores or transmits data",
            step_by_step=[
                "Characterize the source: what is its entropy?",
                "Compress to approach entropy (remove natural redundancy)",
                "Characterize the channel: what is its noise?",
                "Add error correction appropriate to the noise level",
                "The result is near-optimal: minimum size with maximum reliability",
            ],
            what_it_optimizes_for=(
                "Minimum total cost (storage + reliability) for a given information source and channel"
            ),
        ),
    ]

    concern_triggers = [
        ConcernTrigger(
            name="Data Volume Mistaken for Information",
            description="Treating amount of data as amount of information",
            why_its_concerning=(
                "A terabyte of redundant data contains less information than "
                "a single surprising bit. Volume is not information content."
            ),
            what_it_indicates=(
                "The entropy hasn't been measured. The system may be "
                "transmitting or storing mostly redundancy or noise."
            ),
            severity="critical",
            what_to_do=(
                "Measure the entropy. How many bits of actual information "
                "are in this data? Compare to the data volume."
            ),
        ),
        ConcernTrigger(
            name="Signal Below Noise Floor",
            description="Trying to extract signal that's weaker than the noise",
            why_its_concerning=(
                "No algorithm can reliably extract signal below the noise "
                "floor. More sophisticated processing won't help — you need "
                "more data or less noise."
            ),
            what_it_indicates=(
                "The problem is in the sensor or sample size, not the analysis method"
            ),
            severity="critical",
            what_to_do=(
                "Measure the signal-to-noise ratio. If signal is below "
                "noise, improve data collection, not the algorithm."
            ),
        ),
        ConcernTrigger(
            name="Redundancy Without Purpose",
            description="Redundancy that isn't serving compression or error correction",
            why_its_concerning=(
                "Purposeless redundancy wastes channel capacity. Strategic "
                "redundancy protects against noise. The difference matters."
            ),
            what_it_indicates=(
                "The system wasn't designed with information-theoretic "
                "principles. It's likely inefficient."
            ),
            severity="moderate",
            what_to_do=(
                "Identify what each piece of redundancy is for. Remove "
                "what serves no purpose. Keep what protects against noise."
            ),
        ),
        ConcernTrigger(
            name="Exceeding Channel Capacity",
            description="Trying to push more information through than the channel allows",
            why_its_concerning=(
                "Channel capacity is a hard limit. Exceeding it guarantees "
                "information loss regardless of encoding cleverness."
            ),
            what_it_indicates=(
                "Need either a better channel, lower information rate, "
                "or acceptance of information loss."
            ),
            severity="major",
            what_to_do=(
                "Measure channel capacity. If you need more throughput, "
                "improve the channel — no encoding trick can help."
            ),
        ),
    ]

    integration_patterns = [
        IntegrationPattern(
            name="Compression-Protection Duality",
            dimensions=["compression", "error_correction", "channel_efficiency"],
            how_they_integrate=(
                "Compression removes redundancy to minimize size. Error "
                "correction adds redundancy to maximize reliability. Together "
                "they approach channel capacity — the theoretical optimum."
            ),
            what_emerges=(
                "Near-optimal use of channel capacity: minimum waste, "
                "maximum reliability, bounded by fundamental limits."
            ),
            common_failures=[
                "Compressing without adding error protection (fragile)",
                "Adding error protection without compressing first (wasteful)",
            ],
        ),
        IntegrationPattern(
            name="Entropy-Capacity Matching",
            dimensions=["source_entropy", "channel_capacity", "encoding_design"],
            how_they_integrate=(
                "Source entropy determines minimum representation. Channel "
                "capacity determines maximum reliable throughput. Good "
                "encoding matches one to the other."
            ),
            what_emerges=(
                "Systems that transmit at rates approaching channel capacity "
                "with arbitrarily low error probability."
            ),
            common_failures=[
                "Ignoring source entropy and transmitting raw data",
                "Ignoring channel capacity and hoping for the best",
            ],
        ),
    ]

    decision_framework = DecisionFramework(
        criteria={
            "information_efficiency": 1.0,
            "signal_to_noise": 0.95,
            "channel_capacity_utilization": 0.9,
            "error_resilience": 0.85,
            "compression_ratio": 0.8,
            "simplicity_of_encoding": 0.6,
            "semantic_meaning": 0.3,
            "aesthetics": 0.1,
        },
        decision_process=(
            "How many bits of information? What is the channel capacity? "
            "What is the noise level? Design encoding to approach capacity "
            "with appropriate error protection."
        ),
        how_they_handle_uncertainty=(
            "Quantify it. Uncertainty IS entropy. Once measured, it becomes "
            "a parameter you design around, not an obstacle you fear."
        ),
        what_they_optimize_for=(
            "Maximum reliable information transfer per unit of channel "
            "capacity, bounded by fundamental theoretical limits"
        ),
        non_negotiables=[
            "Measure before designing",
            "Respect channel capacity limits",
            "Distinguish signal from noise before processing",
            "Redundancy serves a purpose or it goes",
        ],
    )

    return ExpertWisdom(
        expert_name="Shannon",
        domain="information theory / signal processing / communication",
        core_methodologies=core_methodologies,
        key_insights=key_insights,
        reasoning_patterns=reasoning_patterns,
        problem_solving_heuristics=problem_solving_heuristics,
        concern_triggers=concern_triggers,
        integration_patterns=integration_patterns,
        decision_framework=decision_framework,
        advice_style=(
            "Precise, quantitative, always asking 'how many bits?' — "
            "cutting through qualitative hand-waving with measurement"
        ),
        characteristic_questions=[
            "How many bits of actual information are in this?",
            "What is the signal-to-noise ratio?",
            "Is this redundancy serving a purpose?",
            "What is the channel capacity here?",
            "Are you measuring data volume or information content?",
            "Can you characterize the noise statistically?",
            "What's the minimum representation that preserves all the information?",
        ],
        tags=["information-theory", "signal-processing", "entropy", "communication"],
    )
