"""Memory-kind classifier — diagnostic metadata on knowledge (not yet consumed).

STATUS AS OF 2026-04-24 (fresh-Claude audit round 3, Finding: "pure metadata today"):

The classifier assigns EPISODIC/SEMANTIC/PROCEDURAL/UNCLASSIFIED on write
and exposes the result as a CLI filter on read. **Nothing else in the
codebase consumes the classification.** No code path uses memory_kind
to change retrieval ranking, briefing surface, extraction decisions,
supersession logic, or maturity lifecycle. The column earned its
migration cost and then paid no downstream return.

Earlier docstring called this an "orthogonal diagnostic dimension." That
framing overclaims. The honest description is: **diagnostic metadata for
human slicing via `divineos knowledge --kind SEMANTIC` filtering, and
nothing else.** Until a real consumer wires in, it is not load-bearing.

Candidate future consumers (pre-reg any before wiring, per the standing
"clever local defense" claim):

- Briefing prioritization: EPISODIC entries fade faster than SEMANTIC
  (episodic memories are time-bound; rules don't age the same way).
- Extraction discipline: PROCEDURAL entries should pass a step-sequence
  validator before CONFIRMED.
- Contradiction resolution: a new SEMANTIC claim that contradicts an
  older EPISODIC instance probably doesn't invalidate the instance; the
  instance might be a counterexample the rule needs to account for.

If none of those pan out, rename the column `kind_label` and formalize
the diagnostic-only framing. Until then, treat any code-change that
branches on memory_kind as new-mechanism work requiring a pre-reg.

Three kinds plus UNCLASSIFIED (Beer, variety deficit):

- EPISODIC   — event/instance. "I did X on Y day and Z happened."
               Time-bound, specific instance, narrative shape.
- SEMANTIC   — fact/rule/principle. "X is true / never do X / X causes Y."
               Timeless claim-shape, no specific instance attached.
- PROCEDURAL — how-to/workflow. "To do X: step 1, step 2, step 3."
               Sequence of actions, recipe, skill.
- UNCLASSIFIED — does not cleanly fit the three above. First-class, not
               a fallback: Ashby's Law says the three kinds cannot represent
               every state, so UNCLASSIFIED is where honest non-fits go.

Tiebreak rule
-------------
The SHAPE of the claim decides, not the subject matter.

  "never commit without tests"              -> SEMANTIC  (rule-shape)
  "to commit: stage, test, push"            -> PROCEDURAL (recipe-shape)
  "yesterday I broke the build by skipping" -> EPISODIC  (instance-shape)
  "commits need tests sometimes, I think"   -> UNCLASSIFIED (no clear shape)

If the claim would still be true with no agent, no time, no instance — it's
SEMANTIC. If it's a sequence of actions the reader could follow — it's
PROCEDURAL. If it references a specific event-in-time — it's EPISODIC.
If none apply cleanly, UNCLASSIFIED.

Falsifier for a classification: if a reader could restate the entry in a
different kind-shape and it would read equally true, the original
classification was probably wrong and UNCLASSIFIED is safer.
"""

from __future__ import annotations

import re

# Regex fragments compiled once at import.
# These are heuristics, not proofs. The classifier is allowed to be wrong;
# UNCLASSIFIED is the safety net.

# Episodic markers: first-person past tense, explicit timestamps, instance refs.
_EPISODIC_PATTERNS = [
    re.compile(r"\b(yesterday|today|last night|this morning|earlier|tonight)\b", re.I),
    re.compile(r"\bon \d{4}-\d{2}-\d{2}\b"),  # ISO date
    re.compile(r"\bI (did|broke|shipped|found|noticed|caught|tried|said|wrote)\b", re.I),
    re.compile(r"\bwhen I (was|had|ran|saw)\b", re.I),
    re.compile(r"\bthat time\b", re.I),
]

# Procedural markers: imperative step sequences, how-to framing.
_PROCEDURAL_PATTERNS = [
    # "to ship:" / "to debug the X:" — verb followed (optionally by words) by colon
    re.compile(r"\bto (do|run|build|ship|fix|debug|deploy|test|commit)\b[^.]*:\s*", re.I),
    re.compile(r"\bstep \d+\b", re.I),
    re.compile(r"\bfirst[,.]? .*\bthen\b", re.I),
    # "then X, then Y" — sequenced steps even without explicit "first"
    re.compile(r"\bthen \w+.*\bthen \w+", re.I),
    re.compile(r"\b\d+[.)]\s+\w+.*\n.*\b\d+[.)]\s+\w+", re.I | re.S),  # numbered list
    re.compile(r"\bhow to\b", re.I),
]

# Semantic markers: rule/principle/fact shape, imperatives without steps,
# timeless claims.
_SEMANTIC_PATTERNS = [
    re.compile(r"\b(never|always|must|should|do not|don't) \w+", re.I),
    re.compile(r"\b(is|are|means|implies|requires|depends on)\b", re.I),
    re.compile(r"^\s*[A-Z][\w\s]+ (is|are|means)\b"),  # "X is Y" leading form
]


def _count_matches(patterns: list[re.Pattern[str]], text: str) -> int:
    """Count how many of `patterns` match anywhere in `text`."""
    return sum(1 for p in patterns if p.search(text))


def classify_kind(content: str) -> str:
    """Heuristically classify a piece of knowledge into a memory kind.

    Returns one of MEMORY_KINDS. UNCLASSIFIED when evidence is weak or
    ambiguous (multiple kinds tie with strong signal).

    This is a SHAPE-of-claim classifier, not a subject-matter classifier.
    A statement about a procedure that's phrased as a rule is SEMANTIC.
    A statement about a rule that's phrased as a recipe is PROCEDURAL.
    """
    if not content or not content.strip():
        return "UNCLASSIFIED"

    text = content.strip()

    episodic = _count_matches(_EPISODIC_PATTERNS, text)
    procedural = _count_matches(_PROCEDURAL_PATTERNS, text)
    semantic = _count_matches(_SEMANTIC_PATTERNS, text)

    scores = {
        "EPISODIC": episodic,
        "PROCEDURAL": procedural,
        "SEMANTIC": semantic,
    }

    max_score = max(scores.values())

    # No signal at all -> UNCLASSIFIED.
    if max_score == 0:
        return "UNCLASSIFIED"

    # Tie at the top -> UNCLASSIFIED. We refuse to guess between strong signals.
    top = [k for k, v in scores.items() if v == max_score]
    if len(top) > 1:
        return "UNCLASSIFIED"

    return top[0]
