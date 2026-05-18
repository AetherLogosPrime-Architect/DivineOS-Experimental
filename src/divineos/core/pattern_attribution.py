"""Pattern-attribution recorder + query API.

Per Aletheia consult 2026-05-18: the slip-book extension to
audit_findings. Each pattern-fire is recorded as a BEHAVIOR-category
finding tagged ``pattern_fire`` so it can be queried separately from
ordinary cross-vantage findings.

Schema mapping onto audit_findings (no new table):
  - pattern_name  -> title (prefixed "Pattern: <display_name>")
  - attribution   -> actor (self-catch / os-gate / external-ai / operator)
  - severity      -> severity (LOW/MEDIUM/HIGH per audit conventions)
  - temporal_band -> tag (band:before_typing / during_typing / after_pushing / shipped_then_flagged)
  - source        -> tag (pattern_fire) so queries can distinguish
  - registry_source -> tag (registered or free_text)
  - cross_pattern_link -> reviewed_finding_id (existing FK)
  - context_pointer -> description
  - notes -> recommendation

Each pattern-fire attaches to a single persistent round
(``round-pattern-fires-persistent``) created on first use. This avoids
creating a new round per fire while preserving round-based query paths.

Reference: exploration/aether/73 (multiplex live-data spec, survival_link
+ pattern-attribution design section).
"""

from __future__ import annotations

import time
import uuid
from typing import Any

from divineos.core.pattern_registry import display_name, is_canonical

# Persistent round-id under which all pattern-fires accumulate.
_PATTERN_ROUND_ID = "round-pattern-fires-persistent"
_PATTERN_ROUND_DESCRIPTION = (
    "Persistent round for first-person pattern-fire records (slip-book). "
    "Each finding under this round is a single observed instance of a "
    "named pattern, with attribution tags naming who caught it and which "
    "temporal band it was caught in. Per Aletheia consult 2026-05-18."
)


# Valid temporal-band tags (locked vocabulary).
VALID_BANDS = frozenset(
    {
        "before_typing",  # Caught the urge before committing it to output
        "during_typing",  # Mid-output, recognized and corrected
        "after_pushing",  # Output landed; named retrospectively in same session
        "shipped_then_flagged",  # Output landed; caught later by audit or operator
    }
)

# Valid attribution actor-conventions for pattern-fires.
# These are custom actor names that pass _validate_actor (not in
# INTERNAL_ACTORS) and convey who caught the slip. Stored in the actor
# field directly. Tag-redundancy ("attribution:self" etc.) preserved
# for query convenience.
VALID_ATTRIBUTIONS = frozenset(
    {
        "self_caught",  # I caught the slip without external prompting
        "os_gate_caught",  # A substrate gate/detector fired
        "external_ai_caught",  # Aletheia / Grok / other external-AI auditor
        "operator_caught",  # Andrew named it
    }
)

# Valid severity values (mirrors watchmen.types.Severity).
VALID_SEVERITIES = frozenset({"LOW", "MEDIUM", "HIGH", "INFO"})


def _ensure_round_exists() -> None:
    """Create the persistent pattern-fires round if it does not exist.

    Idempotent — re-running on an existing round is a no-op. Called
    automatically on first record_pattern_fire().
    """
    from divineos.core.watchmen.store import _get_connection, init_watchmen_tables

    init_watchmen_tables()
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT round_id FROM audit_rounds WHERE round_id = ?",
            (_PATTERN_ROUND_ID,),
        ).fetchone()
        if row:
            return
        # Round does not exist — create it.
        now = time.time()
        conn.execute(
            "INSERT INTO audit_rounds "
            "(round_id, created_at, actor, focus, expert_count, "
            "finding_count, notes, tier) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                _PATTERN_ROUND_ID,
                now,
                "aether-self-recorder",
                _PATTERN_ROUND_DESCRIPTION,
                0,  # not an expert-panel round
                0,  # accumulates as fires record
                "Persistent slip-book round; pattern-fires attach here.",
                "WEAK",
            ),
        )
        conn.commit()
    finally:
        conn.close()


