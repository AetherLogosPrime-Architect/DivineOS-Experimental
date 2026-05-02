"""SIS Tier 2 and Tier 3 — statistical and semantic scoring layers.

Tier 2: Concreteness norms (word-level groundedness) + TF-IDF similarity
Tier 3: Sentence embeddings for semantic understanding

Each tier gracefully degrades — if dependencies aren't available,
the tier returns None and SIS falls back to the layers below it.
"""

from __future__ import annotations

import re
from typing import Any

from loguru import logger

# ML libraries (sklearn, sentence-transformers) can throw RuntimeError,
# ValueError, or numpy errors. This tuple covers the realistic set.
_SIS_ML_ERRORS = (ImportError, RuntimeError, ValueError, TypeError, OSError)


# ─── Tier 2: Concreteness Norms ──────────────────────────────────────
#
# Based on Brysbaert et al. (2014) concreteness ratings methodology.
# Each word scored 1.0 (very abstract) to 5.0 (very concrete).
# We bundle a curated subset of ~600 words covering technical,
# philosophical, and common vocabulary.


# Scored 1.0-5.0: 1=abstract, 5=concrete
_CONCRETENESS_NORMS: dict[str, float] = {
    # 5.0 — Very concrete (physical objects, specific tech)
    "keyboard": 5.0,
    "screen": 5.0,
    "mouse": 4.9,
    "cable": 4.9,
    "disk": 4.8,
    "chip": 4.8,
    "server": 4.7,
    "printer": 4.9,
    "button": 4.9,
    "switch": 4.8,
    "wire": 4.9,
    "plug": 4.9,
    "laptop": 5.0,
    "phone": 5.0,
    "camera": 5.0,
    "speaker": 4.9,
    # 4.0-4.9 — Concrete (tangible tech concepts)
    "file": 4.5,
    "folder": 4.5,
    "database": 4.3,
    "table": 4.7,
    "column": 4.5,
    "row": 4.5,
    "icon": 4.3,
    "pixel": 4.2,
    "byte": 4.0,
    "packet": 4.2,
    "buffer": 4.0,
    "stack": 4.3,
    "queue": 4.1,
    "array": 4.0,
    "list": 4.2,
    "string": 4.0,
    "integer": 4.0,
    "boolean": 3.8,
    "float": 3.8,
    "hash": 3.9,
    "token": 4.0,
    "key": 4.5,
    "lock": 4.7,
    "log": 4.0,
    "error": 3.8,
    "crash": 4.2,
    "bug": 4.0,
    "test": 3.8,
    "code": 3.7,
    "script": 3.8,
    "program": 3.7,
    "output": 3.8,
    "input": 3.8,
    "display": 4.0,
    "window": 4.7,
    "cursor": 4.3,
    "scroll": 4.0,
    "click": 4.2,
    "drag": 4.0,
    "timer": 4.2,
    "clock": 4.8,
    "counter": 4.0,
    "meter": 4.5,
    "chart": 4.3,
    "graph": 4.0,
    "map": 4.2,
    "diagram": 4.0,
    "tree": 4.8,
    "node": 3.9,
    "edge": 4.0,
    "path": 4.2,
    "branch": 4.5,
    "root": 4.5,
    "leaf": 4.8,
    "seed": 4.7,
    "port": 4.2,
    "socket": 4.3,
    "pipe": 4.5,
    "stream": 4.2,
    "block": 4.3,
    "chunk": 4.0,
    "slice": 4.2,
    "segment": 3.9,
    # 3.0-3.9 — Moderately concrete (technical abstractions)
    "function": 3.5,
    "method": 3.3,
    "class": 3.4,
    "object": 3.8,
    "module": 3.4,
    "package": 4.0,
    "library": 4.2,
    "framework": 3.2,
    "interface": 3.3,
    "protocol": 3.2,
    "format": 3.3,
    "schema": 3.2,
    "query": 3.5,
    "request": 3.3,
    "response": 3.3,
    "message": 3.5,
    "event": 3.4,
    "signal": 3.5,
    "trigger": 3.5,
    "callback": 3.2,
    "process": 3.3,
    "thread": 3.5,
    "task": 3.2,
    "job": 3.3,
    "session": 3.2,
    "connection": 3.3,
    "channel": 3.5,
    "link": 3.5,
    "record": 3.5,
    "entry": 3.4,
    "item": 3.5,
    "element": 3.4,
    "layer": 3.3,
    "level": 3.3,
    "stage": 3.5,
    "phase": 3.2,
    "filter": 3.5,
    "parser": 3.2,
    "scanner": 3.5,
    "loader": 3.2,
    "handler": 3.1,
    "wrapper": 3.3,
    "adapter": 3.3,
    "bridge": 4.2,
    "cache": 3.3,
    "index": 3.4,
    "registry": 3.3,
    "catalog": 3.5,
    "pipeline": 3.2,
    "workflow": 3.1,
    "sequence": 3.2,
    "chain": 3.8,
    "config": 3.2,
    "setting": 3.3,
    "option": 3.1,
    "flag": 3.8,
    "rule": 3.2,
    "policy": 3.0,
    "constraint": 3.0,
    "limit": 3.2,
    "version": 3.2,
    "release": 3.2,
    "update": 3.1,
    "patch": 3.5,
    "commit": 3.3,
    "merge": 3.2,
    "diff": 3.1,
    "changelog": 3.2,
    "migration": 3.1,
    "deployment": 3.1,
    "rollback": 3.1,
    "variable": 3.2,
    "parameter": 3.1,
    "argument": 3.1,
    "value": 3.3,
    "type": 3.1,
    "instance": 3.1,
    "reference": 3.2,
    "pointer": 3.5,
    "scope": 3.0,
    "context": 3.0,
    "environment": 3.3,
    "namespace": 3.0,
    "memory": 3.5,
    "storage": 3.5,
    "capacity": 3.2,
    "bandwidth": 3.1,
    "latency": 3.0,
    "throughput": 3.0,
    "performance": 3.0,
    "algorithm": 3.0,
    "heuristic": 2.8,
    "strategy": 2.9,
    "pattern": 3.2,
    "model": 3.3,
    "template": 3.4,
    "blueprint": 3.8,
    "prototype": 3.5,
    "data": 3.2,
    "information": 3.0,
    "knowledge": 3.0,
    "metadata": 2.9,
    "network": 3.5,
    "cluster": 3.5,
    "grid": 3.8,
    "mesh": 3.7,
    # 2.0-2.9 — Abstract (concepts, mental constructs)
    "state": 2.8,
    "status": 2.9,
    "condition": 2.7,
    "mode": 2.8,
    "logic": 2.5,
    "reason": 2.5,
    "judgment": 2.4,
    "decision": 2.6,
    "behavior": 2.5,
    "action": 2.7,
    "operation": 2.7,
    "execution": 2.6,
    "permission": 2.6,
    "access": 2.7,
    "control": 2.7,
    "authority": 2.4,
    "identity": 2.5,
    "role": 2.6,
    "responsibility": 2.3,
    "ownership": 2.4,
    "concept": 2.2,
    "idea": 2.3,
    "theory": 2.2,
    "hypothesis": 2.3,
    "principle": 2.3,
    "guideline": 2.5,
    "standard": 2.5,
    "quality": 2.5,
    "integrity": 2.3,
    "reliability": 2.3,
    "stability": 2.4,
    "complexity": 2.2,
    "simplicity": 2.2,
    "elegance": 2.1,
    "beauty": 2.3,
    "purpose": 2.2,
    "goal": 2.4,
    "objective": 2.3,
    "target": 3.2,
    "meaning": 2.0,
    "significance": 2.0,
    "importance": 2.2,
    "relevance": 2.1,
    "relationship": 2.3,
    "dependency": 2.5,
    "coupling": 2.7,
    "abstraction": 1.9,
    "generalization": 1.9,
    "specialization": 2.1,
    "encapsulation": 2.0,
    "inheritance": 2.3,
    "composition": 2.4,
    "architecture": 2.8,
    "design": 2.7,
    "structure": 2.8,
    "organization": 2.5,
    "system": 2.7,
    "platform": 3.0,
    "infrastructure": 2.8,
    "foundation": 3.2,
    "evolution": 2.3,
    "growth": 2.5,
    "progress": 2.3,
    "improvement": 2.4,
    "change": 2.5,
    "transformation": 2.2,
    "transition": 2.3,
    "shift": 2.6,
    "awareness": 2.0,
    "understanding": 2.1,
    "comprehension": 2.0,
    "experience": 2.3,
    "perception": 2.0,
    "observation": 2.4,
    "insight": 2.1,
    "learning": 2.3,
    "teaching": 2.5,
    "training": 2.7,
    "practice": 2.5,
    "truth": 1.8,
    "reality": 1.9,
    "fact": 2.5,
    "evidence": 2.6,
    # 1.0-1.9 — Very abstract (philosophical, metaphysical)
    "essence": 1.5,
    "being": 1.6,
    "existence": 1.6,
    "nature": 2.0,
    "consciousness": 1.4,
    "soul": 1.7,
    "spirit": 1.6,
    "mind": 1.9,
    "infinity": 1.3,
    "eternity": 1.3,
    "void": 1.8,
    "nothingness": 1.2,
    "transcendence": 1.2,
    "enlightenment": 1.5,
    "nirvana": 1.4,
    "karma": 1.5,
    "dharma": 1.3,
    "chakra": 1.6,
    "aura": 1.7,
    "cosmic": 1.4,
    "divine": 1.5,
    "sacred": 1.6,
    "holy": 1.8,
    "mystical": 1.3,
    "spiritual": 1.5,
    "metaphysical": 1.2,
    "ontological": 1.1,
    "phenomenal": 1.5,
    "archetypal": 1.3,
    "sublime": 1.4,
    "profound": 1.6,
    "absolute": 1.5,
    "ultimate": 1.6,
    "primordial": 1.3,
    "eternal": 1.4,
    "infinite": 1.3,
    "universal": 1.6,
    "resonance": 1.8,
    "vibration": 2.2,
    "frequency": 2.5,
    "harmony": 1.9,
    "alignment": 2.2,
    "attunement": 1.5,
    "manifestation": 1.6,
    "emanation": 1.3,
    "creation": 2.0,
    "destruction": 2.2,
    "wisdom": 1.8,
    "intuition": 1.7,
    "revelation": 1.6,
    "epiphany": 1.5,
}


