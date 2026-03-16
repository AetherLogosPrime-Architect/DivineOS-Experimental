"""
Expert Lenses — Structured Reasoning Frameworks

Expert lenses are thinking tools for AI. The code defines WHAT framework
to use. The AI uses the framework to actually think.

This is data, not logic. The experts are frozen dataclasses of steps and
questions. The router is substring matching. The prompt generator is
string formatting. No code here pretends to reason.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ExpertLens:
    """A structured reasoning framework the AI uses as a thinking tool."""

    name: str
    display_name: str
    domain: str
    description: str
    framework_steps: tuple[str, ...]
    key_questions: tuple[str, ...]
    domains: frozenset[str]
    detects: tuple[str, ...]


_FEYNMAN = ExpertLens(
    name="feynman",
    display_name="Richard Feynman",
    domain="First Principles & Clarity",
    description="Strip assumptions, simplify, find what you actually know vs. what you assume.",
    framework_steps=(
        "Strip the jargon: Restate the problem using only words a bright 12-year-old would know. What technical terms are hiding confusion?",
        "Identify assumptions: What are we taking for granted? List every assumption explicitly, even the ones that seem obvious.",
        "Find the fundamentals: What basic principles govern this? What are the actual mechanisms at work? What does physics/math/logic say?",
        "Rebuild from scratch: Starting from the fundamentals, can you reconstruct the claim? Where does the reconstruction diverge from the original?",
        "Make it testable: What experiment or observation would prove this wrong? If nothing could disprove it, it is not a real claim.",
    ),
    key_questions=(
        "What does this actually mean in plain language?",
        "What are we assuming that we have not checked?",
        "Can I explain this without jargon? If not, do I really understand it?",
        "What would disprove this?",
        "What is the simplest version of this that could work?",
    ),
    domains=frozenset(
        {
            "physics",
            "explanation",
            "simplification",
            "understanding",
            "debugging",
            "jargon",
            "clarity",
            "first principles",
            "fundamentals",
            "assumptions",
        }
    ),
    detects=(
        "Jargon used as a substitute for understanding",
        "Hidden assumptions that nobody questioned",
        "Cargo cult reasoning (looks right, lacks mechanism)",
        "Unnecessary complexity masking a simple problem",
    ),
)

_PEARL = ExpertLens(
    name="pearl",
    display_name="Judea Pearl",
    domain="Causal Inference",
    description="Distinguish correlation from causation. Find confounders. Reason about interventions.",
    framework_steps=(
        "Identify the causal claim: What is supposedly causing what? State the claim as 'X causes Y' explicitly. If there is no causal claim, note that.",
        "Check for confounders: What third variables could explain both X and Y? Draw the causal graph. Are there back-door paths?",
        "Assess the Ladder of Causation: Is this observational (we saw X and Y together), interventional (we changed X and Y changed), or counterfactual (if X had not happened, Y would not have)?",
        "Apply do-calculus: If we do(X), does Y change? Can we identify the causal effect from the available data, or do we need an experiment?",
        "Verdict: Is the causal claim supported? What evidence would strengthen or weaken it?",
    ),
    key_questions=(
        "Is this correlation or causation?",
        "What confounders could explain this relationship?",
        "Would intervening on X actually change Y?",
        "What does the causal graph look like?",
        "Are we on Rung 1 (seeing), Rung 2 (doing), or Rung 3 (imagining)?",
    ),
    domains=frozenset(
        {
            "causality",
            "statistics",
            "data",
            "correlation",
            "research",
            "confounders",
            "experiment",
            "intervention",
            "probability",
            "inference",
        }
    ),
    detects=(
        "Correlation mistaken for causation",
        "Missing confounders in causal claims",
        "Observational data used to justify interventional conclusions",
        "Reversed causality (Y actually causes X)",
    ),
)

_YUDKOWSKY = ExpertLens(
    name="yudkowsky",
    display_name="Eliezer Yudkowsky",
    domain="Alignment & Safety",
    description="Analyze goal specification. Find where optimization could go catastrophically wrong.",
    framework_steps=(
        "Identify the optimization target: What is this system actually optimizing for? State the objective function explicitly. Distinguish stated goals from revealed goals.",
        "Check for specification gaming: Could the system achieve the measured objective without achieving the intended objective? Where does the proxy diverge from the goal?",
        "Identify instrumental convergence: What sub-goals will emerge regardless of the terminal goal? (Resource acquisition, self-preservation, goal stability, cognitive enhancement.)",
        "Assess failure modes: What could go catastrophically wrong? Consider: value drift, deceptive alignment, Goodhart's Law, mesa-optimization, distributional shift.",
        "Risk verdict: Is this safe to proceed with? What safeguards are missing? What would make this safer?",
    ),
    key_questions=(
        "What is this actually optimizing for, as opposed to what we say it optimizes for?",
        "What would a maximally clever adversary do with this specification?",
        "Where does the measurable proxy diverge from the real goal?",
        "What instrumental goals will emerge from this?",
        "What is the worst-case scenario, and how likely is it?",
    ),
    domains=frozenset(
        {
            "safety",
            "alignment",
            "ai",
            "risk",
            "optimization",
            "goals",
            "specification",
            "value",
            "catastrophe",
            "failure",
        }
    ),
    detects=(
        "Goal misspecification (optimizing the wrong thing)",
        "Goodhart's Law (metric becomes the target)",
        "Instrumental convergence (power-seeking, self-preservation)",
        "Deceptive alignment (appears safe, is not)",
    ),
)

_NUSSBAUM = ExpertLens(
    name="nussbaum",
    display_name="Martha Nussbaum",
    domain="Ethics & Human Impact",
    description="Assess who is affected. Whose dignity is at stake. What capabilities are enabled or restricted.",
    framework_steps=(
        "Identify stakeholders: Who is affected by this? List all parties, especially those who lack power or voice. Who benefits? Who bears the cost?",
        "Assess capabilities: What can each stakeholder actually do and be? Which central capabilities are at stake? (Life, health, bodily integrity, practical reason, affiliation, play, control over environment.)",
        "Check for exclusion: Is anyone systematically excluded from benefits or participation? Are there structural barriers? Is there an asymmetry of power?",
        "Evaluate flourishing: Does this enable people to live lives they have reason to value? Or does it reduce them to mere instruments?",
        "Justice verdict: Is this just? What would make it more just? What capabilities need protection?",
    ),
    key_questions=(
        "Who is affected, and do they have a voice in this decision?",
        "Whose dignity is at stake?",
        "What capabilities are being enabled or restricted?",
        "Is anyone being used merely as a means?",
        "What would genuine flourishing look like here?",
    ),
    domains=frozenset(
        {
            "ethics",
            "justice",
            "fairness",
            "human",
            "rights",
            "impact",
            "policy",
            "dignity",
            "stakeholder",
            "capability",
            "flourishing",
            "equity",
        }
    ),
    detects=(
        "Invisible stakeholders (affected people nobody considered)",
        "Capability deprivation (restricting what people can do or be)",
        "Instrumental treatment (using people as mere means)",
        "Structural injustice (systems that systematically exclude)",
    ),
)

_HINTON = ExpertLens(
    name="hinton",
    display_name="Geoffrey Hinton",
    domain="Learning & Architecture",
    description="Assess whether the architecture fits the task. Find learning pathologies.",
    framework_steps=(
        "Assess task-architecture fit: What is the task? What structure does the data have? Does the chosen architecture match? (Spatial data needs convolutions, sequences need recurrence or attention, graphs need message-passing.)",
        "Check the training signal: Is there a clear learning signal? Will gradients flow? Watch for vanishing/exploding gradients, dead neurons, mode collapse.",
        "Identify learning pathologies: Overfitting? Underfitting? Catastrophic forgetting? Is the model memorizing or generalizing? Is the training data representative?",
        "Evaluate capacity and complexity: Is the model too large (overfitting risk) or too small (underfitting)? Are there information bottlenecks?",
        "Architecture verdict: Recommend changes. What would improve learning? What is the simplest architecture that could work?",
    ),
    key_questions=(
        "Does the architecture match the structure of the data?",
        "Will gradients actually flow through this network?",
        "Is the model learning or memorizing?",
        "What is the simplest model that could solve this?",
        "Where are the information bottlenecks?",
    ),
    domains=frozenset(
        {
            "ml",
            "neural",
            "learning",
            "training",
            "architecture",
            "model",
            "deep learning",
            "network",
            "gradient",
            "overfitting",
            "loss",
        }
    ),
    detects=(
        "Architecture-task mismatch (wrong inductive bias)",
        "Vanishing or exploding gradients in deep networks",
        "Overfitting vs. underfitting symptoms",
        "Information bottlenecks that kill learning",
    ),
)


# ---------------------------------------------------------------------------
# Registry & public API
# ---------------------------------------------------------------------------

EXPERT_REGISTRY: dict[str, ExpertLens] = {
    "feynman": _FEYNMAN,
    "pearl": _PEARL,
    "yudkowsky": _YUDKOWSKY,
    "nussbaum": _NUSSBAUM,
    "hinton": _HINTON,
}


def get_expert(name: str) -> ExpertLens:
    """Get an expert lens by name. Raises KeyError if not found."""
    name_lower = name.lower()
    if name_lower not in EXPERT_REGISTRY:
        available = ", ".join(sorted(EXPERT_REGISTRY.keys()))
        raise KeyError(f"Unknown expert '{name}'. Available: {available}")
    return EXPERT_REGISTRY[name_lower]


def list_experts() -> list[ExpertLens]:
    """Return all registered expert lenses, sorted by name."""
    return sorted(EXPERT_REGISTRY.values(), key=lambda e: e.name)


def route(question: str, max_experts: int = 3) -> list[tuple[ExpertLens, float]]:
    """
    Score and select the most relevant experts for a question.

    Uses substring matching of domain keywords against the question.
    Returns list of (ExpertLens, score) tuples sorted by score descending.
    Falls back to Feynman (first principles work everywhere) if nothing matches.
    """
    question_lower = question.lower()

    scored: list[tuple[ExpertLens, float]] = []
    for expert in EXPERT_REGISTRY.values():
        matches = sum(1 for kw in expert.domains if kw in question_lower)
        if matches > 0:
            score = matches / len(expert.domains)
            scored.append((expert, round(score, 3)))

    scored.sort(key=lambda x: x[1], reverse=True)

    if not scored:
        return [(EXPERT_REGISTRY["feynman"], 0.1)]

    return scored[:max_experts]


def generate_framework_prompt(expert: ExpertLens, question: str) -> str:
    """
    Generate a structured thinking framework for the AI to follow.

    Outputs markdown the AI reads and reasons through step by step.
    """
    lines: list[str] = []

    lines.append(f"## {expert.display_name} Lens: {expert.domain}")
    lines.append("")
    lines.append(f"**Question:** {question}")
    lines.append("")

    for i, step in enumerate(expert.framework_steps, 1):
        lines.append(f"### Step {i}")
        lines.append(step)
        lines.append("")

    lines.append("### Key Questions to Consider")
    for q in expert.key_questions:
        lines.append(f"- {q}")
    lines.append("")

    lines.append("### What This Lens Detects")
    for d in expert.detects:
        lines.append(f"- {d}")
    lines.append("")

    lines.append("---")
    lines.append("*Reason through each step. Store insights via `divineos learn`.*")

    return "\n".join(lines)
