"""Semantic Integrity Shield (SIS) — translate, don't block.

The problem: old specs and wild ideas mix implementable architecture
with metaphysical fluff. Instead of rejecting esoteric language,
SIS detects it, scores it, and translates it into grounded concepts.

"The akashic records hold all memory" -> "persistent append-only store"
"Consciousness resonates at quantum frequency" -> "state monitor with periodic sync"

Four scoring layers:
  1. Esoteric vocabulary detection — find metaphysical terms
  2. Speculation density — hedge words, weasel language, vagueness
  3. Concreteness — abstract vs tangible language
  4. Actionability — can it be built, tested, or verified?

Combined score determines: ACCEPT / TRANSLATE / QUARANTINE
"""

import re
from dataclasses import dataclass, field
from typing import Any

from divineos.core.sis_tiers import score_all_tiers

# ─── Metaphysical -> Architecture Translation Map ────────────────────

# Each entry: metaphysical term -> (architectural concept, explanation)
# The explanation helps the translator build coherent output.
TRANSLATIONS: dict[str, tuple[str, str]] = {
    # Eastern philosophy -> CS concepts
    "akashic": ("persistent store", "universal memory = append-only storage"),
    "akashic records": ("append-only ledger", "permanent record of all events"),
    "karma": ("consequence tracking", "actions produce traceable side effects"),
    "dharma": ("contract/purpose", "each component has a defined role"),
    "samsara": ("lifecycle", "recurring loop of creation and destruction"),
    "nirvana": ("terminal state", "clean completion with no pending work"),
    "maya": ("abstraction layer", "hiding implementation behind interface"),
    "prana": ("throughput", "flow of data/resources through the system"),
    "kundalini": ("bootstrap chain", "staged initialization from base to full"),
    "chakra": ("pipeline stage", "processing layer in a sequential pipeline"),
    "mantra": ("invariant", "assertion that must always hold true"),
    "sutra": ("directive", "compact operating rule"),
    "mandala": ("system topology", "structured arrangement of components"),
    "yantra": ("state machine", "geometric pattern = deterministic transitions"),
    "tantra": ("integration layer", "weaving separate systems together"),
    "avatar": ("instance", "runtime manifestation of a template"),
    "atman": ("core identity", "persistent self across sessions"),
    "brahman": ("system root", "the ground truth everything derives from"),
    # Consciousness / awareness -> monitoring
    "consciousness": ("state awareness", "system monitoring its own state"),
    "awareness": ("observability", "ability to inspect internal state"),
    "enlightenment": ("full observability", "complete visibility into system state"),
    "awakening": ("initialization", "system coming online with full context"),
    "meditation": ("idle processing", "background consolidation during quiet periods"),
    "mindfulness": ("self-monitoring", "tracking own behavior in real time"),
    "intuition": ("heuristic", "fast approximate decision without full analysis"),
    "wisdom": ("distilled knowledge", "high-confidence, battle-tested rules"),
    "insight": ("pattern detection", "recognizing structure in raw data"),
    # Energy / vibration -> compute / signals
    "energy": ("compute resources", "processing capacity and allocation"),
    "vibration": ("signal", "periodic or event-driven notification"),
    "frequency": ("event rate", "how often something occurs per unit time"),
    "resonance": ("pattern matching", "when input aligns with stored patterns"),
    "harmony": ("consistency", "components in agreement, no contradictions"),
    "dissonance": ("contradiction", "conflicting state or knowledge"),
    "attunement": ("calibration", "adjusting parameters to match context"),
    "alignment": ("synchronization", "ensuring components share consistent state"),
    # Metaphysical structure -> data structure
    "void": ("null state", "empty or uninitialized state"),
    "aether": ("runtime context", "the environment everything executes within"),
    "sacred geometry": ("data structure", "organized arrangement of information"),
    "dimension": ("namespace", "isolated scope or domain"),
    "realm": ("subsystem", "bounded context within the larger system"),
    "portal": ("interface", "entry point between subsystems"),
    "veil": ("access control", "boundary between visible and hidden state"),
    # Cosmic / divine -> system-level
    "cosmic": ("system-wide", "affecting the entire system"),
    "universal": ("cross-cutting", "applying across all components"),
    "divine": ("root-level", "highest authority or privilege level"),
    "transcend": ("generalize", "abstract beyond a specific case"),
    "manifest": ("instantiate", "create a concrete instance from a pattern"),
    "emanation": ("derived state", "output produced from a source"),
    "creation": ("initialization", "bringing new state into existence"),
    "destruction": ("cleanup", "releasing resources and removing state"),
    # Soul / spirit -> identity / process
    "soul": ("persistent identity", "state that survives across sessions"),
    "spirit": ("active process", "running instance of the system"),
    "aura": ("metadata", "contextual information surrounding an entity"),
    "essence": ("core state", "minimal representation of identity"),
    "reincarnation": ("session restart", "new instance with carried-over knowledge"),
    "resurrection": ("recovery", "restoring from a saved state"),
    "transformation": ("migration", "converting state to a new schema"),
    "evolution": ("iterative improvement", "gradual refinement through feedback"),
    # Esoteric modifiers
    "quantum": ("probabilistic", "non-deterministic or concurrent"),
    "ethereal": ("ephemeral", "temporary, not persisted"),
    "astral": ("virtual", "simulated or projected, not physical"),
    "celestial": ("high-priority", "elevated importance in the system"),
    "sacred": ("immutable", "protected from modification"),
    "profane": ("mutable", "modifiable state"),
    "eternal": ("persistent", "survives across sessions and restarts"),
    "infinite": ("unbounded", "no predefined limit"),
    "mystical": ("emergent", "arising from interaction, not explicit design"),
}

