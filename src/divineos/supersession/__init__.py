"""DivineOS Supersession & Contradiction Resolution System.

This module provides contradiction detection, resolution, and querying capabilities
for the DivineOS ledger system. It enables the system to detect when two facts
contradict each other, resolve the contradiction, and maintain a queryable history
of fact evolution.

Key Components:
- ContradictionDetector: Detects contradictions between facts
- ResolutionEngine: Resolves contradictions and creates SUPERSESSION events
- QueryInterface: Queries facts, history, and supersession chains

Usage:
    from divineos.supersession import ContradictionDetector, ResolutionEngine, QueryInterface

    detector = ContradictionDetector()
    engine = ResolutionEngine()
    query = QueryInterface()

    # Detect contradiction
    contradiction = detector.detect_contradiction(fact1, fact2)

    # Resolve contradiction
    if contradiction:
        supersession = engine.resolve_contradiction(contradiction)

    # Query current truth
    current_fact = query.query_current_truth("mathematical_operation", "17_times_23")
"""

from .contradiction_detector import (
    ContradictionDetector,
    Contradiction,
    ContradictionSeverity,
)
from .resolution_engine import (
    ResolutionEngine,
    SupersessionEvent,
    ResolutionStrategy,
)
from .query_interface import (
    QueryInterface,
    FactWithHistory,
)
from .event_integration import (
    create_supersession_event,
    emit_supersession_event,
    register_supersession_listener,
    SupersessionEventData,
)
from .clarity_integration import (
    handle_unresolved_contradiction,
    create_contradiction_violation,
)
from .ledger_integration import (
    LedgerIntegration,
    get_ledger_integration,
    store_fact,
    store_supersession_event,
    query_facts,
    query_supersession_events,
)

# Ensure all components are available
__version__ = "0.1.0"

__all__ = [
    "ContradictionDetector",
    "Contradiction",
    "ContradictionSeverity",
    "ResolutionEngine",
    "SupersessionEvent",
    "ResolutionStrategy",
    "QueryInterface",
    "FactWithHistory",
    "create_supersession_event",
    "emit_supersession_event",
    "register_supersession_listener",
    "SupersessionEventData",
    "handle_unresolved_contradiction",
    "create_contradiction_violation",
    "LedgerIntegration",
    "get_ledger_integration",
    "store_fact",
    "store_supersession_event",
    "query_facts",
    "query_supersession_events",
]