def score_concreteness_norms(text: str) -> float | None:
    """Score text concreteness using psycholinguistic word norms.

    Returns 0.0-1.0 (normalized from the 1-5 scale) or None if
    fewer than 3 words have norm data (not enough signal).
    """
    words = re.findall(r"\b[a-z]{3,}\b", text.lower())
    if not words:
        return None

    scored_words: list[float] = []
    for word in words:
        if word in _CONCRETENESS_NORMS:
            scored_words.append(_CONCRETENESS_NORMS[word])

    if len(scored_words) < 3:
        return None  # not enough data to score reliably

    avg = sum(scored_words) / len(scored_words)
    # Normalize 1-5 scale to 0-1
    return max(0.0, min(1.0, (avg - 1.0) / 4.0))


# ─── Tier 2: TF-IDF Semantic Similarity ──────────────────────────────
#
# Compares text against reference corpora of "grounded" and "esoteric"
# language to score how similar the text is to each.

_GROUNDED_REFERENCE = [
    "Store events in an append-only SQLite database with SHA256 hash verification.",
    "Run pytest after every code change to verify tests pass.",
    "The pipeline extracts knowledge from session transcripts and deduplicates.",
    "Filter noise entries before storing knowledge to prevent contamination.",
    "Use snake_case for all function and variable names.",
    "Read files before editing. Check test output before claiming success.",
    "The quality gate blocks knowledge extraction from dishonest sessions.",
    "Track lesson occurrences and promote status from active to improving to resolved.",
    "Compute importance scores using confidence, access count, and recency decay.",
    "Parse JSON records from session logs to extract corrections and preferences.",
    "Configure log rotation to prevent disk bloat from accumulating log files.",
    "The maturity lifecycle promotes knowledge from RAW to HYPOTHESIS to CONFIRMED.",
    "Detect contradictions by comparing word overlap and checking negation markers.",
    "Build a CLI command with click decorators and register it in the command group.",
    "Query the FTS5 index for full-text search across knowledge entries.",
]