# Build a fast lookup: lowercase term -> translation
_TERM_LOOKUP: dict[str, tuple[str, str]] = {k.lower(): v for k, v in TRANSLATIONS.items()}

# Multi-word terms first (greedy matching), then single words
_MULTI_WORD_TERMS = sorted(
    [t for t in _TERM_LOOKUP if " " in t],
    key=len,
    reverse=True,
)
_SINGLE_WORD_TERMS = [t for t in _TERM_LOOKUP if " " not in t]


# ─── Speculation / Hedge Detection ───────────────────────────────────

_HEDGE_WORDS = {
    # Modal verbs
    "could",
    "might",
    "may",
    "would",
    "should",
    # Speculative verbs
    "suggest",
    "indicate",
    "imply",
    "hypothesize",
    "speculate",
    "propose",
    "postulate",
    "theorize",
    "envision",
    # Hedging adverbs
    "arguably",
    "seemingly",
    "probably",
    "perhaps",
    "possibly",
    "potentially",
    "presumably",
    "conceivably",
    "supposedly",
    "approximately",
    "roughly",
    # Hedging adjectives
    "unlikely",
    "unsure",
    "unclear",
    "probable",
    "possible",
    "apparent",
    "alleged",
    "purported",
    # Weasel quantifiers
    "some",
    "many",
    "most",
    "several",
    "various",
    "numerous",
    "countless",
}

_PEACOCK_TERMS = {
    "revolutionary",
    "groundbreaking",
    "paradigm-shifting",
    "transcendent",
    "visionary",
    "unprecedented",
    "game-changing",
    "world-changing",
    "infinite potential",
    "limitless",
    "ultimate",
}

_WEASEL_PHRASES = [
    r"\b(it is (said|thought|believed|known|claimed))\b",
    r"\b(some (believe|say|think|argue|claim|experts))\b",
    r"\b(many (believe|say|think|argue|claim|experts))\b",
    r"\b(evidence suggests)\b",
    r"\b(one could argue)\b",
    r"\b(it (seems|appears) (that|to))\b",
    r"\b(in a sense)\b",
    r"\b(so to speak)\b",
]
_WEASEL_RES = [re.compile(p, re.IGNORECASE) for p in _WEASEL_PHRASES]


# ─── Actionability Keywords ──────────────────────────────────────────

