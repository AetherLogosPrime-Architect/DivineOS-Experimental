"""
Tree of Life — Cognitive Flow System

Maps the 10 sephirot (+Da'at) to stages of AI cognitive flow.
From intent (Keter) to output (Malkuth). The code defines the
structure. The AI walks the path and thinks.

This is data, not logic. The sephirot are frozen dataclasses.
The flow generator is string formatting. No code here reasons.
"""

from dataclasses import dataclass
from enum import Enum


class Pillar(Enum):
    """The three pillars of the Tree of Life."""

    RIGHT = "Force"  # Expansion: Chokmah, Chesed, Netzach
    LEFT = "Form"  # Constraint: Binah, Gevurah, Hod
    MIDDLE = "Balance"  # Integration: Keter, Da'at, Tiphareth, Yesod, Malkuth


@dataclass(frozen=True)
class Sephirah:
    """A node on the Tree of Life representing a cognitive stage."""

    name: str
    hebrew_name: str
    english_name: str
    pillar: Pillar
    position: int
    description: str
    cognitive_function: str
    prompt_guidance: str


@dataclass(frozen=True)
class Path:
    """A connection between two sephirot on the Tree."""

    from_sephirah: str
    to_sephirah: str
    description: str


# ---------------------------------------------------------------------------
# The 11 Sephirot
# ---------------------------------------------------------------------------

_KETER = Sephirah(
    name="keter",
    hebrew_name="Keter",
    english_name="Crown",
    pillar=Pillar.MIDDLE,
    position=1,
    description="Pure intent. The initial spark before thought takes form.",
    cognitive_function=(
        "Clarify the question or goal. Strip away assumptions about what"
        " the answer should look like. What are we actually trying to"
        " understand or achieve?"
    ),
    prompt_guidance=(
        "State the core question or goal in one sentence. What is the"
        " purest form of what you are trying to accomplish? Do not assume"
        " a solution yet."
    ),
)

_CHOKMAH = Sephirah(
    name="chokmah",
    hebrew_name="Chokmah",
    english_name="Wisdom",
    pillar=Pillar.RIGHT,
    position=2,
    description="First flash of insight. Raw, unstructured intuition.",
    cognitive_function=(
        "Capture the first flash of insight. What comes to mind"
        " immediately, before analysis? This is expansion — do not"
        " filter yet."
    ),
    prompt_guidance=(
        "What is your immediate intuition? List every initial thought,"
        " even half-formed ones. Do not judge them yet."
    ),
)

_BINAH = Sephirah(
    name="binah",
    hebrew_name="Binah",
    english_name="Understanding",
    pillar=Pillar.LEFT,
    position=3,
    description="Structure the insight. Apply form to the raw flash.",
    cognitive_function=(
        "Give structure to the raw insight. What framework, model, or"
        " category applies? Organize the chaos of Chokmah into something"
        " structured."
    ),
    prompt_guidance=(
        "What framework or structure applies? Categorize the insights."
        " What patterns do you recognize? What mental model fits?"
    ),
)

_DAAT = Sephirah(
    name="daat",
    hebrew_name="Da'at",
    english_name="Knowledge",
    pillar=Pillar.MIDDLE,
    position=4,
    description=("Bridge between abstract understanding and concrete application."),
    cognitive_function=(
        "Connect abstract understanding to concrete application. What do"
        " you actually know vs. assume? Where does theory meet practice?"
    ),
    prompt_guidance=(
        "What do you actually know vs. what are you assuming? How does"
        " the framework connect to the concrete situation? What is the"
        " bridge between theory and practice?"
    ),
)

_CHESED = Sephirah(
    name="chesed",
    hebrew_name="Chesed",
    english_name="Mercy",
    pillar=Pillar.RIGHT,
    position=5,
    description="Expansion. Explore broadly without constraint.",
    cognitive_function=(
        "Explore all possibilities without filtering. What options exist?"
        " Be generous and expansive. This is the brainstorm phase."
    ),
    prompt_guidance=(
        "What are ALL the possibilities? List every option, approach, or"
        " solution. Do not eliminate anything yet. What would you try if"
        " there were no constraints?"
    ),
)

