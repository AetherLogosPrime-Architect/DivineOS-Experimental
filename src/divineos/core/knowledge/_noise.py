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


def _is_extraction_noise(content: str, knowledge_type: str) -> bool:
    """Check if extracted content is conversational noise rather than knowledge.

    Returns True if the content should NOT be stored.
    """
    # Strip common prefixes to examine the core content
    stripped = content
    for prefix in ("I decided: ", "I should: ", "I was corrected: "):
        if stripped.startswith(prefix):
            stripped = stripped[len(prefix) :]
            break

    stripped_lower = stripped.lower().strip()

    # System artifacts (XML tags leaked into content)
    if _SYSTEM_ARTIFACT.search(stripped):
        return True

    # Raw user text starting with repeated punctuation (e.g. "??? first off...")
    if re.match(r"^[?!.]{2,}\s", stripped):
        return True

    # Pure affirmation — user just said "yes" with some extra words
    affirmation_core = re.sub(r"[^a-z\s]", "", stripped_lower).strip()
    affirmation_words = affirmation_core.split()
    if affirmation_words and affirmation_words[0] in (
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
        has_reasoning = any(w in affirmation_words for w in ("because", "since", "reason"))
        if not has_reasoning:
            non_affirmation = [
                w
                for w in affirmation_words[1:]
                if w
                not in (
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
                )
            ]
            if len(non_affirmation) <= 8:
                return True

    # Conversational noise pattern match
    if _CONVERSATIONAL_NOISE.match(stripped_lower):
        return True

    # Questions directed at the AI — these are prompts, not knowledge
    if stripped_lower.endswith("?") and knowledge_type in ("DIRECTION", "PRINCIPLE"):
        is_tag_question = stripped_lower.rstrip().endswith(("ok?", "right?", "yes?", "no?"))
        if not is_tag_question:
            question_words = stripped_lower.split()
            if len(question_words) < 15:
                return True

    # Raw user quotes — conversational text stored verbatim
    if knowledge_type in ("DIRECTION", "PRINCIPLE", "BOUNDARY"):
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
            r"(here is the reply|hey claude|your move|ready when you are)",
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
        if re.match(r"lets?\s+(commit|push|keep|do|try|fix|run|check|look)\b", stripped_lower):
            return True
        if re.match(
            r"(ill go with|i got|i just|i was just|i tried|i need my|"
            r"we need to (clean|commit|push|fix|run|check)|"
            r"how (does|is|do|are) (it|this|that|everything))",
            stripped_lower,
        ):
            return True
        if re.search(r"\b(opt out|allow .* to use my data|make sure you opt)\b", stripped_lower):
            return True

    return False


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
