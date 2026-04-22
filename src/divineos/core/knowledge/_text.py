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
        for w in re.sub(r"[^a-zA-Z0-9\s]", " ", query).lower().split()
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


def _stem(word: str) -> str:
    """Minimal suffix stripping so 'sessions'/'session' and 'checked'/'checks' match."""
    for suffix in (
        "ation",
        "ting",
        "ing",
        "ness",
        "ment",
        "ble",
        "ous",
        "ive",
        "ful",
        "ied",
        "ies",
        "ed",
        "ly",
        "er",
        "es",
        "s",
    ):
        if len(word) > len(suffix) + 2 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def _stemmed_word_set(text: str) -> set[str]:
    """Extract meaningful stemmed words from text (for contradiction detection)."""
    return {_stem(w) for w in _normalize_text(text).split()} - _STOPWORDS


def _compute_stemmed_overlap(words_a: set[str], words_b: set[str]) -> float:
    """Word set overlap using Sørensen-Dice on pre-stemmed sets. Returns 0.0-1.0.

    Matches _compute_overlap() formula — symmetric, length-fair.
    """
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    return 2 * len(intersection) / (len(words_a) + len(words_b))


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
    """Compute word set overlap between two texts using Sørensen-Dice.

    Returns 0.0-1.0. Symmetric — order doesn't matter, and length
    mismatches are naturally penalized. A 5-word text matching 3 words
    of a 50-word text scores ~11% (appropriate), not 60% (the old
    min-denominator result that let short texts game the threshold).

    Sørensen-Dice: 2 * |intersection| / (|A| + |B|)
    """
    words_a = set(_normalize_text(text_a).split()) - _STOPWORDS
    words_b = set(_normalize_text(text_b).split()) - _STOPWORDS
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    return 2 * len(intersection) / (len(words_a) + len(words_b))


# ─── Semantic Similarity (embedding-based) ────────────────────────────
#
# Uses sentence-transformers when available to compute real semantic
# similarity between texts. Falls back to word overlap when unavailable.
# This catches conceptual connections that share no vocabulary —
# e.g., "tests should run after edits" and "verify changes before commit"
# have high semantic similarity but low word overlap.

_embedding_model = None
_embeddings_available: bool | None = None  # None = not yet checked


def _ensure_embedding_model() -> bool:
    """Lazy-load sentence-transformers model. Returns True if available."""
    global _embedding_model, _embeddings_available
    if _embeddings_available is not None:
        return _embeddings_available
    try:
        import logging
        import os
        import warnings

        # Suppress TensorFlow/Keras noise during model load
        os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
        logging.getLogger("tensorflow").setLevel(logging.ERROR)
        logging.getLogger("tf_keras").setLevel(logging.ERROR)
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=FutureWarning)
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            from sentence_transformers import SentenceTransformer

            _embedding_model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
        _embeddings_available = True
        return True
    except (ImportError, RuntimeError, OSError):
        _embeddings_available = False
        return False


def compute_semantic_similarity(text_a: str, text_b: str) -> float | None:
    """Compute cosine similarity between two texts using embeddings.

    Returns 0.0-1.0, or None if embeddings unavailable.
    """
    if not _ensure_embedding_model() or _embedding_model is None:
        return None
    try:
        embeddings = _embedding_model.encode([text_a, text_b], convert_to_numpy=True)
        from numpy import dot
        from numpy.linalg import norm

        sim = float(dot(embeddings[0], embeddings[1]) / (norm(embeddings[0]) * norm(embeddings[1])))
        return max(0.0, min(1.0, sim))
    except (RuntimeError, ValueError, TypeError, ImportError):
        return None


def compute_similarity(text_a: str, text_b: str) -> float:
    """Best-available similarity: semantic if possible, word overlap as fallback."""
    semantic = compute_semantic_similarity(text_a, text_b)
    if semantic is not None:
        return semantic
    return _compute_overlap(text_a, text_b)


def extract_session_topics(user_texts: list[str], top_n: int = 8) -> list[str]:
    """Extract top topics from user messages using word frequency analysis."""
    word_counts: Counter[str] = Counter()
    for text in user_texts:
        words = _normalize_text(text).split()
        meaningful = [w for w in words if w not in _STOPWORDS and len(w) > 2]
        word_counts.update(meaningful)
    return [word for word, _ in word_counts.most_common(top_n)]