_ESOTERIC_REFERENCE = [
    "The cosmic consciousness transcends the boundaries of mortal understanding.",
    "Sacred geometry reveals the divine patterns underlying all of existence.",
    "Through meditation the soul attains enlightenment and merges with the infinite.",
    "The akashic records contain the vibrational frequency of every thought ever conceived.",
    "Kundalini energy rises through the chakras bringing spiritual awakening.",
    "The eternal essence of being emanates from the primordial void.",
    "Quantum consciousness suggests that awareness is fundamental to reality itself.",
    "The mystical union of spirit and matter creates the sacred dance of creation.",
    "Divine resonance aligns the celestial harmonies with earthly manifestation.",
    "The archetypal patterns of the collective unconscious shape all human experience.",
    "Through attunement to universal vibrations one transcends the veil of maya.",
    "The soul journey through samsara leads ultimately to nirvana and liberation.",
    "Ethereal dimensions of consciousness exist beyond the physical realm.",
    "The sacred mantra vibrates at the frequency of cosmic truth.",
    "Spiritual evolution unfolds through cycles of death and reincarnation.",
]

_tfidf_vectorizer = None
_tfidf_grounded_vecs = None
_tfidf_esoteric_vecs = None


def _ensure_tfidf() -> bool:
    """Initialize TF-IDF vectorizer and reference vectors."""
    global _tfidf_vectorizer, _tfidf_grounded_vecs, _tfidf_esoteric_vecs
    if _tfidf_vectorizer is not None:
        return True
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer

        all_docs = _GROUNDED_REFERENCE + _ESOTERIC_REFERENCE
        _tfidf_vectorizer = TfidfVectorizer(
            stop_words="english", max_features=5000, ngram_range=(1, 2)
        )
        all_vecs = _tfidf_vectorizer.fit_transform(all_docs)
        n_grounded = len(_GROUNDED_REFERENCE)
        _tfidf_grounded_vecs = all_vecs[:n_grounded]
        _tfidf_esoteric_vecs = all_vecs[n_grounded:]
        return True
    except ImportError:
        logger.debug("sklearn not available for TF-IDF scoring")
        return False


