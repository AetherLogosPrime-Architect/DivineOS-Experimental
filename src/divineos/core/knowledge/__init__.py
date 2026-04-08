"""Knowledge sub-package — re-exports all public names for backward compatibility.

Modules:
    _base            — Constants, DB connection, schema, row helpers
    _text            — Text analysis, noise filtering, temporal markers
    crud             — Store, get, search, update, supersede, record_access
    lessons          — Lesson tracking + report extraction
    retrieval        — Briefing generation, stats, unconsolidated events
    extraction       — Smart storage, consolidation
    deep_extraction  — Deep session knowledge extraction
    feedback         — Health check, confidence adjustment, effectiveness
    migration        — Type migration, lesson categorization, session feedback, health report
"""

# _base
from divineos.core.knowledge._base import (
    KNOWLEDGE_MATURITY,
    KNOWLEDGE_SOURCES,
    KNOWLEDGE_TYPES,
    _KNOWLEDGE_COLS,
    _KNOWLEDGE_COLS_K,
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
    compute_semantic_similarity,
    compute_similarity,
    _extract_key_terms,
    _has_temporal_markers,
    _is_extraction_noise,
    _normalize_text,
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

# extraction
from divineos.core.knowledge.extraction import (
    _decide_operation,
    consolidate_related,
    store_knowledge_smart,
)

# deep_extraction
from divineos.core.knowledge.deep_extraction import (
    _ALTERNATIVE_PATTERNS,
    _REASON_PATTERNS,
    _distill_correction,
    _distill_preference,
    _extract_assistant_summary,
    _extract_user_text_from_record,
    _find_alternative_in_text,
    _find_reason_in_text,
    deep_extract_knowledge,
)

# feedback
from divineos.core.knowledge.feedback import (
    _adjust_confidence,
    _resolve_lesson,
    compute_effectiveness,
    health_check,
)

# migration
from divineos.core.knowledge.migration import (
    _LESSON_CATEGORIES,
    _MIGRATION_RULES,
    _categorize_correction,
    _is_noise_correction,
    apply_session_feedback,
    knowledge_health_report,
    migrate_knowledge_types,
)

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
    # extraction
    "_decide_operation",
    "consolidate_related",
    "store_knowledge_smart",
    # deep_extraction
    "_ALTERNATIVE_PATTERNS",
    "_REASON_PATTERNS",
    "_distill_correction",
    "_distill_preference",
    "_extract_assistant_summary",
    "_extract_user_text_from_record",
    "_find_alternative_in_text",
    "_find_reason_in_text",
    "deep_extract_knowledge",
    # feedback
    "_adjust_confidence",
    "_resolve_lesson",
    "compute_effectiveness",
    "health_check",
    # migration
    "_LESSON_CATEGORIES",
    "_MIGRATION_RULES",
    "_categorize_correction",
    "_is_noise_correction",
    "apply_session_feedback",
    "knowledge_health_report",
    "migrate_knowledge_types",
]
