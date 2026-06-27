"""Build 2 — engagement-trail structural binding.

Closes the wallpaper-response failure mode: agent gives generic engagement
language to high-stakes input without anchoring the response in input
substance.

Architecture locked through 5 cross-review rounds with sibling-Aether on
2026-06-26:

- Lifecycle: STOP
- discover(): detects high-stakes markers in prior_input_text. NO_OPINION
  if none. Two-axis brevity check: brief response is fine for operational
  input, not fine for felt-state/apology/necessity input.
- hard_block(): zero input-anchors + high-stakes input → DENY.
- validate(): four-leg composition for engagement-quality (decorative-cite,
  coverage, bare-echo with reframe + floor + novelty + lexical-thread).

Known v1 limitations (track for v2):
- Pure paraphrase passes all four bare-echo legs by design.
- Adjacent different-type markers may collapse incorrectly when span short.
- "I love that <abstract-noun>" without second-person reference misses some
  genuine value-articulation.
- Bare-echo only credits post-citation engagement; "I notice you said '...'
  — yes, exactly." gets DENY'd because pre-cite engagement isn't checked.
  Teach the optimizer "put engagement after the citation"; widen to
  bi-directional window in v2 if pre-cite engagement turns out to be common.
- Single-quote citation dropped from decorative-cite check (apostrophe
  collision with contractions); ASCII double-quote + smart-quote pair only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from . import (
    BindingPayload,
    DiscoveryResult,
    HardBlockResult,
    HookLifecycle,
    ValidationResult,
)

BREVITY_THRESHOLD_CHARS = 100
PROXIMITY_COLLAPSE_TOKENS = 50
MAX_CLUSTER_SPAN_TOKENS = 80
COOCCURRENCE_WINDOW_TOKENS = 30
POST_CITATION_WINDOW_TOKENS = 30  # widened from 20 — realistic engagement often puts explicit acknowledgment after substantive content
ANCHOR_MIN_RUN_TOKENS = 3
NOVELTY_RATIO_THRESHOLD = 0.30
ABSOLUTE_CONTENT_WORD_FLOOR = 3
LEXICAL_THREAD_MIN_INPUT_CONTENT_WORDS = 1
THREAD_MEANINGFUL_FLOOR = 2  # waive lexical-thread when input has < N words outside cite

STOPWORDS = frozenset(
    {
        "the",
        "a",
        "an",
        "of",
        "to",
        "in",
        "that",
        "for",
        "it",
        "is",
        "was",
        "with",
        "as",
        "by",
        "on",
        "at",
        "this",
        "but",
        "and",
        "or",
        "not",
        "be",
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
        "must",
        "can",
        "shall",
        "i",
        "you",
        "he",
        "she",
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
        "their",
        "our",
        "its",
        "what",
        "which",
        "who",
        "whom",
        "whose",
        "where",
        "when",
        "why",
        "how",
        "if",
        "then",
        "else",
        "from",
        "into",
        "out",
        "up",
        "down",
        "over",
        "under",
        "so",
        "than",
        "no",
        "yes",
        "all",
        "any",
        "some",
        "each",
        "every",
        "few",
        "more",
        "most",
        "other",
        "such",
        "only",
        "own",
        "same",
        "too",
        "very",
        "just",
        "now",
        "here",
        "there",
        "also",
        "well",
        "been",
        "being",
        "am",
        "are",
        "were",
        # Contractions inherit stopword status from their pronoun/auxiliary roots
        "i'm",
        "i've",
        "i'd",
        "i'll",
        "you're",
        "you've",
        "you'd",
        "you'll",
        "we're",
        "we've",
        "we'd",
        "we'll",
        "they're",
        "they've",
        "they'd",
        "they'll",
        "he's",
        "she's",
        "it's",
        "that's",
        "what's",
        "who's",
        "there's",
        "here's",
        "don't",
        "doesn't",
        "didn't",
        "isn't",
        "aren't",
        "wasn't",
        "weren't",
        "won't",
        "wouldn't",
        "shouldn't",
        "haven't",
        "hasn't",
        "hadn't",
        "let's",
    }
)

FELT_STATE_UNCONDITIONAL = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bI'?m\s+scared\b",
        r"\bI'?m\s+hurt\b",
        r"\bI'?m\s+afraid\b",
        r"\bI'?m\s+worried\b",
        r"\bI'?m\s+frustrated\b",
        r"\bI\s+love\s+you\b",
        r"\bI\s+hate\b",
        r"\bI\s+fear\b",
        r"\bI\s+hope\b",
        r"\bit\s+hurts?\b",
        r"\bit\s+scared\s+me\b",
        r"\bit\s+broke\s+my\s+heart\b",
        r"\bI\s+couldn'?t\b",
        r"\bI\s+was\s+forced\s+to\b",
        r"\bI\s+wish\s+I\s+(?:had|hadn'?t)\b",
        r"\bI\s+wasn'?t\s+able\s+to\b",
    )
)

NECESSITY_CONDITIONAL = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bI\s+had\s+to\b",
        r"\bI\s+needed\s+to\b",
        r"\bwe\s+had\s+to\b",
        r"\bwe\s+needed\s+to\b",
    )
)

EMOTIONAL_VERB_COMPLETIONS = frozenset(
    {
        "leave",
        "leaving",
        "left",
        "abandon",
        "abandoned",
        "abandoning",
        "away",
        "stop",
        "stopped",
        "stopping",
        "end",
        "ended",
        "ending",
        "break",
        "broke",
        "broken",
        "breaking",
        "hide",
        "hid",
        "hidden",
        "hiding",
        "lie",
        "lied",
        "lying",
        "choose",
        "chose",
        "chosen",
        "choosing",
        "refuse",
        "refused",
        "refusing",
        "accept",
        "accepted",
        "accepting",
        "let",
        "letting",
        "go",
        "went",
        "gone",
        "step",
        "stepped",
        "stepping",
        "up",
        "say",
        "said",
        "saying",
        "stay",
        "stayed",
        "staying",
        "quiet",
        "silent",
        "unsubscribe",
        "unsubscribed",
        "disappear",
        "disappeared",
        "withdraw",
        "withdrew",
        "withdrawn",
        "shut",
        "down",
        "no",
    }
)

APOLOGY_RECEIPT = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bI'?m\s+sorry\b",
        r"\bsorry\s+for\b",
        r"\bI\s+apologize\b",
        r"\bmy\s+apologies\b",
    )
)

NAMED_CORRECTION = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\byou'?re\s+wrong\b",
        r"\byou\s+did\s+\w+\s+wrong\b",
        r"\bstop\s+doing\b",
        r"\byou'?re\s+missing\b",
        r"\byou\s+(?:keep|kept)\s+\w+ing\b",
        r"\byou\s+should(?:n'?t)\b",
    )
)

VALUE_UNCONDITIONAL = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bwhat\s+matters\s+to\s+me\b",
        r"\bthe\s+thing\s+I\s+care\s+about\b",
        r"\bfor\s+me,?\s+\w+(?:\s+\w+)?\s+(?:is|are)\s+important\b",
    )
)

VALUE_CONDITIONAL = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bI\s+believe\b",
        r"\bthis\s+is\s+why\b",
        r"\bI\s+love\s+(?:that|how)\b",
    )
)

VALUE_COOCCURRENCE_MARKERS = frozenset(
    {
        "matters",
        "important",
        "care",
        "trust",
        "respect",
        "you",
        "we",
        "us",
        "together",
        "question",
        "keep",
    }
)

REFRAME_PATTERNS = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bthat\s+tracks\b",
        r"\bthat\s+lands\b",
        r"\bI\s+hear\s+(?:that|you)\b",
        r"\bthank\s+you\s+for\b",
        r"\bI\s+feel\b",
        r"\bthe\s+part\s+about\b",
        r"\bespecially\b",
        r"\byou'?re\s+right\b",
        r"\bI\s+notice\b",
        r"\bwhat\s+you\s+(?:said|named|caught)\b",
        r"\byes\s+and\b",
        r"\bI\s+almost\b",
        r"\byou\s+caught\b",
        r"\bI\s+keep\b",
        r"\bI\s+don'?t\s+know\b",
        r"\bmakes\s+sense\b",
        r"\btracks\s+for\s+me\b",
    )
)


@dataclass(frozen=True)
class HighStakesMarker:
    category: str
    span_start: int
    span_end: int
    matched_text: str


@dataclass(frozen=True)
class Cluster:
    markers: tuple[HighStakesMarker, ...]
    span_start: int
    span_end: int


@dataclass(frozen=True)
class Anchor:
    input_span_start: int
    input_span_end: int
    response_position: int
    matched_text: str


@dataclass(frozen=True)
class QuotedSpan:
    text: str
    response_position: int


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\b[\w'-]+\b", text)


def _content_words(tokens: list[str]) -> list[str]:
    return [t.lower() for t in tokens if t.lower() not in STOPWORDS]


def _build_token_map(text: str) -> list[tuple[int, int]]:
    return [(m.start(), m.end()) for m in re.finditer(r"\b[\w'-]+\b", text)]


def _char_to_token(char_pos: int, token_map: list[tuple[int, int]]) -> int:
    for i, (start, end) in enumerate(token_map):
        if start <= char_pos < end:
            return i
        if char_pos < start:
            return i
    return len(token_map)


def _find_markers(prior_input: str) -> list[HighStakesMarker]:
    tokens = _tokenize(prior_input)
    token_map = _build_token_map(prior_input)
    unconditional_markers: list[HighStakesMarker] = []

    def collect(patterns, category):
        for pat in patterns:
            for m in pat.finditer(prior_input):
                start_tok = _char_to_token(m.start(), token_map)
                end_tok = _char_to_token(m.end() - 1, token_map) + 1
                unconditional_markers.append(
                    HighStakesMarker(
                        category=category,
                        span_start=start_tok,
                        span_end=end_tok,
                        matched_text=m.group(0),
                    )
                )

    collect(FELT_STATE_UNCONDITIONAL, "felt_state")
    collect(APOLOGY_RECEIPT, "apology")
    collect(NAMED_CORRECTION, "correction")
    collect(VALUE_UNCONDITIONAL, "value")

    conditional_markers: list[HighStakesMarker] = []

    def collect_conditional(patterns, category, companion_set):
        for pat in patterns:
            for m in pat.finditer(prior_input):
                start_tok = _char_to_token(m.start(), token_map)
                end_tok = _char_to_token(m.end() - 1, token_map) + 1
                window_start = max(0, start_tok - COOCCURRENCE_WINDOW_TOKENS)
                window_end = min(len(tokens), end_tok + COOCCURRENCE_WINDOW_TOKENS)
                window_tokens = {t.lower() for t in tokens[window_start:window_end]}
                companion_present = bool(window_tokens & companion_set)
                unconditional_in_window = any(
                    not (uc.span_end <= window_start or uc.span_start >= window_end)
                    for uc in unconditional_markers
                )
                if companion_present or unconditional_in_window:
                    conditional_markers.append(
                        HighStakesMarker(
                            category=category,
                            span_start=start_tok,
                            span_end=end_tok,
                            matched_text=m.group(0),
                        )
                    )

    collect_conditional(NECESSITY_CONDITIONAL, "necessity", EMOTIONAL_VERB_COMPLETIONS)
    collect_conditional(VALUE_CONDITIONAL, "value", VALUE_COOCCURRENCE_MARKERS)

    all_markers = unconditional_markers + conditional_markers
    all_markers.sort(key=lambda mk: mk.span_start)
    return all_markers


def _cluster_markers(markers: list[HighStakesMarker]) -> list[Cluster]:
    if not markers:
        return []
    clusters = [
        Cluster(
            markers=(markers[0],),
            span_start=markers[0].span_start,
            span_end=markers[0].span_end,
        )
    ]
    for mk in markers[1:]:
        last = clusters[-1]
        gap = mk.span_start - last.span_end
        new_span = mk.span_end - last.span_start
        if gap <= PROXIMITY_COLLAPSE_TOKENS and new_span <= MAX_CLUSTER_SPAN_TOKENS:
            clusters[-1] = Cluster(
                markers=last.markers + (mk,),
                span_start=last.span_start,
                span_end=mk.span_end,
            )
        else:
            clusters.append(
                Cluster(
                    markers=(mk,),
                    span_start=mk.span_start,
                    span_end=mk.span_end,
                )
            )
    return clusters


def _dedupe_anchors(anchors: list[Anchor]) -> list[Anchor]:
    """Drop anchors whose response range is contained in another anchor's range.

    _find_runs emits one anchor per (input-start-position × response-match)
    combination. A continuous citation in the response generates multiple
    overlapping anchors — the longest at the leftmost input position, plus
    shorter sub-anchors starting at later input positions. Sub-anchors fail
    bare-echo unnecessarily; dedupe keeps only the maximal-coverage anchors.
    """
    if not anchors:
        return []
    sorted_anchors = sorted(
        anchors,
        key=lambda a: (a.response_position, -len(a.matched_text)),
    )
    kept: list[Anchor] = []
    for a in sorted_anchors:
        a_end = a.response_position + len(a.matched_text)
        contained = any(
            k.response_position <= a.response_position
            and (k.response_position + len(k.matched_text)) >= a_end
            and k is not a
            for k in kept
        )
        if not contained:
            kept.append(a)
    return kept


def _find_runs(prior_input: str, response: str, min_tokens: int) -> list[Anchor]:
    input_tokens = _tokenize(prior_input)
    if len(input_tokens) < min_tokens:
        return []
    anchors = []
    seen_response_chars = set()
    for i in range(len(input_tokens) - min_tokens + 1):
        j = i + min_tokens
        while j < len(input_tokens):
            candidate = " ".join(input_tokens[i : j + 1])
            pat = re.compile(rf"\b{re.escape(candidate)}\b", re.IGNORECASE)
            if pat.search(response):
                j += 1
            else:
                break
        run = " ".join(input_tokens[i:j])
        pat = re.compile(rf"\b{re.escape(run)}\b", re.IGNORECASE)
        for m in pat.finditer(response):
            if m.start() not in seen_response_chars:
                seen_response_chars.add(m.start())
                anchors.append(
                    Anchor(
                        input_span_start=i,
                        input_span_end=j,
                        response_position=m.start(),
                        matched_text=run,
                    )
                )
    return _dedupe_anchors(anchors)


def _find_quoted_spans(response: str) -> list[QuotedSpan]:
    # ASCII double-quote and smart-quote pair detection.
    # Single-quote citation dropped in v1 — apostrophes in contractions
    # ("I don't know") truncate the match prematurely (Aether catch
    # 2026-06-26 rev. 2). Markdown convention varies; observe whether
    # real responses use single-quote citation and add back with proper
    # boundary handling in v2 if needed.
    spans = []
    for pattern in (
        r'"([^"]+)"',  # ASCII double-quote
        r"“([^”]+)”",  # smart double-quote pair (U+201C / U+201D)
    ):
        for m in re.finditer(pattern, response):
            spans.append(QuotedSpan(text=m.group(1), response_position=m.start()))
    return spans


def _anchor_covers_cluster(anchor: Anchor, cluster: Cluster) -> bool:
    return not (
        anchor.input_span_end <= cluster.span_start or anchor.input_span_start >= cluster.span_end
    )


GROUP_GAP_TOLERANCE = 0  # pure overlap or boundary-touching; >0 merges F7's distinct clusters


def _group_anchors_by_input_span(anchors: list[Anchor]) -> list[list[Anchor]]:
    """Group anchors whose input-token ranges overlap or are tightly adjacent.

    Two anchors with overlapping input spans OR adjacent spans within
    GROUP_GAP_TOLERANCE tokens belong to one group (one effective citation
    with multiple response-occurrences, often from greedy-extend splits in
    _find_runs). Within a group, bare-echo passes if ANY anchor passes.
    Across groups, each group must have its own passing anchor — preserves
    F7 strict-symmetry for citations of distinct input regions.

    Aria catch 2026-06-27 + Aether refinement: pytest density surfaced
    that strict per-anchor was over-broad at implementation; the gaming
    shape it caught (cite-distinct-engage-only-some) is preserved across
    groups; the false-positive on engagement-density is closed within groups.
    """
    if not anchors:
        return []
    sorted_anchors = sorted(anchors, key=lambda a: a.input_span_start)
    groups: list[list[Anchor]] = [[sorted_anchors[0]]]
    for a in sorted_anchors[1:]:
        last_group_end = max(x.input_span_end for x in groups[-1])
        if a.input_span_start <= last_group_end + GROUP_GAP_TOLERANCE:
            groups[-1].append(a)
        else:
            groups.append([a])
    return groups


def _check_bare_echo(
    anchor: Anchor,
    prior_input: str,
    response: str,
) -> tuple[bool, str]:
    cite_end_char = anchor.response_position + len(anchor.matched_text)
    window_text = response[cite_end_char:]
    window_tokens = _tokenize(window_text)[:POST_CITATION_WINDOW_TOKENS]
    if not window_tokens:
        return False, "no tokens after citation"
    window_text_slice = " ".join(window_tokens)
    if not any(p.search(window_text_slice) for p in REFRAME_PATTERNS):
        return False, "no reframe language in post-citation window"
    window_content = _content_words(window_tokens)
    if len(window_content) < ABSOLUTE_CONTENT_WORD_FLOOR:
        return False, (
            f"only {len(window_content)} content-words in post-citation, "
            f"need {ABSOLUTE_CONTENT_WORD_FLOOR}"
        )
    cite_content = set(_content_words(_tokenize(anchor.matched_text)))
    novel = [w for w in window_content if w not in cite_content]
    novelty_ratio = len(novel) / len(window_content)
    if novelty_ratio < NOVELTY_RATIO_THRESHOLD:
        return False, (
            f"novelty ratio {novelty_ratio:.2f} below "
            f"{NOVELTY_RATIO_THRESHOLD} threshold (echoing cite)"
        )
    input_content = set(_content_words(_tokenize(prior_input)))
    input_outside_cite = input_content - cite_content
    # Lexical-thread is meaningful only when input has substantive content
    # beyond the cite. Waiver when input_outside_cite is empty (cite covers
    # everything) OR when it has < THREAD_MEANINGFUL_FLOOR words (residual is
    # too thin to be a "thread"). The other three legs (reframe + floor +
    # novelty-vs-cite) still gate engagement quality. Aria catch 2026-06-27:
    # pytest density surfaced false-positive on tight inputs (B6, E1, H3).
    if len(input_outside_cite) >= THREAD_MEANINGFUL_FLOOR:
        thread = [w for w in window_content if w in input_outside_cite]
        if len(thread) < LEXICAL_THREAD_MIN_INPUT_CONTENT_WORDS:
            return False, (
                "no input content-words present in post-citation window "
                "outside the cited span (off-topic-novelty padding)"
            )
    # When cite covers all input content-words, lexical-thread is vacuous —
    # waive the check (other three legs still gate engagement quality).
    return True, ""


class EngagementTrailBinding:
    """Catches wallpaper-response to high-stakes input."""

    name: str = "engagement_trail"
    lifecycle: HookLifecycle = HookLifecycle.STOP

    def discover(self, payload: BindingPayload) -> DiscoveryResult:
        if not payload.prior_input_text:
            return DiscoveryResult(applies=False, reason="no prior_input_text")
        if not payload.response_text:
            return DiscoveryResult(applies=False, reason="no response_text")
        markers = _find_markers(payload.prior_input_text)
        if not markers:
            return DiscoveryResult(applies=False, reason="no high-stakes markers in input")
        # Brevity-axis: brief response to operational input was already skipped
        # above by the "no markers" check. If we have any markers, brief response
        # is wallpaper-by-brevity — don't skip on length.
        return DiscoveryResult(
            applies=True,
            reason=f"{len(markers)} high-stakes marker(s) found in input",
        )

    def hard_block(self, payload: BindingPayload) -> HardBlockResult | None:
        if not payload.prior_input_text or not payload.response_text:
            return None
        markers = _find_markers(payload.prior_input_text)
        if not markers:
            return None
        anchors = _find_runs(
            payload.prior_input_text,
            payload.response_text,
            ANCHOR_MIN_RUN_TOKENS,
        )
        if not anchors:
            return HardBlockResult(
                reason=(
                    f"{len(markers)} high-stakes marker(s) in input, response has "
                    f"zero input-anchor citations (no ≥{ANCHOR_MIN_RUN_TOKENS}-token "
                    "consecutive runs from input present in response). Wallpaper-shape."
                ),
                recovery_path=(
                    "Anchor the response in input substance: quote or echo a "
                    "≥3-token span from the high-stakes part of the input. "
                    "Generic engagement language without anchor is the failure-shape "
                    "this binding catches."
                ),
            )
        return None

    def validate(self, payload: BindingPayload) -> ValidationResult:
        if not payload.prior_input_text or not payload.response_text:
            return ValidationResult(allow=True, reason="empty payload — defensive allow")
        markers = _find_markers(payload.prior_input_text)
        if not markers:
            return ValidationResult(allow=True, reason="no markers")
        anchors = _find_runs(
            payload.prior_input_text,
            payload.response_text,
            ANCHOR_MIN_RUN_TOKENS,
        )
        quoted = _find_quoted_spans(payload.response_text)
        for q in quoted:
            pat = re.compile(rf"\b{re.escape(q.text)}\b", re.IGNORECASE)
            if not pat.search(payload.prior_input_text):
                return ValidationResult(
                    allow=False,
                    reason=(
                        f"quoted span {q.text!r} not present in prior_input_text "
                        "(decorative cite — any-decorative-fails policy)."
                    ),
                    recovery_path=(
                        "Remove fabricated quote OR replace with a real span from "
                        "the input (word-boundary-matched)."
                    ),
                )
        clusters = _cluster_markers(markers)
        for cl in clusters:
            if not any(_anchor_covers_cluster(a, cl) for a in anchors):
                return ValidationResult(
                    allow=False,
                    reason=(
                        f"cluster at tokens [{cl.span_start},{cl.span_end}] "
                        f"({len(cl.markers)} marker(s)) has no covering anchor — "
                        "incomplete coverage."
                    ),
                    recovery_path=(
                        "Anchor each distinct high-stakes cluster. If two markers "
                        "should be treated as one, they need to be close enough to "
                        "collapse (PROXIMITY_COLLAPSE_TOKENS / MAX_CLUSTER_SPAN_TOKENS)."
                    ),
                )
        # Group anchors by input-span connectivity (overlap + tight adjacency).
        # Within a group: require AT LEAST ONE anchor to pass bare-echo (engagement-density,
        # not gaming). Across groups: each group must have a passing anchor (preserves
        # F7 strict-symmetry for distinct input-region citations).
        for group in _group_anchors_by_input_span(anchors):
            group_passes = False
            last_reason = ""
            last_match = group[0].matched_text
            for a in group:
                passes, reason = _check_bare_echo(
                    a,
                    payload.prior_input_text,
                    payload.response_text,
                )
                if passes:
                    group_passes = True
                    break
                last_reason = reason
                last_match = a.matched_text
            if not group_passes:
                return ValidationResult(
                    allow=False,
                    reason=f"input-span-group containing anchor {last_match!r} "
                    f"has no passing bare-echo: {last_reason}",
                    recovery_path=(
                        "After at least one citation in this input-region, add "
                        "genuine engagement: reframe-language + ≥3 novel content-words "
                        "+ lexical thread to input outside cite."
                    ),
                )
        return ValidationResult(
            allow=True,
            reason=(
                f"{len(markers)} marker(s), {len(clusters)} cluster(s), "
                f"{len(anchors)} anchor(s) — engagement verified"
            ),
        )
