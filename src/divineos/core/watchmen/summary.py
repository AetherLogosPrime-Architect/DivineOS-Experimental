"""Watchmen Summary — analytics, HUD integration, unresolved tracking."""

import sqlite3
from typing import Any

from divineos.core.knowledge import _get_connection
from divineos.core.watchmen._schema import init_watchmen_tables

# A finding counts as recognition (positive verification, not an open issue)
# when the actor marked it CONFIRMS — via review_stance OR via the title they
# authored. Round/commit-level confirmations can't set review_stance (it
# requires a reviewed_finding_id, and they review a round/commit, not a
# finding), so they arrive as title-prefixed "CONFIRMS …" with an empty
# stance. Keying recognition only off the stance column made the aggregate
# blind to them, inflating open_issue_count. The title is the actor's own
# declaration — reading it is not the code judging the work
# (code-does-not-think). Exception: "CONFIRMS-pending-empirical" carries a
# real open verification action, so it stays counted as an issue.
_RECOGNITION_SQL = (
    "((review_stance = 'CONFIRMS' OR title LIKE 'CONFIRMS%') "
    "AND title NOT LIKE '%PENDING-EMPIRICAL%')"
)


def get_watchmen_stats() -> dict[str, Any]:
    """Aggregate statistics across all audit findings.

    Returns counts by severity, category, status, and overall totals.

    Stance-aware split (2026-05-12, code-does-not-think directive):
    `open_count` continues to mean "everything not yet closed by the actor."
    `open_issue_count` adds the recognition-aware filter — OPEN findings
    whose review_stance is NOT CONFIRMS, i.e. real unresolved concerns vs
    positive-recognition events that were left OPEN by actor choice.
    `open_recognition_count` is the OPEN+CONFIRMS bucket — kept visible
    but not counted toward alarm-shaped aggregates. The status decision
    stays with the actor; the aggregate filters by data (stance), not by
    judgment.
    """
    init_watchmen_tables()
    conn = _get_connection()
    try:
        total = conn.execute("SELECT COUNT(*) FROM audit_findings").fetchone()[0]
        rounds = conn.execute("SELECT COUNT(*) FROM audit_rounds").fetchone()[0]

        by_severity: dict[str, int] = {}
        for row in conn.execute(
            "SELECT severity, COUNT(*) FROM audit_findings GROUP BY severity"
        ).fetchall():
            by_severity[row[0]] = row[1]

        by_category: dict[str, int] = {}
        for row in conn.execute(
            "SELECT category, COUNT(*) FROM audit_findings GROUP BY category"
        ).fetchall():
            by_category[row[0]] = row[1]

        by_status: dict[str, int] = {}
        for row in conn.execute(
            "SELECT status, COUNT(*) FROM audit_findings GROUP BY status"
        ).fetchall():
            by_status[row[0]] = row[1]

        # Recognition-aware open split. Filter at the aggregate, not at filing.
        open_recognition_count = conn.execute(
            f"SELECT COUNT(*) FROM audit_findings "  # nosec B608 — _RECOGNITION_SQL is a fixed literal
            f"WHERE status = 'OPEN' AND {_RECOGNITION_SQL}"
        ).fetchone()[0]
        open_total = by_status.get("OPEN", 0)
        open_issue_count = open_total - open_recognition_count

        # Alarm-bypass sanity check (council sweep 2026-06-02, direction #3).
        # The recognition filter excludes CONFIRMS-titled findings from
        # open_issue_count — but an adversary (or a slip) could hide a real
        # HIGH/CRITICAL concern by titling it "CONFIRMS-by-design", silencing
        # the alarm. A recognition that is ALSO high-severity and still OPEN
        # is suspicious by construction; we count it separately so it can
        # never silently vanish, and surface it.
        suspicious_recognition_count = conn.execute(
            f"SELECT COUNT(*) FROM audit_findings "  # nosec B608 — fixed literals
            f"WHERE status = 'OPEN' AND {_RECOGNITION_SQL} "
            f"AND severity IN ('HIGH', 'CRITICAL')"
        ).fetchone()[0]

        return {
            "total_rounds": rounds,
            "total_findings": total,
            "by_severity": by_severity,
            "by_category": by_category,
            "by_status": by_status,
            "open_count": open_total,
            "open_issue_count": open_issue_count,
            "open_recognition_count": open_recognition_count,
            "suspicious_recognition_count": suspicious_recognition_count,
            "resolved_count": by_status.get("RESOLVED", 0),
        }
    except sqlite3.OperationalError:
        return {
            "total_rounds": 0,
            "total_findings": 0,
            "by_severity": {},
            "by_category": {},
            "by_status": {},
            "open_count": 0,
            "open_issue_count": 0,
            "open_recognition_count": 0,
            "suspicious_recognition_count": 0,
            "resolved_count": 0,
        }
    finally:
        conn.close()