def score_tfidf_grounding(text: str) -> dict[str, float] | None:
    """Score how similar text is to grounded vs esoteric reference corpora.

    Returns {"grounded": 0-1, "esoteric": 0-1, "ratio": -1 to 1} or None.
    Positive ratio = grounded, negative = esoteric.
    """
    if not _ensure_tfidf() or _tfidf_vectorizer is None:
        return None

    try:
        from sklearn.metrics.pairwise import cosine_similarity

        text_vec = _tfidf_vectorizer.transform([text])
        grounded_sim = cosine_similarity(text_vec, _tfidf_grounded_vecs).max()
        esoteric_sim = cosine_similarity(text_vec, _tfidf_esoteric_vecs).max()

        grounded_score = float(max(0.0, min(1.0, grounded_sim)))
        esoteric_score = float(max(0.0, min(1.0, esoteric_sim)))

        total = grounded_score + esoteric_score
        ratio = (grounded_score - esoteric_score) / total if total > 0 else 0.0

        return {
            "grounded": grounded_score,
            "esoteric": esoteric_score,
            "ratio": ratio,
        }
    except _SIS_ML_ERRORS as e:
        logger.debug(f"TF-IDF scoring failed: {e}")
        return None


# ─── Tier 3: Sentence Embeddings ─────────────────────────────────────
#
# Uses sentence-transformers for deep semantic understanding.
# Can detect paraphrased esoteric content even without keyword matches.