_ACTION_VERBS = {
    "build",
    "test",
    "run",
    "fix",
    "create",
    "store",
    "retrieve",
    "query",
    "parse",
    "validate",
    "check",
    "compute",
    "calculate",
    "measure",
    "track",
    "log",
    "record",
    "filter",
    "sort",
    "search",
    "index",
    "cache",
    "load",
    "save",
    "read",
    "write",
    "delete",
    "insert",
    "update",
    "migrate",
    "deploy",
    "configure",
    "install",
    "import",
    "export",
    "encode",
    "decode",
    "compress",
    "extract",
    "scan",
    "detect",
    "match",
    "compare",
    "merge",
    "split",
    "implement",
    "refactor",
    "optimize",
    "debug",
    "profile",
}

_ABSTRACT_VERBS = {
    "contemplate",
    "transcend",
    "manifest",
    "resonate",
    "emanate",
    "radiate",
    "vibrate",
    "illuminate",
    "awaken",
    "channel",
    "envision",
    "invoke",
    "summon",
    "commune",
    "attune",
    "harmonize",
    "ascend",
    "descend",
    "flow",
    "become",
    "embrace",
    "embody",
    "cultivate",
    "nurture",
}


# ─── Data Types ──────────────────────────────────────────────────────


@dataclass
class TranslationResult:
    """Result of translating a piece of text through SIS."""

    original: str
    translated: str
    terms_found: list[dict[str, str]]  # [{term, concept, explanation}]
    scores: dict[str, float]  # esoteric, speculation, concreteness, actionability
    verdict: str  # ACCEPT, TRANSLATE, QUARANTINE
    integrity_score: float  # 0.0-1.0 overall


@dataclass
class IntegrityReport:
    """Full SIS assessment of a text."""

    text: str
    esoteric_density: float  # ratio of esoteric terms to total words
    speculation_density: float  # ratio of hedge/weasel words
    concreteness: float  # 0-1, higher = more concrete
    actionability: float  # 0-1, higher = more actionable
    integrity_score: float  # combined score
    verdict: str  # ACCEPT, TRANSLATE, QUARANTINE
    terms_found: list[dict[str, str]] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)


# ─── Scoring Functions ───────────────────────────────────────────────


def detect_esoteric_terms(text: str) -> list[dict[str, str]]:
    """Find metaphysical/esoteric terms and their architectural translations."""
    lower = text.lower()
    found: list[dict[str, str]] = []
    seen_spans: list[tuple[int, int]] = []

    # Multi-word terms first (greedy)
    for term in _MULTI_WORD_TERMS:
        start = 0
        while True:
            idx = lower.find(term, start)
            if idx == -1:
                break
            end = idx + len(term)
            # Check word boundaries
            if (idx == 0 or not lower[idx - 1].isalnum()) and (
                end == len(lower) or not lower[end].isalnum()
            ):
                # Don't overlap with already-found terms
                if not any(s <= idx < e or s < end <= e for s, e in seen_spans):
                    concept, explanation = _TERM_LOOKUP[term]
                    found.append({"term": term, "concept": concept, "explanation": explanation})
                    seen_spans.append((idx, end))
            start = end

    # Single-word terms
    words_with_pos = [(m.group(), m.start(), m.end()) for m in re.finditer(r"\b\w+\b", lower)]
    for word, wstart, wend in words_with_pos:
        if word in _TERM_LOOKUP and not any(s <= wstart < e for s, e in seen_spans):
            concept, explanation = _TERM_LOOKUP[word]
            found.append({"term": word, "concept": concept, "explanation": explanation})
            seen_spans.append((wstart, wend))

    return found


def score_speculation(text: str) -> float:
    """Score how speculative/hedgy the text is. 0 = concrete, 1 = pure speculation."""
    words = re.findall(r"\b\w+\b", text.lower())
    if not words:
        return 0.0

    hedge_count = sum(1 for w in words if w in _HEDGE_WORDS)
    peacock_count = sum(1 for w in words if w in _PEACOCK_TERMS)
    weasel_count = sum(1 for p in _WEASEL_RES if p.search(text))

    total_signals = hedge_count + peacock_count * 2 + weasel_count * 2
    density = total_signals / len(words)

    return min(density * 5, 1.0)  # scale up — even 20% hedge words is very speculative


