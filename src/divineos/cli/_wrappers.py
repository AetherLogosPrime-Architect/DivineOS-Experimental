"""Tool wrappers and DB initialization for the CLI."""

from pathlib import Path

import click

from divineos.analysis.record_extraction import init_quality_tables
from divineos.analysis.feature_storage import init_feature_tables, store_features
from divineos.analysis.session_features import (
    get_cross_session_summary,
    run_all_features,
)
from divineos.core.knowledge import (
    apply_session_feedback,
    clear_lessons,
    consolidate_related,
    deep_extract_knowledge,
    generate_briefing,
    get_knowledge,
    get_lesson_summary,
    get_lessons,
    health_check,
    init_knowledge_table,
    knowledge_health_report,
    knowledge_stats,
    migrate_knowledge_types,
    rebuild_fts_index,
    store_knowledge,
)
from divineos.core.ledger import (
    clean_corrupted_events,
    count_events,
    export_to_markdown,
    get_events,
    get_recent_context,
    init_db,
    log_event,
    logger,
    search_events,
    verify_all_events,
)
from divineos.core.memory import (
    clear_core,
    format_core,
    format_recall,
    get_active_memory,
    init_memory_tables,
    promote_to_active,
    recall,
    refresh_active_memory,
    set_core,
)
from divineos.core.tool_wrapper import wrap_tool_execution

# Wrap critical tool calls for event capture
_wrapped_log_event = wrap_tool_execution("log_event", log_event)
_wrapped_get_events = wrap_tool_execution("get_events", get_events)
_wrapped_search_events = wrap_tool_execution("search_events", search_events)
_wrapped_count_events = wrap_tool_execution("count_events", count_events)
_wrapped_get_recent_context = wrap_tool_execution("get_recent_context", get_recent_context)
_wrapped_verify_all_events = wrap_tool_execution("verify_all_events", verify_all_events)
_wrapped_clean_corrupted_events = wrap_tool_execution(
    "clean_corrupted_events",
    clean_corrupted_events,
)
_wrapped_export_to_markdown = wrap_tool_execution("export_to_markdown", export_to_markdown)

# Wrap knowledge consolidation tools
_wrapped_store_knowledge = wrap_tool_execution("store_knowledge", store_knowledge)
_wrapped_get_knowledge = wrap_tool_execution("get_knowledge", get_knowledge)
_wrapped_generate_briefing = wrap_tool_execution("generate_briefing", generate_briefing)
_wrapped_knowledge_stats = wrap_tool_execution("knowledge_stats", knowledge_stats)
_wrapped_rebuild_fts_index = wrap_tool_execution("rebuild_fts_index", rebuild_fts_index)
_wrapped_get_lesson_summary = wrap_tool_execution("get_lesson_summary", get_lesson_summary)
_wrapped_get_lessons = wrap_tool_execution("get_lessons", get_lessons)
_wrapped_deep_extract_knowledge = wrap_tool_execution(
    "deep_extract_knowledge",
    deep_extract_knowledge,
)
_wrapped_consolidate_related = wrap_tool_execution("consolidate_related", consolidate_related)
_wrapped_apply_session_feedback = wrap_tool_execution(
    "apply_session_feedback",
    apply_session_feedback,
)
_wrapped_health_check = wrap_tool_execution("health_check", health_check)
_wrapped_knowledge_health_report = wrap_tool_execution(
    "knowledge_health_report",
    knowledge_health_report,
)
_wrapped_clear_lessons = wrap_tool_execution("clear_lessons", clear_lessons)
_wrapped_migrate_knowledge_types = wrap_tool_execution(
    "migrate_knowledge_types",
    migrate_knowledge_types,
)

# Wrap memory tools
_wrapped_set_core = wrap_tool_execution("set_core", set_core)
_wrapped_clear_core = wrap_tool_execution("clear_core", clear_core)
_wrapped_format_core = wrap_tool_execution("format_core", format_core)
_wrapped_promote_to_active = wrap_tool_execution("promote_to_active", promote_to_active)
_wrapped_get_active_memory = wrap_tool_execution("get_active_memory", get_active_memory)
_wrapped_refresh_active_memory = wrap_tool_execution("refresh_active_memory", refresh_active_memory)
_wrapped_recall = wrap_tool_execution("recall", recall)
_wrapped_format_recall = wrap_tool_execution("format_recall", format_recall)

# Wrap analysis tools
_wrapped_run_all_features = wrap_tool_execution("run_all_features", run_all_features)
_wrapped_store_features = wrap_tool_execution("store_features", store_features)
_wrapped_get_cross_session_summary = wrap_tool_execution(
    "get_cross_session_summary",
    get_cross_session_summary,
)


_db_ready = False


def _load_seed_if_empty() -> None:
    """Populate a fresh database from seed.json using the seed manager."""
    import json as _json

    from divineos.core.seed_manager import (
        apply_seed,
        get_applied_seed_version,
        should_reseed,
        validate_seed,
    )

    seed_path = Path(__file__).parent.parent / "seed.json"
    if not seed_path.exists():
        return

    seed = _json.loads(seed_path.read_text(encoding="utf-8"))

    errors = validate_seed(seed)
    if errors:
        logger.warning(f"Seed validation errors: {errors}")

    current_version = get_applied_seed_version()
    seed_version = seed.get("version", "0.0.0")

    if not should_reseed(current_version, seed_version):
        return

    counts = apply_seed(seed, mode="merge")

    if counts["knowledge"] or counts["lessons"] or counts["core_slots"]:
        click.secho(
            f"[+] Seed v{seed_version} applied: "
            f"{counts['core_slots']} core slots, "
            f"{counts['knowledge']} knowledge, "
            f"{counts['lessons']} lessons "
            f"({counts['skipped']} skipped as existing).",
            fg="green",
        )

    try:
        _wrapped_refresh_active_memory(importance_threshold=0.3)
    except Exception as e:
        logger.debug("Post-seed memory refresh failed (best-effort): %s", e)


def _ensure_db() -> None:
    """Create all tables if they don't exist. Idempotent and fast after first call."""
    global _db_ready  # noqa: PLW0603
    if _db_ready:
        return
    init_db()
    init_knowledge_table()
    init_quality_tables()
    init_feature_tables()
    init_memory_tables()
    from divineos.core.knowledge.relationships import init_relationship_table

    init_relationship_table()

    from divineos.core.growth import init_session_history_table
    from divineos.core.tone_texture import init_tone_texture_table

    init_session_history_table()
    init_tone_texture_table()

    from divineos.core.logic.warrants import init_warrant_table
    from divineos.core.logic.relations import init_relation_table

    init_warrant_table()
    init_relation_table()

    _load_seed_if_empty()
    _db_ready = True