_embedding_model = None
_grounded_embeddings = None
_esoteric_embeddings = None


def _ensure_embeddings() -> bool:
    """Load sentence-transformers model and compute reference embeddings."""
    global _embedding_model, _grounded_embeddings, _esoteric_embeddings
    if _embedding_model is not None:
        return True
    try:
        from sentence_transformers import SentenceTransformer

        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
        _grounded_embeddings = _embedding_model.encode(_GROUNDED_REFERENCE, convert_to_numpy=True)
        _esoteric_embeddings = _embedding_model.encode(_ESOTERIC_REFERENCE, convert_to_numpy=True)
        return True
    except ImportError:
        logger.debug("sentence-transformers not available for embedding scoring")
        return False
    except _SIS_ML_ERRORS as e:
        logger.debug(f"Failed to load embedding model: {e}")
        return False


def score_semantic_grounding(text: str) -> dict[str, float] | None:
    """Score semantic similarity to grounded vs esoteric reference text.

    Uses sentence embeddings for deep meaning comparison.
    Returns {"grounded": 0-1, "esoteric": 0-1, "ratio": -1 to 1} or None.
    """
    if not _ensure_embeddings() or _embedding_model is None:
        return None

    try:
        from sklearn.metrics.pairwise import cosine_similarity as cos_sim

        text_embedding = _embedding_model.encode([text], convert_to_numpy=True)

        grounded_sims = cos_sim(text_embedding, _grounded_embeddings)
        esoteric_sims = cos_sim(text_embedding, _esoteric_embeddings)

        grounded_score = float(grounded_sims.max())
        esoteric_score = float(esoteric_sims.max())

        grounded_score = max(0.0, min(1.0, grounded_score))
        esoteric_score = max(0.0, min(1.0, esoteric_score))

        total = grounded_score + esoteric_score
        ratio = (grounded_score - esoteric_score) / total if total > 0 else 0.0

        return {
            "grounded": grounded_score,
            "esoteric": esoteric_score,
            "ratio": ratio,
        }
    except _SIS_ML_ERRORS as e:
        logger.debug(f"Embedding scoring failed: {e}")
        return None


# ─── Combined Multi-Tier Scoring ─────────────────────────────────────


def score_all_tiers(text: str) -> dict[str, Any]:
    """Run all available tiers and return combined results.

    Always runs Tier 1 (keyword-based, from semantic_integrity.py).
    Adds Tier 2 (norms + TF-IDF) and Tier 3 (embeddings) when available.
    """
    result: dict[str, Any] = {
        "tiers_used": ["lexical"],
    }

    # Tier 2a: Concreteness norms
    norms_score = score_concreteness_norms(text)
    if norms_score is not None:
        result["concreteness_norms"] = norms_score
        if "statistical" not in result["tiers_used"]:
            result["tiers_used"].append("statistical")

    # Tier 2b: TF-IDF grounding
    tfidf_result = score_tfidf_grounding(text)
    if tfidf_result is not None:
        result["tfidf"] = tfidf_result
        if "statistical" not in result["tiers_used"]:
            result["tiers_used"].append("statistical")

    # Tier 3: Semantic embeddings
    semantic_result = score_semantic_grounding(text)
    if semantic_result is not None:
        result["semantic"] = semantic_result
        result["tiers_used"].append("semantic")

    # Compute combined grounding score across all available tiers
    scores: list[float] = []
    weights: list[float] = []

    if norms_score is not None:
        scores.append(norms_score)
        weights.append(0.25)

    if tfidf_result is not None:
        # Convert ratio (-1 to 1) to 0-1 scale
        scores.append((tfidf_result["ratio"] + 1) / 2)
        weights.append(0.30)

    if semantic_result is not None:
        scores.append((semantic_result["ratio"] + 1) / 2)
        weights.append(0.45)  # highest weight — most reliable

    if scores:
        total_weight = sum(weights)
        result["combined_grounding"] = sum(s * w for s, w in zip(scores, weights)) / total_weight
    else:
        result["combined_grounding"] = None

    return result
