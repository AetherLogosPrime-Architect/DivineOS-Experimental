"""Extraction noise filter and temporal-marker detection.

Split from _text.py to keep modules under 500 lines.
"""

import re

# ─── Noise Filter ────────────────────────────────────────────────────

_MIN_CONTENT_WORDS = 3  # content with fewer meaningful words gets skipped

# Patterns that indicate conversational filler with no substance after it.
_CONVERSATIONAL_NOISE = re.compile(
    r"^(how does (it|this|that) (look|feel|seem)[\s?.!]*$|"
    r"any (adjustments|suggestions|thoughts|ideas)[\s?.!]*$|"
    r"sounds good[\s.!]*$|"
    r"that works[\s.!]*$|"
    r"i agree[d]?[\s.!]*$)",
    re.IGNORECASE,
)

# Content that is a task-notification XML tag or system artifact
_SYSTEM_ARTIFACT = re.compile(r"<task-notification|<tool-use-id|<task-id", re.IGNORECASE)


def _is_pure_affirmation(stripped_lower: str) -> bool:
    """Check if content is just an affirmation with filler words."""
    affirmation_core = re.sub(r"[^a-z\s]", "", stripped_lower).strip()
    affirmation_words = affirmation_core.split()
    if not affirmation_words or affirmation_words[0] not in (
        "yes",
        "yeah",
        "yep",
        "ok",
        "okay",
        "sure",
        "proceed",
        "go",
        "lets",
        "do",
        "perfect",
        "wonderful",
        "great",
    ):
        return False

    if any(w in affirmation_words for w in ("because", "since", "reason")):
        return False

    _FILLER_WORDS = {
        "it",
        "do",
        "lets",
        "go",
        "ahead",
        "please",
        "lol",
        "the",
        "and",
        "but",
        "so",
        "then",
        "we",
        "can",
        "this",
        "that",
        "its",
        "im",
        "you",
        "keep",
        "going",
        "now",
        "make",
        "sure",
        "what",
        "just",
        "first",
        "also",
        "get",
        "got",
        "need",
        "needs",
        "want",
        "have",
        "has",
        "done",
        "think",
        "know",
        "like",
        "look",
        "see",
        "try",
        "continue",
        "find",
        "nothing",
        "wrong",
        "right",
        "build",
        "more",
        "stuff",
        "things",
        "thing",
        "for",
        "from",
        "with",
        "about",
        "until",
        "when",
        "where",
        "how",
        "will",
        "would",
        "could",
        "should",
        "still",
        "really",
        "very",
        "much",
        "well",
        "good",
        "new",
        "all",
        "here",
        "there",
        "them",
        "they",
        "been",
        "being",
        "into",
        "some",
        "were",
        "work",
        "start",
        "stop",
    }
    non_affirmation = [w for w in affirmation_words[1:] if w not in _FILLER_WORDS]
    return len(non_affirmation) <= 8


def _is_raw_quote_noise(stripped: str, stripped_lower: str) -> bool:
    """Check if content is raw user quote (casual speech stored verbatim)."""
    double_dot_count = stripped.count("..")
    if double_dot_count >= 3:
        return True
    if double_dot_count >= 2 and re.search(
        r"\b(lol|haha|dont |isnt |cant |wont |arent |youre |theyre |ive |youve )",
        stripped_lower,
    ):
        return True

    casual_count = len(
        re.findall(
            r"(:\)|;\)|:D|<3|lol\b|haha\b|soooo|sooo|dont |isnt |cant |wont |arent |youre )",
            stripped_lower,
        )
    )
    if casual_count >= 2:
        return True

    if re.search(r"\b(oops|whoops|accidentally|i meant to)\b", stripped_lower):
        return True
    if re.match(
        r"(this is what (he|she|they) said|i got a review from|"
        r"here is what|someone said|he said|she said|"
        r"my friend (said|wanted|sent|asked))",
        stripped_lower,
    ):
        return True
    if re.search(
        r"(here is the reply|here is the audit|here is the review|"
        r"here is the report|here is my review|here is my audit|"
        r"hey claude|your move|ready when you are)",
        stripped_lower,
    ):
        return True

    if stripped.rstrip().endswith("..") and len(stripped.split()) < 10:
        return True
    if stripped_lower.startswith(("you ", "if you ", "now you ", "while you ")):
        has_weight = any(
            w in stripped_lower
            for w in (
                "must",
                "always",
                "never",
                "rule",
                "only fixed",
                "forgot",
                "broke",
                "missed",
                "didn't",
                "failed",
            )
        )
        if not has_weight:
            return True
    if stripped_lower.rstrip().endswith("?") and len(stripped.split()) < 20:
        is_tag = stripped_lower.rstrip().endswith(("ok?", "right?", "yes?", "no?"))
        if not is_tag:
            return True
    if re.search(
        r"\b(feel free to|go ahead and|clear it out|clean it up|"
        r"keep going|keep at it|keep it up)\b",
        stripped_lower,
    ):
        return True
    if re.search(
        r"\blets?\s+(commit|push|keep|do|try|fix|run|check|look|merge|ship)\b", stripped_lower
    ):
        return True
    if re.search(
        r"\b(ill go with|i got|i just|i was just|i tried|i need my|"
        r"we need to (clean|commit|push|fix|run|check)|"
        r"how (does|is|do|are) (it|this|that|everything))\b",
        stripped_lower,
    ):
        return True
    if re.search(r"\b(opt out|allow .* to use my data|make sure you opt)\b", stripped_lower):
        return True

    return False