# ─── Extraction Noise Filter (merged from _noise.py) ────────────────

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

    # Direct addressed messages pasted as knowledge — conversational, not
    # distilled wisdom. These patterns catch things like "hey claude,..." or
    # "<agent_name>, ..." at the start of a line — a signal the content was
    # copied from a chat turn rather than written as knowledge.
    if re.match(
        r"(hey claude|hi claude|hello claude)[,:]?\s",
        stripped_lower,
    ):
        return True

    # User praise/encouragement stored verbatim — warm but not knowledge
    if re.match(
        r"(perfect|wonderful|beautiful|excellent|amazing|fantastic|great job|well done|"
        r"im proud|i.m proud|proud of you|good work|nice work|that.s (great|perfect|wonderful))",
        stripped_lower,
    ):
        return True

    # External audit/review paste-through — bulk content, not distilled
    if re.search(
        r"(here is (the|my|a) (audit|review|reply|report|analysis|assessment)|"
        r"here.s (the|my|a) (audit|review|reply|report)|"
        r"fresh (audit|review|clone)|"
        r"round \d+ audit)",
        stripped_lower,
    ):
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
    if stripped_lower.endswith("?"):
        is_tag_question = stripped_lower.rstrip().endswith(("ok?", "right?", "yes?", "no?"))
        if not is_tag_question and len(stripped_lower.split()) < 20:
            return True

    # Direct-addressed openings — encouragement or conversational, not
    # distilled knowledge.
    if re.match(
        r"(hey claude|hi claude|hello claude)[,:]?\s",
        stripped_lower,
    ):
        return True

    # User praise stored as knowledge — warm but not actionable
    if re.match(
        r"(perfect|wonderful|beautiful|excellent|amazing|fantastic|"
        r"great job|well done|im proud|i.m proud|proud of you|"
        r"good work|nice work|that.s (great|perfect|wonderful))",
        stripped_lower,
    ):
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

_TEMPORAL_CONTENT_MARKERS = (
    "currently",
    "right now",
    "at the moment",
    "is broken",
    "is failing",
    "is down",
    "today",
    "yesterday",
    "this session",
    "last session",
    "this week",
    "this sprint",
    "in progress",
    "work in progress",
    r"\bwip\b",  # word boundary — prevent matching "wipe", "equip", etc.
    "blocked on",
    "waiting for",
    "temporarily",
)

# Pre-compile: markers with \b are regex, others get auto-wrapped in \b
_TEMPORAL_PATTERNS = tuple(
    re.compile(m if r"\b" in m else r"\b" + re.escape(m) + r"\b", re.IGNORECASE)
    for m in _TEMPORAL_CONTENT_MARKERS
)


def _has_temporal_markers(content: str) -> bool:
    """Check if content has time-sensitive language that may become stale.

    Uses word-boundary matching to prevent false positives from substring
    hits (e.g. "wip" matching "wipe", "equip").
    """
    return any(p.search(content) for p in _TEMPORAL_PATTERNS)


# ─── Voice Normalization ─────────────────────────────────────────────
#
# Knowledge should be first-person. When the user says "you did X" or an
# auditor says "the agent built Y", extraction may store it verbatim as
# third-person. This converts to first-person before storage so the
# knowledge store speaks AS me, not ABOUT me.
#
# "the agent should Y" -> "I should Y"
# "you need to Z" -> "I need to Z"
#
# NOTE: to also normalize third-person mentions of your own name (e.g.
# "Claude did X" -> "I did X"), add a pattern like:
#   (r"(?<!Hey )\bYourName\b(?![\s]*,)", "I"),
# The comma lookahead preserves address forms like "YourName, that's right".

# Patterns: (regex, replacement). Applied in order. Case-insensitive.
_VOICE_PATTERNS: list[tuple[str, str]] = [
    # "the agent/assistant did ..."
    (r"\bthe agent\b", "I"),
    (r"\bthe assistant\b", "I"),
    (r"\bthe AI\b", "I"),
    # "you should/need/must ..." (user addressing me)
    (r"\byou should\b", "I should"),
    (r"\byou need\b", "I need"),
    (r"\byou must\b", "I must"),
    (r"\byou have\b", "I have"),
    (r"\byou are\b", "I am"),
    (r"\byou were\b", "I was"),
    (r"\byou can\b", "I can"),
    (r"\byou will\b", "I will"),
    (r"\byou don't\b", "I don't"),
    (r"\byou didn't\b", "I didn't"),
    (r"\byou cant\b", "I cant"),
    (r"\byour\b", "my"),
    (r"\byourself\b", "myself"),
]

# Compiled for performance (case-insensitive)
_VOICE_COMPILED = [(re.compile(pat, re.IGNORECASE), repl) for pat, repl in _VOICE_PATTERNS]