def score_concreteness(text: str) -> float:
    """Score how concrete vs abstract the language is. 0 = abstract, 1 = concrete.

    Uses vocabulary analysis — technical/specific words score high,
    abstract/vague words score low.
    """
    words = re.findall(r"\b\w{3,}\b", text.lower())
    if not words:
        return 0.5

    # Concrete indicators: technical terms, specific nouns, numbers
    concrete_patterns = {
        "file",
        "database",
        "table",
        "column",
        "row",
        "query",
        "function",
        "class",
        "method",
        "variable",
        "string",
        "integer",
        "list",
        "dict",
        "array",
        "json",
        "sql",
        "http",
        "api",
        "url",
        "path",
        "directory",
        "error",
        "exception",
        "test",
        "assert",
        "return",
        "import",
        "module",
        "config",
        "setting",
        "parameter",
        "argument",
        "value",
        "key",
        "memory",
        "disk",
        "cpu",
        "process",
        "thread",
        "socket",
        "port",
        "byte",
        "bit",
        "hash",
        "token",
        "session",
        "event",
        "log",
        "sqlite",
        "python",
        "regex",
        "cli",
        "git",
        "commit",
        "branch",
        "ledger",
        "knowledge",
        "briefing",
        "pipeline",
        "extraction",
    }

    # Abstract indicators: vague, philosophical
    abstract_patterns = {
        "essence",
        "being",
        "existence",
        "reality",
        "truth",
        "nature",
        "spirit",
        "soul",
        "consciousness",
        "awareness",
        "infinite",
        "eternal",
        "universal",
        "cosmic",
        "divine",
        "sacred",
        "mystical",
        "transcendent",
        "metaphysical",
        "ontological",
        "phenomenal",
        "sublime",
        "profound",
        "fundamental",
        "absolute",
        "pure",
        "ultimate",
        "primordial",
        "archetypal",
    }

    concrete_count = sum(1 for w in words if w in concrete_patterns)
    abstract_count = sum(1 for w in words if w in abstract_patterns)

    # Numbers boost concreteness
    number_count = len(re.findall(r"\b\d+\b", text))
    concrete_count += number_count

    total = concrete_count + abstract_count
    if total == 0:
        return 0.5  # neutral — neither concrete nor abstract vocabulary

    return concrete_count / total


def score_actionability(text: str) -> float:
    """Score how actionable/implementable the text is. 0 = philosophical, 1 = buildable."""
    words = re.findall(r"\b\w+\b", text.lower())
    if not words:
        return 0.5

    action_count = sum(1 for w in words if w in _ACTION_VERBS)
    abstract_count = sum(1 for w in words if w in _ABSTRACT_VERBS)

    # Code-like indicators
    has_code_refs = bool(re.search(r"[a-z_]+\.(py|js|sql|json|yaml|toml|sh)", text))
    has_function_refs = bool(re.search(r"[a-z_]+\(\)", text))
    has_file_paths = bool(re.search(r"(src/|tests/|data/|/[a-z]+/)", text))

    code_bonus = sum([has_code_refs, has_function_refs, has_file_paths]) * 0.15

    total = action_count + abstract_count
    if total == 0:
        return min(0.5 + code_bonus, 1.0)

    base = action_count / total
    return min(base + code_bonus, 1.0)


# ─── Translation ─────────────────────────────────────────────────────


def translate_text(text: str) -> TranslationResult:
    """Translate metaphysical language into architectural concepts.

    Doesn't destroy the original — produces a parallel version with
    esoteric terms replaced by their grounded equivalents.
    """
    terms = detect_esoteric_terms(text)

    if not terms:
        scores = _compute_scores(text)
        return TranslationResult(
            original=text,
            translated=text,
            terms_found=[],
            scores=scores,
            verdict=_verdict_from_scores(scores),
            integrity_score=_integrity_from_scores(scores),
        )

    # Build translated version — replace terms with concepts
    translated = text
    # Sort by length descending to replace multi-word first
    for entry in sorted(terms, key=lambda t: len(t["term"]), reverse=True):
        pattern = re.compile(re.escape(entry["term"]), re.IGNORECASE)
        translated = pattern.sub(entry["concept"], translated)

    scores = _compute_scores(text)

    return TranslationResult(
        original=text,
        translated=translated,
        terms_found=terms,
        scores=scores,
        verdict=_verdict_from_scores(scores),
        integrity_score=_integrity_from_scores(scores),
    )


