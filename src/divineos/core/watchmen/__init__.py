"""Watchmen — External Validation as a Native Runtime Capability.

The council audit process (25 experts, structured findings, severity ratings)
was too valuable to leave as a manual one-off. This module makes it a
permanent part of the OS: accept structured audit findings, route them to
knowledge/claims/lessons, and surface unresolved issues in the briefing.

Who watches the watchmen? External auditors do — through this module.
The OS itself never triggers audits. Only external actors (CLI, user,
collaborating AI) can submit findings. Three structural guarantees:
  1. Actor validation — internal actors rejected at store level
  2. CLI-only entry — no scheduled hooks or pipeline phases call submit
  3. No self-trigger — the OS reads findings but never creates them
"""

from divineos.core.watchmen._schema import init_watchmen_tables
from divineos.core.watchmen.cadence import (
    CADENCE_THRESHOLD_DAYS,
    cadence_status_line,
    days_since_last_audit,
    format_cadence_warning,
    is_overdue,
    last_external_audit_ts,
)
from divineos.core.watchmen.router import route_finding, route_round
from divineos.core.watchmen.store import (
    get_finding,
    get_round,
    list_findings,
    list_rounds,
    resolve_finding,
    submit_finding,
    submit_round,
)
from divineos.core.watchmen.summary import (
    format_watchmen_summary,
    get_watchmen_stats,
    unresolved_findings,
    watchmen_loop_status,
)

__all__ = [
    "CADENCE_THRESHOLD_DAYS",
    "cadence_status_line",
    "days_since_last_audit",
    "format_cadence_warning",
    "format_watchmen_summary",
    "get_finding",
    "get_round",
    "get_watchmen_stats",
    "init_watchmen_tables",
    "is_overdue",
    "last_external_audit_ts",
    "list_findings",
    "list_rounds",
    "resolve_finding",
    "route_finding",
    "route_round",
    "submit_finding",
    "submit_round",
    "unresolved_findings",
    "watchmen_loop_status",
]