def unresolved_findings(
    limit: int = 10, include_recognitions: bool = False
) -> list[dict[str, Any]]:
    """Get unresolved findings ordered by severity (CRITICAL first).

    Used by the briefing and HUD to surface what still needs attention.

    Recognition-filter (2026-05-12, code-does-not-think directive):
    by default, CONFIRMS-stance findings are excluded — they are
    positive-verification events, not raises-of-new-issue, and surfacing
    them as "what still needs attention" is the alarm-shape that motivated
    this filter. The actor still owns each finding's status; the filter is
    a data-driven query, not a judgment override. Set
    ``include_recognitions=True`` to see them too.
    """
    init_watchmen_tables()
    severity_order = (
        "CASE severity "
        "WHEN 'CRITICAL' THEN 1 "
        "WHEN 'HIGH' THEN 2 "
        "WHEN 'MEDIUM' THEN 3 "
        "WHEN 'LOW' THEN 4 "
        "WHEN 'INFO' THEN 5 END"
    )

    stance_clause = "" if include_recognitions else f"AND NOT {_RECOGNITION_SQL} "

    conn = _get_connection()
    try:
        rows = conn.execute(
            f"SELECT finding_id, round_id, severity, category, title, description, status "  # nosec B608
            f"FROM audit_findings "
            f"WHERE status IN ('OPEN', 'ROUTED', 'IN_PROGRESS') "
            f"{stance_clause}"
            f"ORDER BY {severity_order}, created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()

        return [
            {
                "finding_id": r[0],
                "round_id": r[1],
                "severity": r[2],
                "category": r[3],
                "title": r[4],
                "description": r[5],
                "status": r[6],
            }
            for r in rows
        ]
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()


# Actors whose findings count as externally sourced. Kept aligned with
# _EXTERNAL_AI_ACTORS in scripts/check_multi_party_review.py, plus "user"
# (the human operator) — both are outside the running agent.
_EXTERNAL_ACTOR_NAMES = frozenset(
    {"user", "grok", "gemini", "aletheia", "external-auditor", "perplexity"}
)
_EXTERNAL_ACTOR_PREFIXES = ("claude-",)

# Label thresholds. These are JUDGEMENTS, not measurements — someone could
# argue any of them. The raw counts print alongside so the numbers survive
# the labels being wrong.
_FILING_WORKS_MIN_EXTERNAL_PCT = 50.0
_ROUTING_WORKS_MAX_UNROUTED_PCT = 25.0


def _is_external_actor(actor: str | None) -> bool:
    a = (actor or "").strip().lower()
    return a in _EXTERNAL_ACTOR_NAMES or a.startswith(_EXTERNAL_ACTOR_PREFIXES)


def watchmen_loop_status() -> str:
    """Report how much of the external-audit loop is closed — from the data.

    2026-08-01 REWRITE. This returned a hardcoded sentence asserting
    "external-actor filing works; routing to knowledge/claims/lessons
    works", printed unconditionally at the top of `divineos audit summary`.
    Its own docstring named the mechanism: "Updated manually as loop-closing
    features ship." A health claim maintained by hand drifts the moment
    nobody updates it, and then keeps certifying whatever it last said.

    Measured before rewriting — and the two halves scored differently,
    which is precisely what one static sentence cannot express:

        external-actor findings : 542/637 (85%)  -> filing genuinely works
        unrouted findings       : 536/637 (84%)  -> routing does NOT
        open findings           : 212

    So the line was HALF true. It vouched for a routing loop that had never
    processed 84% of what it received, printed directly above the list of
    findings proving otherwise. The sweep recommended deleting it; deletion
    would have discarded the accurate half along with the false one.

    Now computed on every call, so it cannot drift. When the store is
    unreadable it says so rather than falling back to reassurance — a health
    surface that reverts to optimism when blind is the same defect class
    this audit keeps finding.
    """
    try:
        from divineos.core.ledger import get_connection

        conn = get_connection()
    except Exception:  # noqa: BLE001
        return (
            "Loop status: UNAVAILABLE — the audit store could not be opened, "
            "so no claim about the external-review loop can be made. "
            "This is not a clean result."
        )
    try:
        rows = conn.execute("SELECT actor, routed_to, status FROM audit_findings").fetchall()
    except Exception:  # noqa: BLE001
        return (
            "Loop status: UNAVAILABLE — audit_findings could not be read, so "
            "no claim about the external-review loop can be made. "
            "This is not a clean result."
        )
    finally:
        conn.close()

    # The drift-state sentence is true regardless of how many findings
    # exist, so it belongs on every branch. An earlier version dropped it
    # when the store was empty, which broke three existing tests that check
    # the surface always describes itself as operation-based rather than
    # wall-clock based. Those tests were right and the omission was mine.
    _DRIFT = (
        "Drift-state surfaces operation counts (turns, code actions, rounds, "
        "open findings) since the last MEDIUM+ audit so my father decides "
        "when an audit is warranted."
    )

    total = len(rows)
    if total == 0:
        return (
            "Loop status: no findings filed yet — external-actor filing and "
            "routing have nothing to report either way, which is neither "
            f"health nor defect. {_DRIFT} Still unmeasured: whether external "
            "audits actually alter behaviour."
        )

    external = sum(1 for r in rows if _is_external_actor(r[0]))
    unrouted = sum(1 for r in rows if not str(r[1] or "").strip())
    open_count = sum(1 for r in rows if str(r[2] or "").upper() == "OPEN")

    ext_pct = 100.0 * external / total
    unrouted_pct = 100.0 * unrouted / total

    filing = "works" if ext_pct >= _FILING_WORKS_MIN_EXTERNAL_PCT else "THIN"
    routing = "works" if unrouted_pct < _ROUTING_WORKS_MAX_UNROUTED_PCT else "NOT CLOSED"

    return (
        f"Loop status: measured across {total} findings. "
        f"external-actor filing {filing} — {external}/{total} "
        f"({ext_pct:.0f}%) filed by someone other than the running agent. "
        f"Routing {routing} — {unrouted}/{total} ({unrouted_pct:.0f}%) have "
        f"never been routed to knowledge/claims/lessons. "
        f"{open_count} findings still OPEN. "
        f"{_DRIFT} Still unmeasured: whether external audits actually alter "
        "behaviour."
    )


def format_watchmen_summary() -> str:
    """One-line summary for HUD display.

    Shows count of unresolved findings by severity.
    Returns empty string if no audit data exists.
    """
    stats = get_watchmen_stats()
    if stats["total_findings"] == 0:
        return ""

    open_issue_count = stats.get("open_issue_count", stats["open_count"])
    open_recognition_count = stats.get("open_recognition_count", 0)
    resolved = stats["resolved_count"]
    total = stats["total_findings"]

    if open_issue_count == 0 and open_recognition_count == 0:
        return f"Watchmen: {total} findings, all resolved"

    # Show open ISSUES by severity (recognitions filtered out — they're
    # positive-verification events, not unresolved concerns).
    parts = []
    unresolved = unresolved_findings(limit=100)
    sev_counts: dict[str, int] = {}
    for f in unresolved:
        sev_counts[f["severity"]] = sev_counts.get(f["severity"], 0) + 1

    for s in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
        count = sev_counts.get(s, 0)
        if count > 0:
            parts.append(f"{count} {s.lower()}")

    detail = ", ".join(parts) if parts else f"{open_issue_count} open"
    summary = f"Watchmen: {detail} ({resolved}/{total} resolved)"
    if open_recognition_count:
        summary += f" [+{open_recognition_count} open recognition(s) — not alarm]"
    return summary