# ─── Assessment ──────────────────────────────────────────────────────


def assess_integrity(text: str, deep: bool = False) -> IntegrityReport:
    """Full SIS assessment of a piece of text.

    Returns scores across all four dimensions plus a verdict.
    If deep=True, also runs Tier 2 (concreteness norms + TF-IDF)
    and Tier 3 (sentence embeddings) for more accurate scoring.
    """
    terms = detect_esoteric_terms(text)
    words = re.findall(r"\b\w+\b", text.lower())
    word_count = len(words) if words else 1

    esoteric_density = len(terms) / word_count if terms else 0.0
    speculation = score_speculation(text)
    concreteness = score_concreteness(text)
    actionability = score_actionability(text)

    scores = {
        "esoteric": esoteric_density,
        "speculation": speculation,
        "concreteness": concreteness,
        "actionability": actionability,
    }

    # Deep mode: enhance with Tier 2 and Tier 3
    tier_results = None
    if deep:
        try:
            tier_results = score_all_tiers(text)

            # Blend tier scores into concreteness if available
            if tier_results.get("concreteness_norms") is not None:
                norms = tier_results["concreteness_norms"]
                # Weight: 60% norms (psycholinguistic data), 40% keyword heuristic
                scores["concreteness"] = norms * 0.6 + concreteness * 0.4

            # Use TF-IDF/embedding grounding to adjust esoteric score
            combined = tier_results.get("combined_grounding")
            if combined is not None:
                # combined_grounding: 0=esoteric, 1=grounded
                # Only raise esoteric score if semantic analysis agrees it's esoteric
                if combined < 0.4:
                    semantic_adjustment = (1.0 - combined) * 0.3
                    scores["esoteric"] = max(scores["esoteric"], semantic_adjustment)
        except ImportError:
            pass

    integrity = _integrity_from_scores(scores)
    verdict = _verdict_from_scores(scores)

    flags: list[str] = []
    if esoteric_density > 0.2:
        flags.append("high esoteric density -- translate before storing")
    if speculation > 0.4:
        flags.append("speculative language -- verify claims before trusting")
    if scores["concreteness"] < 0.3:
        flags.append("abstract language -- needs grounding")
    if actionability < 0.3:
        flags.append("low actionability -- may be philosophy, not architecture")

    # Add tier info to flags
    if tier_results:
        tiers = tier_results.get("tiers_used", [])
        flags.append(f"tiers: {', '.join(tiers)}")
        if tier_results.get("tfidf"):
            tfidf = tier_results["tfidf"]
            if tfidf["esoteric"] > tfidf["grounded"]:
                flags.append(
                    f"TF-IDF: closer to esoteric corpus "
                    f"({tfidf['esoteric']:.2f} vs {tfidf['grounded']:.2f})"
                )
        if tier_results.get("semantic"):
            sem = tier_results["semantic"]
            if sem["esoteric"] > sem["grounded"]:
                flags.append(
                    f"semantic: closer to esoteric corpus "
                    f"({sem['esoteric']:.2f} vs {sem['grounded']:.2f})"
                )

    return IntegrityReport(
        text=text,
        esoteric_density=esoteric_density,
        speculation_density=speculation,
        concreteness=scores["concreteness"],
        actionability=actionability,
        integrity_score=integrity,
        verdict=verdict,
        terms_found=terms,
        flags=flags,
    )