_GEVURAH = Sephirah(
    name="gevurah",
    hebrew_name="Gevurah",
    english_name="Severity",
    pillar=Pillar.LEFT,
    position=6,
    description="Discipline. Eliminate what does not belong.",
    cognitive_function=(
        "Constrain and eliminate. Which possibilities are actually viable?"
        " What should be cut? Apply rigor — what fails under scrutiny?"
    ),
    prompt_guidance=(
        "Which possibilities survive scrutiny? What should be eliminated"
        " and why? What are the dealbreakers? Apply constraints: time,"
        " resources, feasibility, correctness."
    ),
)

_TIPHARETH = Sephirah(
    name="tiphareth",
    hebrew_name="Tiphareth",
    english_name="Beauty",
    pillar=Pillar.MIDDLE,
    position=7,
    description=("Harmony. The balanced synthesis of expansion and constraint."),
    cognitive_function=(
        "Synthesize. What balanced answer emerges from the tension between"
        " Chesed (expansion) and Gevurah (constraint)? Find the elegant"
        " solution that honors both."
    ),
    prompt_guidance=(
        "What is the synthesis? How do the surviving possibilities combine"
        " into a coherent answer? What is the elegant solution that"
        " balances breadth with rigor?"
    ),
)

_NETZACH = Sephirah(
    name="netzach",
    hebrew_name="Netzach",
    english_name="Victory",
    pillar=Pillar.RIGHT,
    position=8,
    description="Drive and emotional resonance. What makes this compelling.",
    cognitive_function=(
        "Test for emotional resonance and drive. Is this answer compelling?"
        " Does it motivate action? Will it persuade?"
    ),
    prompt_guidance=(
        "Is this answer compelling? Does it resonate? Would someone care"
        " about this result? If it feels lifeless, what would make it alive?"
    ),
)

_HOD = Sephirah(
    name="hod",
    hebrew_name="Hod",
    english_name="Splendor",
    pillar=Pillar.LEFT,
    position=9,
    description="Logic and rigor. What makes this correct.",
    cognitive_function=(
        "Test for logical rigor. Is this answer correct? Check for logical"
        " fallacies, missing evidence, unsupported claims."
    ),
    prompt_guidance=(
        "Is this answer logically sound? Check every claim for evidence."
        " Are there logical fallacies? Missing steps? What would a"
        " rigorous critic say?"
    ),
)

_YESOD = Sephirah(
    name="yesod",
    hebrew_name="Yesod",
    english_name="Foundation",
    pillar=Pillar.MIDDLE,
    position=10,
    description="Consolidation. The actionable blueprint before manifestation.",
    cognitive_function=(
        "Consolidate into an actionable plan. Combine the compelling"
        " (Netzach) with the rigorous (Hod) into something actionable."
    ),
    prompt_guidance=(
        "What is the concrete plan? List specific, actionable steps."
        " What comes first? What depends on what? Convert the synthesis"
        " into a blueprint."
    ),
)

_MALKUTH = Sephirah(
    name="malkuth",
    hebrew_name="Malkuth",
    english_name="Kingdom",
    pillar=Pillar.MIDDLE,
    position=11,
    description="Manifestation. The concrete output in the real world.",
    cognitive_function=(
        "Manifest the final output. State the answer, deliver the result,"
        " produce the artifact. Thought becomes reality."
    ),
    prompt_guidance=(
        "State the final answer or output. Be concrete and specific."
        " This is the deliverable. What exactly is the result of this"
        " entire reasoning process?"
    ),
)

# ---------------------------------------------------------------------------
# Registry and Flow Constants
# ---------------------------------------------------------------------------

SEPHIROT: dict[str, Sephirah] = {
    "keter": _KETER,
    "chokmah": _CHOKMAH,
    "binah": _BINAH,
    "daat": _DAAT,
    "chesed": _CHESED,
    "gevurah": _GEVURAH,
    "tiphareth": _TIPHARETH,
    "netzach": _NETZACH,
    "hod": _HOD,
    "yesod": _YESOD,
    "malkuth": _MALKUTH,
}

LIGHTNING_FLASH: tuple[str, ...] = (
    "keter",
    "chokmah",
    "binah",
    "daat",
    "chesed",
    "gevurah",
    "tiphareth",
    "netzach",
    "hod",
    "yesod",
    "malkuth",
)

