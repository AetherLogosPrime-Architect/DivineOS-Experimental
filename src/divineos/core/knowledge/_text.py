"""Text analysis helpers — normalization, key terms, overlap, noise filtering."""

import re
from collections import Counter

# ─── FTS Stopwords ───────────────────────────────────────────────────

_FTS_STOPWORDS = frozenset(
    {
        "the",
        "and",
        "are",
        "was",
        "for",
        "what",
        "how",
        "who",
        "why",
        "when",
        "where",
        "which",
        "does",
        "that",
        "this",
        "with",
        "from",
        "have",
        "has",
        "had",
        "not",
        "but",
        "can",
        "will",
        "about",
        "its",
        "is",
        "it",
        "be",
        "do",
        "did",
        "been",
        "being",
        "there",
        "their",
        "they",
        "them",
        "than",
        "then",
        "these",
        "those",
        "into",
        "our",
        "you",
        "your",
        "we",
        "my",
        "me",
        "of",
        "in",
        "on",
        "to",
        "a",
        "an",
    }
)


def _build_fts_query(query: str) -> str:
    """Convert natural language query into FTS5 OR-based search.

    Strips stopwords and joins meaningful terms with OR so partial
    matches still return results. Single-word queries pass through as-is.
    """
    words = [
        w
        for w in re.sub(r"[^a-zA-Z0-9\s]", "", query).lower().split()
        if w not in _FTS_STOPWORDS and len(w) > 1
    ]
    if not words:
        return query
    if len(words) == 1:
        return words[0]
    return " OR ".join(words)


# ─── General Stopwords ───────────────────────────────────────────────

_STOPWORDS = frozenset(
    {
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "shall",
        "can",
        "to",
        "of",
        "in",
        "for",
        "on",
        "with",
        "at",
        "by",
        "from",
        "as",
        "into",
        "through",
        "during",
        "before",
        "after",
        "above",
        "below",
        "between",
        "and",
        "but",
        "or",
        "nor",
        "not",
        "so",
        "yet",
        "both",
        "either",
        "neither",
        "each",
        "every",
        "all",
        "any",
        "few",
        "more",
        "most",
        "other",
        "some",
        "such",
        "no",
        "only",
        "same",
        "than",
        "too",
        "very",
        "just",
        "that",
        "this",
        "these",
        "those",
        "i",
        "you",
        "he",
        "she",
        "it",
        "we",
        "they",
        "me",
        "him",
        "her",
        "us",
        "them",
        "my",
        "your",
        "his",
        "its",
        "our",
        "their",
        "what",
        "which",
        "who",
        "whom",
        "when",
        "where",
        "why",
        "how",
        "if",
        "then",
        "else",
        "here",
        "there",
        "also",
        "about",
        "up",
        "out",
        "down",
        "off",
        "over",
        "under",
        "again",
        "further",
        "once",
        "like",
        "well",
        "back",
        "even",
        "still",
        "way",
        "get",
        "got",
        "let",
        "say",
        "said",
        "go",
        "going",
        "went",
        "come",
        "came",
        "make",
        "made",
        "take",
        "took",
        "see",
        "saw",
        "know",
        "knew",
        "think",
        "thought",
        "want",
        "need",
        "use",
        "used",
        "try",
        "tried",
        "look",
        "looked",
        "give",
        "gave",
        "tell",
        "told",
        "work",
        "worked",
        "call",
        "called",
        "yes",
        "ok",
        "okay",
        "yeah",
        "sure",
        "right",
        "now",
        "one",
        "two",
        "first",
        "new",
        "old",
        "good",
        "bad",
        "big",
        "small",
        "much",
        "many",
        "long",
        "little",
        "thing",
        "things",
        "something",
        "anything",
        "everything",
        "nothing",
        "im",
        "dont",
        "doesnt",
        "didnt",
        "isnt",
        "arent",
        "wasnt",
        "werent",
        "wont",
        "cant",
        "couldnt",
        "shouldnt",
        "wouldnt",
        "thats",
        "lets",
        "ive",
        "youre",
        "theyre",
        "hes",
        "shes",
        # AI coding conversation filler
        "file",
        "files",
        "code",
        "run",
        "running",
        "output",
        "tool",
        "tools",
        "command",
        "task",
        "tasks",
        "check",
        "set",
        "add",
        "added",
        "change",
        "changes",
        "changed",
        "put",
        "read",
        "show",
        "done",
        "lol",
        "haha",
        "hey",
        "thanks",
        "thank",
        "please",
        "help",
        "claude",
        "kiro",
        "notification",
        "users",
        "user",
        "keep",
        "start",
        "stop",
        "already",
        "pretty",
        "really",
        "actually",
        "basically",
        "everything",
        "able",
    },
)


# ─── Text Analysis ───────────────────────────────────────────────────


def _normalize_text(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _extract_key_terms(text: str) -> str:
    """Remove stopwords, return space-separated key terms for FTS5 queries."""
    normalized = _normalize_text(text)
    words = normalized.split()
    terms = [w for w in words if w not in _STOPWORDS and len(w) > 2]
    # Deduplicate while preserving order
    seen: set[str] = set()
    unique = []
    for t in terms:
        if t not in seen:
            seen.add(t)
            unique.append(t)
    return " ".join(unique[:20])  # cap at 20 terms for FTS5 query


def _compute_overlap(text_a: str, text_b: str) -> float:
    """Compute word set overlap between two texts. Returns 0.0-1.0."""
    words_a = set(_normalize_text(text_a).split()) - _STOPWORDS
    words_b = set(_normalize_text(text_b).split()) - _STOPWORDS
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    smaller = min(len(words_a), len(words_b))
    return len(intersection) / smaller


def extract_session_topics(user_texts: list[str], top_n: int = 8) -> list[str]:
    """Extract top topics from user messages using word frequency analysis."""
    word_counts: Counter[str] = Counter()
    for text in user_texts:
        words = _normalize_text(text).split()
        meaningful = [w for w in words if w not in _STOPWORDS and len(w) > 2]
        word_counts.update(meaningful)
    return [word for word, _ in word_counts.most_common(top_n)]


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