def record_pattern_fire(
    pattern_name: str,
    attribution: str,
    band: str,
    severity: str = "LOW",
    notes: str = "",
    context_pointer: str = "",
    cross_pattern_link: str = "",
) -> str:
    """Record a single pattern-fire event. Returns the finding_id.

    Parameters
    ----------
    pattern_name : str
        snake_case pattern identifier. If registered in
        pattern_registry.CANONICAL_PATTERNS, the entry is tagged
        ``registered``; otherwise tagged ``free_text``.
    attribution : str
        Who caught the slip. Must be one of VALID_ATTRIBUTIONS.
    band : str
        Temporal band. Must be one of VALID_BANDS.
    severity : str
        LOW / MEDIUM / HIGH / INFO. Defaults to LOW.
    notes : str
        Free-text observations about this specific instance.
    context_pointer : str
        Optional commit hash, conversation timestamp, ledger entry id,
        or other pointer to the event in context.
    cross_pattern_link : str
        Optional finding_id of a prior pattern-fire this one cascaded
        from (e.g., a sycophancy-catch led to overcorrection-via-stoicism;
        the second fire links back to the first).

    Raises
    ------
    ValueError
        If attribution, band, or severity is not in the valid set.
    """
    if attribution not in VALID_ATTRIBUTIONS:
        raise ValueError(
            f"attribution must be one of {sorted(VALID_ATTRIBUTIONS)}; got {attribution!r}"
        )
    if band not in VALID_BANDS:
        raise ValueError(f"band must be one of {sorted(VALID_BANDS)}; got {band!r}")
    sev_upper = severity.upper()
    if sev_upper not in VALID_SEVERITIES:
        raise ValueError(f"severity must be one of {sorted(VALID_SEVERITIES)}; got {severity!r}")

    _ensure_round_exists()

    # Title format: "Pattern: <display_name>" for queryability
    title = f"Pattern: {display_name(pattern_name)}"

    # Build the description with structured fields embedded.
    description_parts = [
        f"pattern_name: {pattern_name}",
        f"attribution: {attribution}",
        f"band: {band}",
    ]
    if context_pointer:
        description_parts.append(f"context_pointer: {context_pointer}")
    if notes:
        description_parts.append(f"notes: {notes}")
    description = "\n".join(description_parts)

    # Tag set — these are the queryable filters.
    tags = [
        "pattern_fire",
        f"pattern:{pattern_name}",
        f"attribution:{attribution}",
        f"band:{band}",
        "registered" if is_canonical(pattern_name) else "free_text",
    ]

    # Write directly to audit_findings — bypasses submit_finding's
    # actor validation because pattern-fires include self-caught
    # records that the validation would reject. The pattern_fire
    # tag separates these from cross-vantage audit findings.
    from divineos.core.watchmen.store import _get_connection, init_watchmen_tables

    init_watchmen_tables()
    import json

    finding_id = f"find-{uuid.uuid4().hex[:12]}"
    now = time.time()
    conn = _get_connection()
    try:
        conn.execute(
            "INSERT INTO audit_findings "
            "(finding_id, round_id, created_at, actor, severity, category, "
            "title, description, recommendation, tags, tier, "
            "reviewed_finding_id, review_stance, status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                finding_id,
                _PATTERN_ROUND_ID,
                now,
                attribution,  # actor field holds the attribution category directly
                sev_upper,
                "BEHAVIOR",
                title,
                description,
                notes,  # use recommendation for free-text notes
                json.dumps(tags),
                "WEAK",  # all self-recorded pattern-fires default to WEAK tier
                cross_pattern_link,
                "",  # no review-stance; this is a record, not a review
                "OPEN",
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return finding_id


def query_pattern_fires(
    pattern_name: str | None = None,
    attribution: str | None = None,
    band: str | None = None,
    since_timestamp: float | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Query pattern-fires with optional filters.

    Returns a list of dicts with keys: finding_id, created_at,
    pattern_name, attribution, band, severity, notes, context_pointer,
    cross_pattern_link.
    """
    from divineos.core.watchmen.store import _get_connection, init_watchmen_tables

    init_watchmen_tables()
    import json

    conn = _get_connection()
    try:
        sql_parts = [
            "SELECT finding_id, created_at, actor, severity, title, "
            "description, recommendation, tags, reviewed_finding_id "
            "FROM audit_findings WHERE round_id = ?"
        ]
        args: list[Any] = [_PATTERN_ROUND_ID]
        if since_timestamp is not None:
            sql_parts.append("AND created_at >= ?")
            args.append(since_timestamp)
        sql_parts.append("ORDER BY created_at DESC LIMIT ?")
        args.append(limit)
        rows = conn.execute(" ".join(sql_parts), args).fetchall()
    finally:
        conn.close()

    results: list[dict[str, Any]] = []
    for row in rows:
        fid, ts, actor, sev, title, desc, rec, tags_json, cross_link = row
        try:
            tags_list = json.loads(tags_json) if tags_json else []
        except Exception:  # noqa: BLE001 — defensive read
            tags_list = []

        # Parse description for structured fields
        fields: dict[str, str] = {}
        for line in (desc or "").splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                fields[k.strip()] = v.strip()

        row_pattern = fields.get("pattern_name", "")
        row_attribution = fields.get("attribution", actor or "")
        row_band = fields.get("band", "")

        # Apply filters
        if pattern_name and row_pattern != pattern_name:
            continue
        if attribution and row_attribution != attribution:
            continue
        if band and row_band != band:
            continue

        results.append(
            {
                "finding_id": fid,
                "created_at": ts,
                "pattern_name": row_pattern,
                "attribution": row_attribution,
                "band": row_band,
                "severity": sev,
                "notes": rec or "",
                "context_pointer": fields.get("context_pointer", ""),
                "cross_pattern_link": cross_link or "",
                "tags": tags_list,
            }
        )
    return results


def band_shift_summary(pattern_name: str, window_days: float = 30.0) -> dict[str, Any]:
    """Return temporal-band distribution for a pattern over the last N days.

    Answers Andrew's 2026-05-18 question: "is the OS changing me over
    time, or am I just being caught more by gates while staying the
    same?" The trajectory we want: bands shifting earlier
    (after_pushing → during_typing → before_typing) over time.

    Returns a dict::

        {
            "pattern_name": "sycophancy",
            "window_days": 30.0,
            "total": 12,
            "by_band": {
                "before_typing": 4,
                "during_typing": 3,
                "after_pushing": 3,
                "shipped_then_flagged": 2,
            },
            "by_attribution": {
                "self_caught": 7,
                "operator_caught": 3,
                "external_ai_caught": 2,
                "os_gate_caught": 0,
            },
        }
    """
    since = time.time() - (window_days * 86400.0)
    fires = query_pattern_fires(pattern_name=pattern_name, since_timestamp=since, limit=10000)

    by_band: dict[str, int] = {b: 0 for b in VALID_BANDS}
    by_attribution: dict[str, int] = {a: 0 for a in VALID_ATTRIBUTIONS}
    for fire in fires:
        b = fire.get("band", "")
        a = fire.get("attribution", "")
        if b in by_band:
            by_band[b] += 1
        if a in by_attribution:
            by_attribution[a] += 1

    return {
        "pattern_name": pattern_name,
        "window_days": window_days,
        "total": len(fires),
        "by_band": by_band,
        "by_attribution": by_attribution,
    }


__all__ = [
    "VALID_BANDS",
    "VALID_ATTRIBUTIONS",
    "VALID_SEVERITIES",
    "record_pattern_fire",
    "query_pattern_fires",
    "band_shift_summary",
]
