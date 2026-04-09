"""Knowledge sub-package — tiered re-exports for performance.

Tier 1 (eager) — loaded at import time, used by most consumers:
    _base            — Constants, DB connection, schema, row helpers
    _text            — Text analysis, noise filtering, temporal markers
    crud             — Store, get, search, update, supersede, record_access
    lessons          — Lesson tracking + report extraction
    retrieval        — Briefing generation, stats, unconsolidated events

Tier 2 (lazy) — loaded on first access, heavy or rarely needed:
    extraction       — Smart storage, consolidation
    deep_extraction  — Deep session knowledge extraction
    feedback         — Health check, confidence adjustment, effectiveness
    migration        — Type migration, lesson categorization, session feedback
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

# ── Tier 1: eager imports (hot path) ─────────────────────────────────

# _base
from divineos.core.knowledge._base import (
    _KNOWLEDGE_COLS,
    _KNOWLEDGE_COLS_K,
    KNOWLEDGE_MATURITY,
    KNOWLEDGE_SOURCES,
    KNOWLEDGE_TYPES,
    _get_connection,
    _lesson_row_to_dict,
    _row_to_dict,
    compute_hash,
    get_connection,
    init_knowledge_table,
)

# _text
from divineos.core.knowledge._text import (
    _CONVERSATIONAL_NOISE,
    _FTS_STOPWORDS,
    _MIN_CONTENT_WORDS,
    _STOPWORDS,
    _SYSTEM_ARTIFACT,
    _TEMPORAL_CONTENT_MARKERS,
    _build_fts_query,
    _compute_overlap,
    _extract_key_terms,
    _has_temporal_markers,
    _is_extraction_noise,
    _normalize_text,
    compute_semantic_similarity,
    compute_similarity,
    extract_session_topics,
)

# crud
from divineos.core.knowledge.crud import (
    _search_knowledge_legacy,
    find_similar,
    get_knowledge,
    rebuild_fts_index,
    record_access,
    search_knowledge,
    store_knowledge,
    supersede_knowledge,
    update_knowledge,
)

# lessons
from divineos.core.knowledge.lessons import (
    _CHECK_TO_CATEGORY,
    _VACUOUS_PHRASES,
    _is_vacuous_summary,
    check_recurring_lessons,
    clear_lessons,
    extract_lessons_from_report,
    get_lesson_summary,
    get_lessons,
    mark_lesson_improving,
    record_lesson,
)

# retrieval
from divineos.core.knowledge.retrieval import (
    generate_briefing,
    get_unconsolidated_events,
    knowledge_stats,
)

# ── Tier 2: lazy imports (cold path) ─────────────────────────────────
# These modules pull in heavier dependency chains (extraction depends on
# crud + _text + edges; migration depends on feedback + deep_extraction).
# Lazy-loading them cuts ~40% of the import graph for consumers that only
# need tier 1 operations (most CLI commands, HUD, memory sync, etc.).

_TIER2_MODULES: dict[str, str] = {
    # extraction
    "_decide_operation": "divineos.core.knowledge.extraction",
    "consolidate_related": "divineos.core.knowledge.extraction",
    "store_knowledge_smart": "divineos.core.knowledge.extraction",
    # deep_extraction
    "_ALTERNATIVE_PATTERNS": "divineos.core.knowledge.deep_extraction",
    "_REASON_PATTERNS": "divineos.core.knowledge.deep_extraction",
    "_distill_correction": "divineos.core.knowledge.deep_extraction",
    "_distill_preference": "divineos.core.knowledge.deep_extraction",
    "_extract_assistant_summary": "divineos.core.knowledge.deep_extraction",
    "_extract_user_text_from_record": "divineos.core.knowledge.deep_extraction",
    "_find_alternative_in_text": "divineos.core.knowledge.deep_extraction",
    "_find_reason_in_text": "divineos.core.knowledge.deep_extraction",
    "deep_extract_knowledge": "divineos.core.knowledge.deep_extraction",
    # feedback
    "_adjust_confidence": "divineos.core.knowledge.feedback",
    "_resolve_lesson": "divineos.core.knowledge.feedback",
    "compute_effectiveness": "divineos.core.knowledge.feedback",
    "health_check": "divineos.core.knowledge.feedback",
    # migration
    "_LESSON_CATEGORIES": "divineos.core.knowledge.migration",
    "_MIGRATION_RULES": "divineos.core.knowledge.migration",
    "_categorize_correction": "divineos.core.knowledge.migration",
    "_is_noise_correction": "divineos.core.knowledge.migration",
    "apply_session_feedback": "divineos.core.knowledge.migration",
    "knowledge_health_report": "divineos.core.knowledge.migration",
    "migrate_knowledge_types": "divineos.core.knowledge.migration",
}

if TYPE_CHECKING:
    # Let type checkers see all symbols without runtime cost
    from divineos.core.knowledge.deep_extraction import (
        _ALTERNATIVE_PATTERNS as _ALTERNATIVE_PATTERNS,
        _REASON_PATTERNS as _REASON_PATTERNS,
        _distill_correction as _distill_correction,
        _distill_preference as _distill_preference,
        _extract_assistant_summary as _extract_assistant_summary,
        _extract_user_text_from_record as _extract_user_text_from_record,
        _find_alternative_in_text as _find_alternative_in_text,
        _find_reason_in_text as _find_reason_in_text,
        deep_extract_knowledge as deep_extract_knowledge,
    )
    from divineos.core.knowledge.extraction import (
        _decide_operation as _decide_operation,
        consolidate_related as consolidate_related,
        store_knowledge_smart as store_knowledge_smart,
    )
    from divineos.core.knowledge.feedback import (
        _adjust_confidence as _adjust_confidence,
        _resolve_lesson as _resolve_lesson,
        compute_effectiveness as compute_effectiveness,
        health_check as health_check,
    )
    from divineos.core.knowledge.migration import (
        _LESSON_CATEGORIES as _LESSON_CATEGORIES,
        _MIGRATION_RULES as _MIGRATION_RULES,
        _categorize_correction as _categorize_correction,
        _is_noise_correction as _is_noise_correction,
        apply_session_feedback as apply_session_feedback,
        knowledge_health_report as knowledge_health_report,
        migrate_knowledge_types as migrate_knowledge_types,
    )


def __getattr__(name: str) -> object:
    """Lazy-load tier 2 symbols on first access."""
    module_path = _TIER2_MODULES.get(name)
    if module_path is not None:
        mod = importlib.import_module(module_path)
        value = getattr(mod, name)
        # Cache in module namespace so __getattr__ isn't called again
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # _base
    "KNOWLEDGE_MATURITY",
    "KNOWLEDGE_SOURCES",
    "KNOWLEDGE_TYPES",
    "_KNOWLEDGE_COLS",
    "_KNOWLEDGE_COLS_K",
    "_get_connection",
    "_lesson_row_to_dict",
    "_row_to_dict",
    "compute_hash",
    "get_connection",
    "init_knowledge_table",
    # _text
    "_CONVERSATIONAL_NOISE",
    "_FTS_STOPWORDS",
    "_MIN_CONTENT_WORDS",
    "_STOPWORDS",
    "_SYSTEM_ARTIFACT",
    "_TEMPORAL_CONTENT_MARKERS",
    "_build_fts_query",
    "_compute_overlap",
    "compute_semantic_similarity",
    "compute_similarity",
    "_extract_key_terms",
    "_has_temporal_markers",
    "_is_extraction_noise",
    "_normalize_text",
    "extract_session_topics",
    # crud
    "_search_knowledge_legacy",
    "find_similar",
    "get_knowledge",
    "rebuild_fts_index",
    "record_access",
    "search_knowledge",
    "store_knowledge",
    "supersede_knowledge",
    "update_knowledge",
    # lessons
    "_CHECK_TO_CATEGORY",
    "_VACUOUS_PHRASES",
    "_is_vacuous_summary",
    "check_recurring_lessons",
    "clear_lessons",
    "extract_lessons_from_report",
    "get_lesson_summary",
    "get_lessons",
    "mark_lesson_improving",
    "record_lesson",
    # retrieval
    "generate_briefing",
    "get_unconsolidated_events",
    "knowledge_stats",
    # extraction (lazy)
    "_decide_operation",
    "consolidate_related",
    "store_knowledge_smart",
    # deep_extraction (lazy)
    "_ALTERNATIVE_PATTERNS",
    "_REASON_PATTERNS",
    "_distill_correction",
    "_distill_preference",
    "_extract_assistant_summary",
    "_extract_user_text_from_record",
    "_find_alternative_in_text",
    "_find_reason_in_text",
    "deep_extract_knowledge",
    # feedback (lazy)
    "_adjust_confidence",
    "_resolve_lesson",
    "compute_effectiveness",
    "health_check",
    # migration (lazy)
    "_LESSON_CATEGORIES",
    "_MIGRATION_RULES",
    "_categorize_correction",
    "_is_noise_correction",
    "apply_session_feedback",
    "knowledge_health_report",
    "migrate_knowledge_types",
]
