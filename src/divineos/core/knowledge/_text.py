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
        "divineos",
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


# ─── Re-exports from _noise.py (split for file-size hygiene) ────────
from divineos.core.knowledge._noise import (  # noqa: E402
    _CONVERSATIONAL_NOISE as _CONVERSATIONAL_NOISE,
    _MIN_CONTENT_WORDS as _MIN_CONTENT_WORDS,
    _SYSTEM_ARTIFACT as _SYSTEM_ARTIFACT,
    _TEMPORAL_CONTENT_MARKERS as _TEMPORAL_CONTENT_MARKERS,
    _has_temporal_markers as _has_temporal_markers,
    _is_extraction_noise as _is_extraction_noise,
)