def _is_extraction_noise(content: str, knowledge_type: str) -> bool:
    """Check if extracted content is conversational noise rather than knowledge.

    Returns True if the content should NOT be stored.
    """
    stripped = content
    for prefix in ("I decided: ", "I should: ", "I was corrected: "):
        if stripped.startswith(prefix):
            stripped = stripped[len(prefix) :]
            break

    stripped_lower = stripped.lower().strip()

    if _SYSTEM_ARTIFACT.search(stripped):
        return True

    if re.match(r"^[?!.]{2,}\s", stripped):
        return True

    if _is_pure_affirmation(stripped_lower):
        return True

    if _CONVERSATIONAL_NOISE.match(stripped_lower):
        return True

    # Questions directed at the AI — prompts, not knowledge
    if stripped_lower.endswith("?") and knowledge_type in ("DIRECTION", "PRINCIPLE"):
        is_tag_question = stripped_lower.rstrip().endswith(("ok?", "right?", "yes?", "no?"))
        if not is_tag_question and len(stripped_lower.split()) < 15:
            return True

    if knowledge_type in ("DIRECTION", "PRINCIPLE", "BOUNDARY"):
        if _is_raw_quote_noise(stripped, stripped_lower):
            return True

    # Positive signal check: PRINCIPLE and BOUNDARY must contain prescriptive
    # or declarative structure. Raw quotes lack this. Without it, downgrade
    # happens in the caller — here we just flag it as noise.
    if knowledge_type in ("PRINCIPLE", "BOUNDARY"):
        if not _has_prescriptive_signal(stripped_lower):
            return True

    return False


# ─── Prescriptive Signal Detection ──────────────────────────────────


_PRESCRIPTIVE_PATTERNS = re.compile(
    r"\b("
    # Obligation / prohibition
    r"should|must|always|never|do not|don't|cannot|can't|"
    # Conditional / causal structure
    r"if .+ then|when .+ then|because|in order to|so that|"
    # Rules and preferences
    r"prefer .+ over|rule|principle|directive|requirement|"
    # Declarative knowledge patterns
    r"is (never|always|only|required|forbidden|mandatory)|"
    # Comparative / evaluative
    r"better than|worse than|instead of|rather than|"
    # Lessons learned
    r"lesson|learned|mistake|corrected|fixed|broken|"
    # Needs / importance
    r"needs? (work|fixing|attention|improvement|to be)|still needs|"
    # Identity / self-knowledge
    r"i am|i need to|i will|i refuse|i commit to"
    r")\b",
    re.IGNORECASE,
)


def _has_prescriptive_signal(content_lower: str) -> bool:
    """Check if content has at least one signal that it's a real principle.

    Principles are prescriptive or declarative statements about how things
    should be. Raw user quotes and conversational fragments lack these
    signals. Without at least one, content isn't a principle — it's noise.
    """
    # Short content gets a pass — compact statements are often principles
    if len(content_lower.split()) <= 12:
        return True

    return bool(_PRESCRIPTIVE_PATTERNS.search(content_lower))


# ─── Temporal Markers ────────────────────────────────────────────────

_TEMPORAL_CONTENT_MARKERS = {
    "currently",
    "right now",
    "at the moment",
    "is broken",
    "is failing",
    "is down",
    "today",
    "this week",
    "this sprint",
    "in progress",
    "work in progress",
    "wip",
    "blocked on",
    "waiting for",
    "temporarily",
}


def _has_temporal_markers(content: str) -> bool:
    """Check if content has time-sensitive language that may become stale."""
    content_lower = content.lower()
    return any(marker in content_lower for marker in _TEMPORAL_CONTENT_MARKERS)