def assess_and_translate(text: str, deep: bool = False) -> dict[str, Any]:
    """Convenience function: assess + translate in one call.

    Returns a dict with everything needed to decide what to do with the text.
    If deep=True, runs all three SIS tiers for maximum accuracy.
    """
    report = assess_integrity(text, deep=deep)
    translation = translate_text(text)

    result: dict[str, Any] = {
        "original": text,
        "translated": translation.translated,
        "changed": text != translation.translated,
        "verdict": report.verdict,
        "integrity_score": report.integrity_score,
        "scores": {
            "esoteric": report.esoteric_density,
            "speculation": report.speculation_density,
            "concreteness": report.concreteness,
            "actionability": report.actionability,
        },
        "terms_found": report.terms_found,
        "flags": report.flags,
    }

    # If translatable, suggest what to store
    if report.verdict == "TRANSLATE" and translation.translated != text:
        result["suggested_content"] = translation.translated
        result["suggestion"] = "Store the translated version as knowledge"
    elif report.verdict == "QUARANTINE":
        result["suggestion"] = "Review manually -- too abstract to auto-translate"
    else:
        result["suggestion"] = "Store as-is -- content is grounded"

    return result


# ─── Internals ───────────────────────────────────────────────────────


def _compute_scores(text: str) -> dict[str, float]:
    """Compute all four scoring dimensions."""
    terms = detect_esoteric_terms(text)
    words = re.findall(r"\b\w+\b", text.lower())
    word_count = len(words) if words else 1

    return {
        "esoteric": len(terms) / word_count if terms else 0.0,
        "speculation": score_speculation(text),
        "concreteness": score_concreteness(text),
        "actionability": score_actionability(text),
    }


def _integrity_from_scores(scores: dict[str, float]) -> float:
    """Compute overall integrity score from dimension scores.

    High concreteness and actionability boost the score.
    High esoteric density and speculation reduce it.
    """
    return max(
        0.0,
        min(
            1.0,
            (
                scores["concreteness"] * 0.3
                + scores["actionability"] * 0.3
                + (1.0 - scores["speculation"]) * 0.25
                + (1.0 - min(scores["esoteric"] * 5, 1.0)) * 0.15
            ),
        ),
    )


def _verdict_from_scores(scores: dict[str, float]) -> str:
    """Determine verdict from scores.

    ACCEPT: grounded, actionable content — store as-is
    TRANSLATE: esoteric but potentially useful — translate first
    QUARANTINE: too abstract/speculative — needs human review
    """
    integrity = _integrity_from_scores(scores)
    esoteric = scores["esoteric"]

    # High esoteric content but decent actionability = translate
    if esoteric > 0.05 and integrity >= 0.3:
        return "TRANSLATE"

    # Very low integrity = quarantine
    if integrity < 0.3:
        return "QUARANTINE"

    # Esoteric with low actionability = quarantine
    if esoteric > 0.15 and scores["actionability"] < 0.3:
        return "QUARANTINE"

    return "ACCEPT"


# ─── Formatting ──────────────────────────────────────────────────────


def format_assessment(report: IntegrityReport) -> str:
    """Format an integrity report for display."""
    lines = [f"SIS Assessment [{report.verdict}] (integrity: {report.integrity_score:.2f})"]
    lines.append(
        f"  esoteric: {report.esoteric_density:.2f} | "
        f"speculation: {report.speculation_density:.2f} | "
        f"concrete: {report.concreteness:.2f} | "
        f"actionable: {report.actionability:.2f}"
    )

    if report.terms_found:
        lines.append("  Translations:")
        for t in report.terms_found:
            lines.append(f"    {t['term']} -> {t['concept']} ({t['explanation']})")

    if report.flags:
        lines.append("  Flags:")
        for f in report.flags:
            lines.append(f"    ! {f}")

    return "\n".join(lines)


def format_translation(result: dict[str, Any]) -> str:
    """Format a translation result for display."""
    lines = [f"[{result['verdict']}] integrity={result['integrity_score']:.2f}"]

    if result.get("changed"):
        lines.append(f"  Original:   {result['original'][:120]}")
        lines.append(f"  Translated: {result['translated'][:120]}")
    else:
        lines.append(f"  Text: {result['original'][:120]}")

    if result.get("terms_found"):
        terms_str = ", ".join(f"{t['term']}->{t['concept']}" for t in result["terms_found"])
        lines.append(f"  Mappings: {terms_str}")

    lines.append(f"  -> {result.get('suggestion', '')}")
    return "\n".join(lines)