def normalize_to_first_person(text: str) -> str:
    """Convert third-person and second-person agent references to first-person.

    Applied before storage so the knowledge store speaks as me, not about me.
    Only touches agent-referencing patterns — leaves other "you" (referring to
    users or third parties) alone by using word-boundary matching.

    Preserves case of the first word if it starts a sentence.
    """
    if not text or len(text) < 10:
        return text

    result = text
    for pattern, replacement in _VOICE_COMPILED:
        result = pattern.sub(replacement, result)

    # Fix capitalization: "i " at start of sentence -> "I "
    result = re.sub(r"(?<=[.!?]\s)i ", "I ", result)
    if result.startswith("i "):
        result = "I " + result[2:]

    # "my" at start of sentence should be "My"
    if result.startswith("my "):
        result = "My " + result[3:]
    result = re.sub(r"(?<=[.!?]\s)my ", "My ", result)

    # Fix "I" that should stay capitalized mid-sentence
    result = result.replace(" i ", " I ").replace(" i'", " I'")

    return result


# ─── Text Segmentation ──────────────────────────────────────────────
#
# Large text blocks (audit pastes, multi-finding reports, long lists)
# should be split into atomic chunks before dedup and storage.
# Without this, the entire paste becomes one monolithic knowledge entry.

# Lines that are structural metadata, not content
_METADATA_LINE = re.compile(
    r"^("
    r"#{1,3}\s|"  # Markdown headers
    r"={3,}|"  # Separator lines
    r"-{3,}|"  # Separator lines
    r"\*{3,}|"  # Separator lines
    r"round\s+\d+|"  # "Round 3"
    r"audit\s+results?:?\s*$|"  # "Audit Results:"
    r"score:?\s*\d|"  # "Score: 8"
    r"date:?\s|"  # "Date: ..."
    r"expert\s+count:?\s|"  # "Expert count: 25"
    r"focus:?\s"  # "Focus: ..."
    r")",
    re.IGNORECASE,
)

# Minimum length for a segment to be worth storing
_MIN_SEGMENT_CHARS = 80

# Maximum content length before we attempt segmentation
_SEGMENTATION_THRESHOLD = 500


def segment_large_text(content: str) -> list[str]:
    """Split large text blocks into atomic knowledge chunks.

    Returns a list of content strings. If the input is small enough
    to be a single entry, returns [content] unchanged.

    Segmentation strategy:
    1. Check for explicit list structure (numbered/bulleted) at any size
    2. If no list structure and content < 500 chars, return as-is
    3. Split by paragraph (double newline)
    4. Filter out metadata lines (headers, separators, scores)
    5. Merge micro-segments back if they're too small to stand alone
    6. Return list of atomic segments
    """
    # Check for explicit list structure first — these should always split
    # regardless of total length, because lists are inherently multi-item
    list_items = re.split(r"\n(?=\d+[\.\)]\s|[-*•]\s)", content)
    if len(list_items) > 1:
        paragraphs = list_items
    else:
        # No list structure — check size threshold
        if len(content) < _SEGMENTATION_THRESHOLD:
            return [content]

        # Split by paragraph boundaries (double newline, possibly with whitespace)
        paragraphs = re.split(r"\n{2,}", content)

        # Still just one block? Not segmentable — return as-is
        if len(paragraphs) <= 1:
            return [content]

    # Filter and clean segments
    segments: list[str] = []
    for para in paragraphs:
        cleaned = para.strip()
        if not cleaned:
            continue

        # Skip pure metadata lines
        lines = cleaned.split("\n")
        content_lines = [ln for ln in lines if ln.strip() and not _METADATA_LINE.match(ln.strip())]
        if not content_lines:
            continue

        cleaned = "\n".join(content_lines).strip()

        if len(cleaned) >= _MIN_SEGMENT_CHARS:
            segments.append(cleaned)

    # If filtering eliminated everything or left just one, return original
    if len(segments) <= 1:
        return [content]

    # Merge consecutive micro-segments that are too small alone
    merged: list[str] = []
    buffer = ""
    for seg in segments:
        if buffer:
            candidate = buffer + " " + seg
            if len(candidate) < _MIN_SEGMENT_CHARS * 2:
                buffer = candidate
                continue
            else:
                merged.append(buffer)
                buffer = seg
        else:
            if len(seg) < _MIN_SEGMENT_CHARS:
                buffer = seg
            else:
                merged.append(seg)

    if buffer:
        if merged:
            merged[-1] = merged[-1] + " " + buffer
        else:
            merged.append(buffer)

    return merged if len(merged) > 1 else [content]