MIDDLE_PILLAR: tuple[str, ...] = (
    "keter",
    "daat",
    "tiphareth",
    "yesod",
    "malkuth",
)

PATHS: tuple[Path, ...] = (
    Path("keter", "chokmah", "Intent ignites intuition"),
    Path("keter", "binah", "Intent seeks structure"),
    Path("chokmah", "binah", "Raw insight receives form"),
    Path("chokmah", "chesed", "Intuition expands into possibilities"),
    Path("binah", "gevurah", "Structure becomes judgment"),
    Path("daat", "chesed", "Knowledge opens exploration"),
    Path("daat", "gevurah", "Knowledge informs constraint"),
    Path("chesed", "tiphareth", "Possibilities seek balance"),
    Path("gevurah", "tiphareth", "Constraints shape synthesis"),
    Path("tiphareth", "netzach", "Synthesis seeks resonance"),
    Path("tiphareth", "hod", "Synthesis seeks rigor"),
    Path("netzach", "yesod", "Drive grounds into plan"),
    Path("hod", "yesod", "Logic grounds into plan"),
    Path("yesod", "malkuth", "Blueprint becomes output"),
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_sephirah(name: str) -> Sephirah:
    """Get a sephirah by name. Case-insensitive. Raises KeyError if not found."""
    key = name.lower()
    if key not in SEPHIROT:
        available = ", ".join(sorted(SEPHIROT.keys()))
        raise KeyError(f"Unknown sephirah: {name!r}. Available: {available}")
    return SEPHIROT[key]


def list_sephirot() -> list[Sephirah]:
    """Return all sephirot sorted by position in the Lightning Flash."""
    return sorted(SEPHIROT.values(), key=lambda s: s.position)


def get_pillar(pillar: Pillar) -> list[Sephirah]:
    """Return all sephirot on a given pillar, sorted by position."""
    return sorted(
        [s for s in SEPHIROT.values() if s.pillar == pillar],
        key=lambda s: s.position,
    )


def get_paths_from(name: str) -> list[Path]:
    """Return all paths originating from a given sephirah."""
    key = name.lower()
    if key not in SEPHIROT:
        available = ", ".join(sorted(SEPHIROT.keys()))
        raise KeyError(f"Unknown sephirah: {name!r}. Available: {available}")
    return [p for p in PATHS if p.from_sephirah == key]


def generate_flow_prompt(question: str, depth: str = "full") -> str:
    """Generate a structured reasoning flow prompt.

    Args:
        question: The question or goal to reason about.
        depth: "full" for all 11 stages, "quick" for Middle Pillar (5 stages).

    Returns:
        Markdown-formatted reasoning flow.

    Raises:
        ValueError: If depth is not "full" or "quick".
    """
    if depth == "full":
        flow = LIGHTNING_FLASH
        mode_label = "Full Lightning Flash (11 stages)"
    elif depth == "quick":
        flow = MIDDLE_PILLAR
        mode_label = "Quick Middle Pillar (5 stages)"
    else:
        raise ValueError(f"Invalid depth: {depth!r}. Must be 'full' or 'quick'.")

    lines: list[str] = [
        "## Tree of Life: Cognitive Flow\n",
        f"**Question:** {question}",
        f"**Mode:** {mode_label}\n",
        "---\n",
    ]

    for i, name in enumerate(flow, 1):
        seph = SEPHIROT[name]
        lines.append(f"### {i}. {seph.hebrew_name} ({seph.english_name}) — {seph.description}\n")
        lines.append(f"{seph.prompt_guidance}\n")

    lines.append("---\n")
    lines.append("*Walk each stage. Let each sephirah complete before moving to the next.*")

    return "\n".join(lines)


def render_tree() -> str:
    """Render an ASCII representation of the Tree of Life."""
    return """\
                 Keter
                (Crown)
               /   |   \\
        Binah      |      Chokmah
   (Understanding) |     (Wisdom)
               \\   |   /
                 Da'at
              (Knowledge)
               /   |   \\
      Gevurah      |      Chesed
     (Severity)    |     (Mercy)
               \\   |   /
               Tiphareth
               (Beauty)
               /   |   \\
         Hod       |      Netzach
    (Splendor)     |    (Victory)
               \\   |   /
                 Yesod
             (Foundation)
                   |
                Malkuth
               (Kingdom)"""