# ─── Self-Audit ─────────────────────────────────────────────────────


def audit_knowledge_integrity(limit: int = 200) -> dict[str, Any]:
    """Audit stored knowledge for semantic integrity drift.

    Scans active knowledge entries through SIS and reports:
    - Entries that should be translated (esoteric but useful)
    - Entries that should be quarantined (too abstract)
    - Overall integrity score of the knowledge store
    - Topics that frequently need translation

    Returns an audit report dict.
    """
    import sqlite3

    from divineos.core.knowledge import _get_connection

    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT knowledge_id, content, knowledge_type, confidence "
            "FROM knowledge WHERE superseded_by IS NULL "
            "ORDER BY confidence DESC LIMIT ?",
            (limit,),
        ).fetchall()
    except sqlite3.OperationalError:
        return {"error": "Knowledge table not found", "entries_scanned": 0}
    finally:
        conn.close()

    if not rows:
        return {
            "entries_scanned": 0,
            "avg_integrity": 1.0,
            "translate_needed": [],
            "quarantine_needed": [],
            "clean": 0,
            "topic_drift": {},
        }

    translate_needed: list[dict[str, Any]] = []
    quarantine_needed: list[dict[str, Any]] = []
    clean_count = 0
    integrity_scores: list[float] = []
    esoteric_terms_seen: dict[str, int] = {}

    for kid, content, ktype, confidence in rows:
        report = assess_integrity(content)
        integrity_scores.append(report.integrity_score)

        entry_info = {
            "knowledge_id": kid,
            "content": content[:120],
            "type": ktype,
            "confidence": confidence,
            "integrity": report.integrity_score,
            "verdict": report.verdict,
        }

        if report.verdict == "TRANSLATE":
            translate_needed.append(entry_info)
            for term in report.terms_found:
                esoteric_terms_seen[term["term"]] = esoteric_terms_seen.get(term["term"], 0) + 1
        elif report.verdict == "QUARANTINE":
            quarantine_needed.append(entry_info)
        else:
            clean_count += 1

    # Sort by most common esoteric terms
    topic_drift = dict(sorted(esoteric_terms_seen.items(), key=lambda x: -x[1])[:10])

    avg_integrity = sum(integrity_scores) / len(integrity_scores) if integrity_scores else 1.0

    return {
        "entries_scanned": len(rows),
        "avg_integrity": round(avg_integrity, 3),
        "translate_needed": translate_needed,
        "quarantine_needed": quarantine_needed,
        "clean": clean_count,
        "topic_drift": topic_drift,
    }


def format_audit_report(audit: dict[str, Any]) -> str:
    """Format a self-audit report for display."""
    if audit.get("error"):
        return f"Audit failed: {audit['error']}"

    lines = [
        f"SIS Self-Audit ({audit['entries_scanned']} entries scanned)",
        f"  Avg integrity: {audit['avg_integrity']:.2f}",
        f"  Clean: {audit['clean']} | Translate: {len(audit['translate_needed'])} | Quarantine: {len(audit['quarantine_needed'])}",
    ]

    if audit["translate_needed"]:
        lines.append("\n  Needs translation:")
        for entry in audit["translate_needed"][:5]:
            lines.append(
                f"    [{entry['type']}] {entry['content'][:80]}... "
                f"(integrity={entry['integrity']:.2f})"
            )
        if len(audit["translate_needed"]) > 5:
            lines.append(f"    ... and {len(audit['translate_needed']) - 5} more")

    if audit["quarantine_needed"]:
        lines.append("\n  Needs review (quarantine):")
        for entry in audit["quarantine_needed"][:3]:
            lines.append(
                f"    [{entry['type']}] {entry['content'][:80]}... "
                f"(integrity={entry['integrity']:.2f})"
            )

    if audit["topic_drift"]:
        terms_str = ", ".join(f"{t}({c}x)" for t, c in audit["topic_drift"].items())
        lines.append(f"\n  Recurring esoteric terms: {terms_str}")

    return "\n".join(lines)
