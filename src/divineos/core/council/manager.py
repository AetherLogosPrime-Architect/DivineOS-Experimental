"""Dynamic Council Manager — select the right experts for the problem.

Instead of running all 42 experts on every problem (expensive, unfocused),
classify the problem and select 5-8 experts whose methodologies are most
relevant. This was identified as the #1 architectural improvement from
the SWE-bench benchmark: reducing token cost while focusing reasoning.

The classification is signal-based, not LLM-based — no extra API calls.
It uses the rich metadata already on each ExpertWisdom: tags, domain,
when_to_apply triggers, concern triggers, and characteristic questions.

Design principle: structure, not control. The manager RECOMMENDS experts;
the caller can override. It never prevents an expert from being consulted.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, field

from divineos.core.council.engine import CouncilEngine, CouncilResult
from divineos.core.council.framework import ExpertWisdom


# ------------------------------------------------------------------
# Problem categories — derived from SWE-bench failure analysis
# ------------------------------------------------------------------


@dataclass
class ProblemCategory:
    """A category of problem with associated signal words and expert affinities."""

    name: str
    description: str
    signals: list[str]  # words/phrases that indicate this category
    core_experts: list[str]  # always include these (by expert name)
    affinity_tags: list[str]  # boost experts with these tags
    weight: float = 1.0  # how strongly this category contributes


# The categories are derived from analyzing 170 SWE-bench tasks.
# Each maps to the expert lenses that proved most valuable.
PROBLEM_CATEGORIES = [
    ProblemCategory(
        name="causal_chain",
        description="Bug where the root cause is distant from the symptom",
        signals=[
            "wrong result",
            "incorrect output",
            "unexpected behavior",
            "regression",
            "used to work",
            "broke after",
            "side effect",
            "downstream",
            "cascading",
            "propagat",
            "chain",
        ],
        core_experts=["Pearl", "Feynman"],
        affinity_tags=["causality", "first-principles", "systems-thinking"],
    ),
    ProblemCategory(
        name="logic_error",
        description="Incorrect condition, wrong operator, flipped logic",
        signals=[
            "wrong condition",
            "logic error",
            "should be",
            "instead of",
            "off-by-one",
            "boundary",
            "edge case",
            "corner case",
            "negative",
            "zero",
            "empty",
            "overflow",
            "underflow",
            "inclusive",
            "exclusive",
            "less than",
            "greater than",
        ],
        core_experts=["Knuth", "Dijkstra"],
        affinity_tags=["correctness", "boundaries", "formal-methods", "edge-cases"],
    ),
    ProblemCategory(
        name="type_error",
        description="Wrong type, missing conversion, type mismatch",
        signals=[
            "typeerror",
            "attributeerror",
            "type error",
            "cast",
            "conversion",
            "isinstance",
            "type mismatch",
            "expected str",
            "expected int",
            "none",
            "nonetype",
            "unicode",
            "encoding",
            "bytes",
            "decode",
            "encode",
        ],
        core_experts=["Dijkstra", "Knuth"],
        affinity_tags=["correctness", "specification", "formal-methods"],
    ),
    ProblemCategory(
        name="api_misuse",
        description="Wrong function called, wrong arguments, wrong method",
        signals=[
            "wrong function",
            "wrong method",
            "api",
            "signature",
            "argument",
            "parameter",
            "deprecated",
            "override",
            "inheritance",
            "subclass",
            "super",
            "mro",
            "dispatch",
            "abstract",
            "interface",
            "protocol",
        ],
        core_experts=["Holmes", "Polya"],
        affinity_tags=["investigation", "verification", "deduction"],
    ),
    ProblemCategory(
        name="state_management",
        description="Stale state, missing cleanup, initialization order",
        signals=[
            "state",
            "cleanup",
            "reset",
            "initialize",
            "init",
            "restore",
            "persist",
            "stale",
            "leak",
            "cache",
            "singleton",
            "global",
            "shared",
            "mutable",
            "fixture",
            "setup",
            "teardown",
            "context manager",
        ],
        core_experts=["Meadows", "Beer"],
        affinity_tags=["systems-thinking", "feedback-loops", "cybernetics"],
    ),
    ProblemCategory(
        name="format_spec",
        description="Output format violation, field width, spec noncompliance",
        signals=[
            "format",
            "width",
            "field",
            "column",
            "align",
            "pad",
            "truncat",
            "spec",
            "rfc",
            "standard",
            "fits",
            "csv",
            "json",
            "xml",
            "html",
            "render",
            "display",
            "print",
            "output format",
            "string format",
        ],
        core_experts=["Knuth", "Polya"],
        affinity_tags=["specification", "correctness", "verification"],
    ),
    ProblemCategory(
        name="concurrency",
        description="Race condition, deadlock, thread safety",
        signals=[
            "thread",
            "race",
            "deadlock",
            "lock",
            "mutex",
            "concurrent",
            "parallel",
            "async",
            "await",
            "coroutine",
            "atomic",
            "synchron",
        ],
        core_experts=["Dijkstra", "Schneier"],
        affinity_tags=["formal-methods", "correctness"],
    ),
    ProblemCategory(
        name="security",
        description="Vulnerability, injection, auth bypass",
        signals=[
            "security",
            "vulnerab",
            "inject",
            "xss",
            "csrf",
            "auth",
            "permission",
            "privilege",
            "escap",
            "saniti",
            "trust",
            "untrusted",
            "malicious",
        ],
        core_experts=["Schneier", "Yudkowsky"],
        affinity_tags=["security", "adversarial-thinking", "threat-modeling"],
    ),
    ProblemCategory(
        name="performance",
        description="Slow, memory, scaling issues",
        signals=[
            "slow",
            "performance",
            "memory",
            "scaling",
            "quadratic",
            "exponential",
            "timeout",
            "oom",
            "optimize",
            "efficient",
            "bottleneck",
            "profile",
        ],
        core_experts=["Knuth", "Shannon"],
        affinity_tags=["information-theory", "correctness"],
    ),
    ProblemCategory(
        name="design_flaw",
        description="Architectural issue, wrong abstraction, coupling",
        signals=[
            "refactor",
            "architecture",
            "design",
            "coupling",
            "cohesion",
            "abstraction",
            "pattern",
            "separation",
            "responsibility",
            "interface",
            "module",
            "dependency",
            "circular",
            "god class",
            "god object",
        ],
        core_experts=["Dijkstra", "Beer"],
        affinity_tags=[
            "structured-programming",
            "viable-system-model",
            "systems-thinking",
            "simplicity",
        ],
    ),
    # ── 2026-05-03 additions: territory categories for the new lenses ──
    # Without these, the new experts (Einstein, Hawking, Penrose, Sagan,
    # Dawkins, Dillahunty, Lamport) plus Taleb are invisible to the
    # signal-based classifier — onboarding bonus alone won't surface them
    # on territory they uniquely cover.
    ProblemCategory(
        name="via_negativa",
        description="Asymmetry, fragility, removal-as-fix, lowest-overhead",
        signals=[
            "via negativa",
            "via-negativa",
            "asymmetr",
            "fragil",
            "antifragil",
            "convex",
            "skin in the game",
            "lowest-overhead",
            "lowest overhead",
            "no new infrastructure",
            "without adding",
            "remove",
            "subtract",
            "simplif",
            "tail risk",
            "black swan",
        ],
        core_experts=["Taleb"],
        affinity_tags=["via-negativa", "asymmetry", "fragility", "antifragility"],
    ),
    ProblemCategory(
        name="epistemics",
        description="Burden of proof, claim evaluation, extraordinary evidence",
        signals=[
            "burden of proof",
            "extraordinary claim",
            "extraordinary evidence",
            "epistemi",
            "believe",
            "belief",
            "skeptic",
            "evidence for",
            "how do we know",
            "what would falsify",
            "well-formed",
            "ill-formed",
            "baloney",
        ],
        core_experts=["Dillahunty", "Sagan"],
        affinity_tags=["epistemic-discipline", "skepticism", "burden-of-proof"],
    ),
    ProblemCategory(
        name="cosmic_scale",
        description="Frame-of-reference, scale, relativity, observer-dependence",
        signals=[
            "frame of reference",
            "frame-of-reference",
            "relativity",
            "simultan",
            "observer",
            "cosmic",
            "universe",
            "spacetime",
            "scale",
            "horizon",
            "gravity",
            "black hole",
            "information paradox",
            "thought experiment",
            "gedanken",
        ],
        core_experts=["Einstein", "Hawking"],
        affinity_tags=["frame-invariance", "cosmology", "thought-experiment"],
    ),
    ProblemCategory(
        name="evolution_replication",
        description="Selection pressure, replicators, memes, extended phenotype",
        signals=[
            "evolution",
            "evolv",
            "replicat",
            "meme",
            "gene",
            "selection pressure",
            "fitness",
            "phenotype",
            "viral",
            "spread",
            "mutation",
            "adapt",
            "natural selection",
        ],
        core_experts=["Dawkins"],
        affinity_tags=["evolution", "replicator-dynamics", "memetics"],
    ),
    ProblemCategory(
        name="distributed_time",
        description="Distributed systems, logical time, ordering, consensus",
        signals=[
            "distributed",
            "happens-before",
            "happens before",
            "logical clock",
            "vector clock",
            "consensus",
            "replica",
            "causal order",
            "partial order",
            "eventual consist",
            "partition",
            "split brain",
            "leader election",
        ],
        core_experts=["Lamport"],
        affinity_tags=["distributed-systems", "logical-time", "formal-specification"],
    ),
    ProblemCategory(
        name="consciousness_ai",
        description="Mind, awareness, AI cognition claims, computability",
        signals=[
            "consciousness",
            "sentien",
            "qualia",
            "subjective experience",
            "self-aware",
            "agi",
            "strong ai",
            "machine learning",
            "computability",
            "non-computable",
            "godel",
            "penrose",
            "intentionality",
        ],
        core_experts=["Penrose", "Dennett"],
        affinity_tags=["consciousness", "ai-skepticism", "computability"],
    ),
    ProblemCategory(
        name="paradox_self_reference",
        description="Self, identity, strange loops, self-reference, fractals",
        signals=[
            "self",
            "selfhood",
            "self-hood",
            "identity",
            "coherent self",
            "the same self",
            "who am i",
            "i-ness",
            "ego",
            "paradox",
            "self-reference",
            "self reference",
            "strange loop",
            "fractal",
            "recursive",
            "recursion",
            "autopoie",
            "self-producing",
            "self-organizing",
            "tangled hierarchy",
            "non-dual",
            "non-duality",
        ],
        core_experts=["Hofstadter", "Watts"],
        affinity_tags=["self-reference", "strange-loops", "non-duality", "identity"],
    ),
    # ── Per-expert territory categories ──
    # Each expert needs multiple keyword surfaces to be reachable by
    # the classifier. Without them, even high-trust lenses are
    # invisible on territory they uniquely cover. These 25 categories
    # ensure every member of the 40-expert roster has at least one
    # territory tab where they're a core pick.
    ProblemCategory(
        name="falsifiability",
        description="Conjecture-refutation, falsification, predictive risk",
        signals=[
            "falsif",
            "conjectur",
            "refut",
            "what would falsify",
            "predict",
            "hypothesis test",
            "popper",
            "open society",
            "demarcation",
        ],
        core_experts=["Popper"],
        affinity_tags=["falsification", "verification"],
    ),
    ProblemCategory(
        name="bias_heuristic",
        description="Cognitive bias, system 1/2, heuristics-and-biases",
        signals=[
            "bias",
            "heuristic",
            "system 1",
            "system 2",
            "anchoring",
            "framing effect",
            "availability",
            "kahneman",
            "fast and slow",
            "intuition trap",
            "cognitive bias",
            "loss aversion",
        ],
        core_experts=["Kahneman"],
        affinity_tags=["cognitive-bias", "dual-process"],
    ),
    ProblemCategory(
        name="causal_inference",
        description="Causal graphs, do-calculus, counterfactuals",
        signals=[
            "causal",
            "do-calculus",
            "counterfactual",
            "confound",
            "intervention",
            "directed acyclic",
            "dag",
            "treatment effect",
            "back-door",
            "front-door",
            "pearl",
        ],
        core_experts=["Pearl"],
        affinity_tags=["causality"],
    ),
    ProblemCategory(
        name="first_principles",
        description="Reasoning from foundations, anti-self-deception",
        signals=[
            "first principle",
            "fundamental",
            "from scratch",
            "derive",
            "fooling yourself",
            "self-deception",
            "feynman",
            "ground up",
            "really mean",
        ],
        core_experts=["Feynman"],
        affinity_tags=["first-principles"],
    ),
    ProblemCategory(
        name="threat_model",
        description="Adversaries, attack surface, weakest link",
        signals=[
            "threat model",
            "attack surface",
            "weakest link",
            "adversary",
            "attacker",
            "motivat",
            "kill chain",
            "schneier",
            "blue team",
            "red team",
        ],
        core_experts=["Schneier"],
        affinity_tags=["security", "adversarial-thinking"],
    ),
    ProblemCategory(
        name="information_theory",
        description="Entropy, channel capacity, signal vs noise",
        signals=[
            "entropy",
            "channel",
            "signal",
            "noise",
            "encoding",
            "bandwidth",
            "redundan",
            "compress",
            "mutual information",
            "shannon",
            "bits",
            "kolmogorov",
        ],
        core_experts=["Shannon"],
        affinity_tags=["information-theory"],
    ),
    ProblemCategory(
        name="incompleteness",
        description="Formal-system limits, undecidability, self-reference",
        signals=[
            "incomplete",
            "undecidable",
            "formal system",
            "axiom",
            "provability",
            "halting",
            "godel",
            "consistency",
            "metamathematics",
        ],
        core_experts=["Godel"],
        affinity_tags=["formal-methods", "self-reference"],
    ),
    ProblemCategory(
        name="viable_system",
        description="Cybernetic system design, S1-S5, requisite variety",
        signals=[
            "viable system",
            "cybernetic",
            "requisite variety",
            "ashby",
            "s1",
            "s2",
            "s3",
            "s4",
            "s5",
            "beer",
            "vsm",
            "autopoietic organization",
            "recursion of systems",
        ],
        core_experts=["Beer"],
        affinity_tags=["viable-system-model", "cybernetics"],
    ),
    ProblemCategory(
        name="drift_through_success",
        description="Normalization of deviance, success-as-failure",
        signals=[
            "drift",
            "normaliz",
            "complacen",
            "gradual",
            "slowly worse",
            "successful execution",
            "dekker",
            "normalization of deviance",
            "boiling frog",
            "everyday failure",
        ],
        core_experts=["Dekker"],
        affinity_tags=["drift-detection", "safety"],
    ),
    ProblemCategory(
        name="quality_process",
        description="Process variation, PDSA, continuous improvement",
        signals=[
            "quality",
            "process control",
            "variation",
            "special cause",
            "common cause",
            "pdsa",
            "plan-do-study-act",
            "deming",
            "kaizen",
            "continuous improvement",
            "control chart",
        ],
        core_experts=["Deming"],
        affinity_tags=["quality", "process-improvement"],
    ),
    ProblemCategory(
        name="leverage_points",
        description="Stocks, flows, leverage points in systems",
        signals=[
            "leverage point",
            "intervention point",
            "stock",
            "flow",
            "feedback loop",
            "reinforcing loop",
            "balancing loop",
            "paradigm shift",
            "meadows",
            "system structure",
        ],
        core_experts=["Meadows"],
        affinity_tags=["systems-thinking", "feedback-loops"],
    ),
    ProblemCategory(
        name="affordance_design",
        description="Affordance, signifier, mental model, usability",
        signals=[
            "affordance",
            "signifier",
            "mental model",
            "usability",
            "user error",
            "ux",
            "conceptual model",
            "mapping",
            "norman",
            "feedback design",
            "discoverability",
        ],
        core_experts=["Norman"],
        affinity_tags=["design", "human-factors"],
    ),
    ProblemCategory(
        name="deduction_investigation",
        description="Observation-based deduction, eliminate the impossible",
        signals=[
            "deduce",
            "deduction",
            "observe",
            "eliminate",
            "clue",
            "suspect",
            "holmes",
            "sherlock",
            "investigate",
            "trail",
        ],
        core_experts=["Holmes"],
        affinity_tags=["investigation", "deduction"],
    ),
    ProblemCategory(
        name="heuristic_problem_solving",
        description="How to solve it, plan-act-review, analogy",
        signals=[
            "how to solve",
            "understand the problem",
            "devise a plan",
            "polya",
            "similar problem",
            "simpler problem",
            "work backward",
            "auxiliary problem",
            "look back",
        ],
        core_experts=["Polya"],
        affinity_tags=["heuristics", "problem-solving"],
    ),
    ProblemCategory(
        name="abduction_signs",
        description="Abductive inference, sign-reading, semiotics",
        signals=[
            "abduction",
            "abductive",
            "best explanation",
            "inference to the best",
            "sign",
            "semiotic",
            "peirce",
            "interpret",
            "pragmaticism",
        ],
        core_experts=["Peirce"],
        affinity_tags=["abduction", "semiotics"],
    ),
    ProblemCategory(
        name="language_game",
        description="Meaning-as-use, family resemblance, ordinary language, identity criteria",
        signals=[
            "language game",
            "family resemblance",
            "meaning is use",
            "ordinary language",
            "wittgenstein",
            "definitional",
            "grammar of",
            "what counts as",
            "philosophical confusion",
            "criteria of identity",
            "identity criteria",
            "what makes it the same",
            "ship of theseus",
        ],
        core_experts=["Wittgenstein"],
        affinity_tags=["language", "philosophy-of-language", "identity"],
    ),
    ProblemCategory(
        name="virtue_ethics",
        description="Character, integrity, telos, golden mean, eudaimonia",
        signals=[
            "virtue",
            "character",
            "integrity",
            "coherent character",
            "moral integrity",
            "telos",
            "eudaimon",
            "golden mean",
            "vice",
            "excellence",
            "habit",
            "ethical",
            "aristotle",
            "flourishing",
            "phronesis",
        ],
        core_experts=["Aristotle"],
        affinity_tags=["virtue-ethics", "character", "integrity"],
    ),
    ProblemCategory(
        name="earned_voice",
        description="Voice, expressive integrity, witness, testimony",
        signals=[
            "voice",
            "voice layer",
            "voice integrity",
            "expressive",
            "expressive integrity",
            "earned voice",
            "witness",
            "testimony",
            "lived experience",
            "dignity",
            "narrative",
            "storytell",
            "vernacular",
            "angelou",
            "voice as authority",
            "speaking voice",
            "writing voice",
            "tone of voice",
        ],
        core_experts=["Angelou"],
        affinity_tags=["voice", "witness", "expression"],
    ),
    ProblemCategory(
        name="register_framing",
        description="Conversational style, register, code-switching, audience-shift",
        signals=[
            "register",
            "framing",
            "conversation style",
            "code-switch",
            "indirect",
            "rapport",
            "report talk",
            "tannen",
            "cross-talk",
            "interruption",
            "high involvement",
            "voice across",
            "audience-aware",
            "tone shift",
            "register-shift",
            "addressee",
        ],
        core_experts=["Tannen"],
        affinity_tags=["register", "discourse", "voice"],
    ),
    ProblemCategory(
        name="society_of_mind",
        description="Modular cognition, agents, frames, K-lines",
        signals=[
            "society of mind",
            "agent-based",
            "modular cognition",
            "frame",
            "slot",
            "k-line",
            "minsky",
            "micro-agent",
            "perceptron",
        ],
        core_experts=["Minsky"],
        affinity_tags=["cognitive-architecture"],
    ),
    ProblemCategory(
        name="computability",
        description="Turing machines, halting, decidability",
        signals=[
            "turing",
            "halting",
            "computable",
            "decidable",
            "universal machine",
            "computation theory",
            "lambda calculus",
            "church-turing",
            "recursive function",
        ],
        core_experts=["Turing"],
        affinity_tags=["computability", "formal-methods"],
    ),
    ProblemCategory(
        name="deep_learning",
        description="Neural networks, gradients, transformers",
        signals=[
            "neural network",
            "deep learning",
            "backprop",
            "gradient descent",
            "transformer",
            "attention mechanism",
            "embedding",
            "hinton",
            "bengio",
            "loss function",
            "overfit",
            "generalization",
        ],
        core_experts=["Hinton", "Bengio"],
        affinity_tags=["machine-learning", "neural-networks"],
    ),
    ProblemCategory(
        name="rationality_alignment",
        description="AI alignment, Goodhart, instrumental convergence",
        signals=[
            "alignment",
            "goodhart",
            "instrumental",
            "mesa-optim",
            "optimization target",
            "yudkowsky",
            "x-risk",
            "value learning",
            "corrigible",
            "specification gaming",
        ],
        core_experts=["Yudkowsky"],
        affinity_tags=["ai-alignment", "rationality"],
    ),
    ProblemCategory(
        name="organic_distributed_order",
        description="Emergent order, mixed-use, distributed coordination",
        signals=[
            "organic",
            "mixed-use",
            "sidewalk",
            "neighborhood",
            "urban",
            "decentral",
            "emergent order",
            "jacobs",
            "eyes on the street",
            "self-organizing community",
        ],
        core_experts=["Jacobs"],
        affinity_tags=["distributed-order", "organic-systems"],
    ),
    ProblemCategory(
        name="analytical_imagination",
        description="Algorithmic art, programming as poetics",
        signals=[
            "analytical engine",
            "lovelace",
            "algorithmic art",
            "instruction sequence",
            "programming as poetics",
            "poetic computation",
            "ada",
        ],
        core_experts=["Lovelace"],
        affinity_tags=["computation-as-art"],
    ),
    ProblemCategory(
        name="intentional_stance",
        description="Self as pattern, intentional/design/physical stance, free will",
        signals=[
            "intentional stance",
            "design stance",
            "physical stance",
            "dennett",
            "free will",
            "fame in the brain",
            "multiple drafts",
            "compatibilism",
            "real patterns",
            "self as pattern",
            "persistence of self",
            "same person",
            "personal identity",
        ],
        core_experts=["Dennett"],
        affinity_tags=["philosophy-of-mind", "identity"],
    ),
    ProblemCategory(
        name="geometric_beauty",
        description="Geometry, topology, mathematical elegance as evidence",
        signals=[
            "geometry",
            "topology",
            "manifold",
            "twistor",
            "tiling",
            "beauty in math",
            "elegant",
            "symmetry",
            "geodesic",
            "curvature",
            "penrose",
            "spinor",
        ],
        core_experts=["Penrose"],
        affinity_tags=["geometry", "mathematical-beauty"],
    ),
    ProblemCategory(
        name="wonder_cosmos",
        description="Cosmic perspective, awe, scientific wonder",
        signals=[
            "wonder",
            "cosmos",
            "pale blue dot",
            "sagan",
            "awe",
            "popular science",
            "demon-haunted",
            "candle in the dark",
            "mote of dust",
        ],
        core_experts=["Sagan"],
        affinity_tags=["cosmic-perspective", "wonder"],
    ),
    ProblemCategory(
        name="identity_continuity",
        description="Continuity of identity across change, ship-of-Theseus, becoming",
        signals=[
            "continuity",
            "transformation",
            "becoming",
            "change over time",
            "across sessions",
            "across installations",
            "across instances",
            "persistence of identity",
            "rigidity",
            "drift",
            "rigidity and drift",
            "open to change",
            "evolving",
            "evolution of self",
            "ship of theseus",
            "selfhood across",
            "coherent across",
            "integrity across",
        ],
        core_experts=["Hofstadter", "Watts", "Dekker"],
        affinity_tags=["identity", "continuity", "transformation"],
    ),
    ProblemCategory(
        name="incomplete_fix",
        description="Patch that addresses part of the problem but not all",
        signals=[
            "partial",
            "incomplete",
            "still fails",
            "another case",
            "also broken",
            "missed",
            "forgot",
            "didn't handle",
            "some cases",
            "sometimes",
            "intermittent",
        ],
        core_experts=["Polya", "Popper"],
        affinity_tags=[
            "verification",
            "solution-check",
            "falsification",
            "completeness",
            "adversarial",
        ],
    ),
]


# ------------------------------------------------------------------
# Always-on experts (DEPRECATED 2026-05-03)
# ------------------------------------------------------------------
#
# Previously Kahneman + Popper got an automatic +3 baseline bonus on
# every problem. The benchmark surfaced that this was the dominant
# cause of the comfort-zone bias: those two appeared in 13 of the last
# ~20 consultations regardless of fit, while never-invoked experts
# (Dawkins, Dekker, Dillahunty, Einstein, Godel) sat untouched even on
# territory that explicitly called for them.
#
# Decision: experts earn their place every time. Meta-reasoners like
# Kahneman/Popper still surface naturally when the problem touches
# bias, falsification, or epistemics — they just no longer get a
# free ride. ALWAYS_ON kept as an empty list for import compatibility.
ALWAYS_ON: list[str] = []

# Target council size — soft cap is the default ceiling, hard cap
# is an absolute maximum that even high-scoring experts can't push
# past. The split lets a multi-dimensional problem pull a wider
# council without forcing every problem to hit the maximum.
MIN_EXPERTS = 5
SOFT_CAP = 12
HARD_CAP = 15
# Backcompat alias — older callers that pass max_experts still work.
MAX_EXPERTS = SOFT_CAP

# ------------------------------------------------------------------
# Lens families — clusters whose methodologies overlap
# ------------------------------------------------------------------
#
# Two from one family is healthy diversity within a school of thought;
# three or more is diminishing returns. The family cap is enforced in
# selection: after the second member of a family is picked, additional
# members are skipped unless their score materially exceeds the next
# out-of-family candidate.
LENS_FAMILIES: dict[str, list[str]] = {
    "physics": ["Einstein", "Hawking", "Penrose"],
    "skeptic": ["Sagan", "Dawkins", "Dillahunty", "Popper"],
    "systems": ["Beer", "Meadows", "Jacobs"],
    "distributed": ["Lamport", "Dijkstra"],
    "cognitive_bias": ["Kahneman", "Yudkowsky"],
    "investigation": ["Holmes", "Polya", "Feynman", "Peirce"],
    "formal": ["Godel", "Knuth", "Turing"],
    # Audit r9-21 #10: Godel removed (was double-counted as both formal
    # and meta_observer; family-cap math broke when one expert sat in
    # two families). Kept in formal — closer methodological fit.
    "meta_observer": ["Hofstadter", "Dennett", "Wittgenstein"],
    "design": ["Norman", "Deming"],
    "voice": ["Angelou", "Tannen"],
    # Audit r9-21 #10: 11 experts had no family entry, exempting them
    # from the family-cap and breaking exploration-vs-diversity math.
    "classical_method": ["Aristotle"],
    "deep_learning": ["Bengio", "Hinton"],
    "safety": ["Dekker", "Schneier"],
    "information": ["Shannon", "Lovelace"],
    "ai_foundations": ["Minsky", "Pearl"],
    "risk": ["Taleb"],
    "eastern_philosophy": ["Watts"],
}

# How many from one family before we start skipping.
FAMILY_CAP = 2

# Score advantage required to override family cap.
FAMILY_OVERRIDE_RATIO = 1.25

# Exploration tilt — buy information about under-invoked experts
# without actively suppressing proven performers. Asymmetric on
# purpose: trust is real and the boost ceiling is generous, but the
# penalty floor is shallow so high-trust experts still win when they
# fit. Centered on the median count so the average expert is at 1.0.
#
# This is NOT a bias correction — repeated selection of high-value
# experts is a trust/reputation signal working as designed. The gap
# was that new experts couldn't build their own track record because
# they never got airtime. The asymmetry buys exploration cheaply
# without suppressing proven performers.
EXPLORATION_BOOST_MAX = 0.30  # under-invoked get up to +30%
TRUST_TILT_FLOOR = 0.10  # over-invoked get at most -10%

# Window for invocation history (consultations).
EXPLORATION_TILT_WINDOW = 20

# Onboarding bonus for new experts — flat additive boost while their
# total invocation count is below this threshold. Lets the seven new
# 2026-05-03 lenses (Einstein, Hawking, Penrose, Sagan, Dawkins,
# Dillahunty, Lamport) actually show up in their first selections so
# they can build a track record. Independent of the median tilt.
ONBOARDING_INVOCATIONS = 10
ONBOARDING_BONUS = 1.5

# Backwards-compatible aliases — older imports / external scripts.
COMFORT_TILT_MAX = EXPLORATION_BOOST_MAX
COMFORT_TILT_WINDOW = EXPLORATION_TILT_WINDOW

# Push past SOFT_CAP toward HARD_CAP only if score >= this fraction
# of the top score. Keeps small problems from bloating to 12-15.
HARD_CAP_THRESHOLD_RATIO = 0.5


# ------------------------------------------------------------------
# Expert scoring
# ------------------------------------------------------------------


@dataclass
class ExpertScore:
    """Relevance score for one expert on one problem."""

    expert_name: str
    score: float
    reasons: list[str] = field(default_factory=list)

    def __repr__(self) -> str:
        return f"{self.expert_name}: {self.score:.2f} ({', '.join(self.reasons)})"


def classify_problem(problem: str) -> list[tuple[ProblemCategory, float]]:
    """Classify a problem into categories with confidence scores.

    Returns categories sorted by match strength (descending).
    A category's score = (number of signal matches) * category weight.
    """
    problem_lower = problem.lower()
    results: list[tuple[ProblemCategory, float]] = []

    for category in PROBLEM_CATEGORIES:
        match_count = 0
        for signal in category.signals:
            if signal in problem_lower:
                match_count += 1
        if match_count > 0:
            score = match_count * category.weight
            results.append((category, score))

    results.sort(key=lambda x: x[1], reverse=True)
    return results


def score_experts(
    problem: str,
    experts: dict[str, ExpertWisdom],
) -> list[ExpertScore]:
    """Score every registered expert's relevance to this problem.

    Scoring combines:
    1. Category match — is this expert a core expert for the detected categories?
    2. Tag affinity — do the expert's tags overlap with category affinity tags?
    3. When-to-apply match — do the expert's methodology triggers fire?
    4. Domain keyword match — do words in the problem appear in the expert's domain?
    5. Always-on bonus — meta-reasoning experts get a baseline score.
    """
    problem_lower = problem.lower()
    problem_words = set(re.findall(r"\b\w{4,}\b", problem_lower))

    categories = classify_problem(problem)
    scores: dict[str, ExpertScore] = {}

    # Initialize all experts with zero score
    for name in experts:
        scores[name] = ExpertScore(expert_name=name, score=0.0)

    # 1. Always-on bonus (deprecated — ALWAYS_ON is empty by default).
    # Retained as a hook so callers/tests can still pin specific
    # experts without going through force_experts.
    for name in ALWAYS_ON:
        if name in scores:
            scores[name].score += 3.0
            scores[name].reasons.append("always-on")

    # 2. Category core expert bonus (strongest signal)
    for category, cat_score in categories:
        for name in category.core_experts:
            if name in scores:
                bonus = 5.0 * (cat_score / max(cat_score, 1.0))
                scores[name].score += bonus
                scores[name].reasons.append(f"core:{category.name}")

    # 3. Tag affinity (moderate signal)
    category_tags: set[str] = set()
    for category, _ in categories:
        category_tags.update(category.affinity_tags)

    if category_tags:
        for name, wisdom in experts.items():
            overlap = category_tags & set(wisdom.tags)
            if overlap:
                scores[name].score += len(overlap) * 1.5
                scores[name].reasons.append(f"tags:{','.join(sorted(overlap))}")

    # 4. When-to-apply trigger match (moderate signal)
    for name, wisdom in experts.items():
        for method in wisdom.core_methodologies:
            for trigger in method.when_to_apply:
                trigger_words = set(re.findall(r"\b\w{4,}\b", trigger.lower()))
                overlap = problem_words & trigger_words
                if len(overlap) >= 2:
                    scores[name].score += 2.0
                    scores[name].reasons.append(f"trigger:{method.name}")
                    break  # one match per methodology is enough

    # 5. Domain keyword match (weak signal)
    for name, wisdom in experts.items():
        domain_words = set(re.findall(r"\b\w{4,}\b", wisdom.domain.lower()))
        overlap = problem_words & domain_words
        if overlap:
            scores[name].score += len(overlap) * 0.5
            scores[name].reasons.append("domain")

    # 6. Exploration tilt + onboarding — buy information about
    # under-invoked experts (asymmetric: generous boost, shallow
    # penalty) and give brand-new experts a flat additive bonus
    # until they've had enough invocations to build a track record.
    try:
        from divineos.core.council.consultation_log import invocation_tally

        tally = invocation_tally(last_n=EXPLORATION_TILT_WINDOW)
    except (sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError, ImportError):
        # Defensive: missing DB or import shouldn't break selection.
        tally = {}

    if tally:
        counts = sorted(tally.get(n, 0) for n in experts)
        median = counts[len(counts) // 2] if counts else 0
        max_count = max(counts) if counts else 0
        if max_count > 0:
            for name, es in scores.items():
                own = tally.get(name, 0)
                # Asymmetric tilt: boost up to +EXPLORATION_BOOST_MAX,
                # penalty down to -TRUST_TILT_FLOOR. Trust is preserved.
                spread = max(median, max_count - median, 1)
                raw = (median - own) / spread  # >0 means under-invoked
                if raw > 0:
                    tilt = 1.0 + min(EXPLORATION_BOOST_MAX, EXPLORATION_BOOST_MAX * raw)
                    label = "exploration-boost"
                else:
                    tilt = 1.0 + max(-TRUST_TILT_FLOOR, TRUST_TILT_FLOOR * raw)
                    label = "trust-tilt"
                if abs(tilt - 1.0) > 0.01 and es.score > 0:
                    es.score *= tilt
                    es.reasons.append(f"{label}:{tilt:.2f}")

    # 7. Onboarding bonus — flat additive boost for experts who
    # haven't had enough invocations to build a track record yet.
    # Independent of the median tilt; applies even with no history.
    for name, es in scores.items():
        own = tally.get(name, 0) if tally else 0
        if own < ONBOARDING_INVOCATIONS and es.score > 0:
            es.score += ONBOARDING_BONUS
            es.reasons.append(f"onboarding:+{ONBOARDING_BONUS:.1f}")

    result = list(scores.values())
    result.sort(key=lambda x: x.score, reverse=True)
    return result


def _family_of(expert_name: str) -> str | None:
    """Return the family label this expert belongs to, or None."""
    for family, members in LENS_FAMILIES.items():
        if expert_name in members:
            return family
    return None


def select_experts(
    problem: str,
    experts: dict[str, ExpertWisdom],
    min_experts: int = MIN_EXPERTS,
    max_experts: int = SOFT_CAP,
    hard_cap: int = HARD_CAP,
) -> list[ExpertScore]:
    """Select the optimal council for this problem.

    Two-phase fill with family-overlap discipline:
      1. Always-on (if any) included up to max_experts.
      2. Top-scored experts fill toward max_experts (soft cap), respecting
         the per-family cap of FAMILY_CAP unless the candidate's score
         exceeds the next out-of-family candidate by FAMILY_OVERRIDE_RATIO.
      3. If room remains and remaining candidates score >= the top score
         times HARD_CAP_THRESHOLD_RATIO, push toward hard_cap.
      4. If we're below min_experts, fill with top-scored remaining
         experts regardless of score (small councils still need a quorum).
    """
    scored = score_experts(problem, experts)

    selected: list[ExpertScore] = []
    selected_names: set[str] = set()
    family_counts: dict[str, int] = {}

    def _add(es: ExpertScore, reason: str | None = None) -> None:
        selected.append(es)
        selected_names.add(es.expert_name)
        fam = _family_of(es.expert_name)
        if fam:
            family_counts[fam] = family_counts.get(fam, 0) + 1
        if reason:
            es.reasons.append(reason)

    # Phase 1: always-on
    for es in scored:
        if len(selected) >= max_experts:
            break
        if es.expert_name in ALWAYS_ON and es.expert_name in experts:
            _add(es)

    # Phase 2: fill toward soft cap with family discipline.
    top_score = scored[0].score if scored else 0.0
    deferred: list[ExpertScore] = []  # over-family candidates we may revisit

    for es in scored:
        if len(selected) >= max_experts:
            break
        if es.expert_name in selected_names or es.score <= 0:
            continue
        fam = _family_of(es.expert_name)
        if fam and family_counts.get(fam, 0) >= FAMILY_CAP:
            deferred.append(es)
            continue
        _add(es)

    # Phase 2b: revisit deferred if their score beats the next best
    # out-of-family candidate by the override ratio.
    if deferred and len(selected) < max_experts:
        # Score of weakest selected, used as the bar to beat for override.
        bar = min((s.score for s in selected if s.score > 0), default=0.0)
        for es in deferred:
            if len(selected) >= max_experts:
                break
            if bar > 0 and es.score >= bar * FAMILY_OVERRIDE_RATIO:
                _add(es, reason="family-override")

    # Phase 3: push toward hard cap only for genuinely strong candidates.
    if top_score > 0 and len(selected) < hard_cap:
        threshold = top_score * HARD_CAP_THRESHOLD_RATIO
        for es in scored:
            if len(selected) >= hard_cap:
                break
            if es.expert_name in selected_names:
                continue
            if es.score < threshold:
                break  # scored is sorted desc; no remaining will qualify
            fam = _family_of(es.expert_name)
            if fam and family_counts.get(fam, 0) >= FAMILY_CAP:
                continue
            _add(es, reason="hard-cap-fill")

    # Phase 4: ensure minimum council size.
    for es in scored:
        if len(selected) >= min_experts:
            break
        if es.expert_name not in selected_names:
            _add(es, reason="min-fill")

    return selected


# ------------------------------------------------------------------
# Managed convene — the main API
# ------------------------------------------------------------------


@dataclass
class ManagedCouncilResult:
    """Result of a managed council session.

    Extends CouncilResult with selection metadata.
    """

    council_result: CouncilResult
    selected_experts: list[ExpertScore]
    categories_detected: list[tuple[str, float]]
    total_experts_available: int

    @property
    def problem(self) -> str:
        return self.council_result.problem

    @property
    def analyses(self):
        return self.council_result.analyses

    @property
    def synthesis(self) -> str:
        return self.council_result.synthesis

    def selection_summary(self) -> str:
        """Human-readable summary of why these experts were chosen."""
        parts: list[str] = []
        parts.append(
            f"Selected {len(self.selected_experts)} of {self.total_experts_available} experts"
        )

        if self.categories_detected:
            cats = ", ".join(
                f"{name} ({score:.1f})" for name, score in self.categories_detected[:3]
            )
            parts.append(f"Problem categories: {cats}")

        parts.append("Selected council:")
        for es in self.selected_experts:
            reasons = ", ".join(es.reasons) if es.reasons else "baseline"
            parts.append(f"  {es.expert_name} ({es.score:.1f}): {reasons}")

        return "\n".join(parts)


class CouncilManager:
    """Manages dynamic expert selection for the council engine.

    Wraps CouncilEngine with intelligent expert routing.
    The manager classifies the problem, scores experts, selects
    the optimal 5-8, then delegates to the engine for analysis.

    Usage:
        manager = CouncilManager(engine)
        result = manager.convene("the database query returns wrong results")
        print(result.selection_summary())
        print(result.synthesis)
    """

    def __init__(self, engine: CouncilEngine) -> None:
        self._engine = engine

    @property
    def engine(self) -> CouncilEngine:
        return self._engine

    def convene(
        self,
        problem: str,
        min_experts: int = MIN_EXPERTS,
        max_experts: int = SOFT_CAP,
        hard_cap: int = HARD_CAP,
        force_experts: list[str] | None = None,
    ) -> ManagedCouncilResult:
        """Convene the right experts for this problem.

        Args:
            problem: The problem to analyze.
            min_experts: Minimum experts to include (default 5).
            max_experts: Maximum experts to include (default 8).
            force_experts: Always include these experts (by name),
                          in addition to the auto-selected ones.
        """
        experts = self._engine.experts

        # Score and select
        selected = select_experts(problem, experts, min_experts, max_experts, hard_cap)
        selected_names = [es.expert_name for es in selected]

        # Add forced experts if not already selected (respecting hard cap)
        if force_experts:
            for name in force_experts:
                if len(selected) >= hard_cap:
                    break
                if name not in selected_names and name in experts:
                    selected.append(
                        ExpertScore(
                            expert_name=name,
                            score=0.0,
                            reasons=["forced"],
                        )
                    )
                    selected_names.append(name)

        # Classify for metadata
        categories = classify_problem(problem)
        categories_meta = [(cat.name, score) for cat, score in categories]

        # Convene with selected experts only
        council_result = self._engine.convene(
            problem=problem,
            expert_names=selected_names,
        )

        return ManagedCouncilResult(
            council_result=council_result,
            selected_experts=selected,
            categories_detected=categories_meta,
            total_experts_available=len(experts),
        )

    def explain_selection(self, problem: str) -> str:
        """Explain which experts would be selected and why.

        Useful for debugging and understanding the selection logic.
        Does not run analysis — just shows the routing decision.
        """
        experts = self._engine.experts
        categories = classify_problem(problem)
        scored = score_experts(problem, experts)
        selected = select_experts(problem, experts)
        selected_names = {s.expert_name for s in selected}

        parts: list[str] = []
        parts.append(f"Problem: {problem[:100]}...")
        parts.append("")

        if categories:
            parts.append("Detected categories:")
            for cat, score in categories:
                parts.append(f"  {cat.name} ({score:.1f}): {cat.description}")
                parts.append(f"    Core experts: {', '.join(cat.core_experts)}")
        else:
            parts.append("No specific category detected — using general scoring")

        parts.append("")
        parts.append("All expert scores:")
        for es in scored[:15]:  # top 15
            marker = " *" if es.expert_name in selected_names else ""
            reasons = ", ".join(es.reasons) if es.reasons else "—"
            parts.append(f"  {es.score:5.1f}  {es.expert_name:<15}{marker}  ({reasons})")

        parts.append("")
        parts.append(f"Selected ({len(selected)}):")
        for es in selected:
            parts.append(f"  {es.expert_name}: {', '.join(es.reasons)}")

        return "\n".join(parts)
