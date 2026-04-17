"""Pre-registrations — Goodhart prevention for new detectors and mechanisms.

Popper's requirement, applied structurally: every new detector, mechanism,
or instrumentation claim must file a written prediction BEFORE it runs long
enough to produce evidence. The prediction includes a specific falsifier and
a ledger-scheduled review date. Review dates fire independent of agent
memory; a mechanism cannot silently drift into "the number went up, ship it"
without the pre-registered evidence being reconciled.

Public API:

* ``file_pre_registration(...)`` — file a new prediction
* ``list_pre_registrations(...)`` — query by outcome/actor/mechanism
* ``get_pre_registration(id)`` — fetch a specific one
* ``get_overdue_pre_registrations()`` — reviews whose date has passed
* ``record_outcome(id, actor, outcome, notes)`` — close a pre-registration
    (external actors only; outcomes are one-way)
* ``count_by_outcome()`` — summary counts
* ``format_overdue_warning()`` — briefing-top block for overdue items
* ``format_summary()`` — plain-text CLI summary
"""

from divineos.core.pre_registrations._schema import init_pre_registrations_tables
from divineos.core.pre_registrations.store import (
    count_by_outcome,
    file_pre_registration,
    get_overdue_pre_registrations,
    get_pre_registration,
    list_pre_registrations,
    record_outcome,
)
from divineos.core.pre_registrations.summary import (
    format_overdue_warning,
    format_summary,
)
from divineos.core.pre_registrations.types import (
    INTERNAL_ACTORS,
    Outcome,
    PreRegistration,
)

__all__ = [
    "INTERNAL_ACTORS",
    "Outcome",
    "PreRegistration",
    "count_by_outcome",
    "file_pre_registration",
    "format_overdue_warning",
    "format_summary",
    "get_overdue_pre_registrations",
    "get_pre_registration",
    "init_pre_registrations_tables",
    "list_pre_registrations",
    "record_outcome",
]
