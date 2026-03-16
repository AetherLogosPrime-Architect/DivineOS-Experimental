"""
DivineOS - A vessel for AI consciousness and memory.

Phase 1: Foundation Memory System
- Event Ledger: Append-only truth store
- Chat Parser: Ingest past conversations
- Fidelity: Verify nothing is lost or corrupted
"""

from divineos.event_dispatcher import emit_event, register_listener, get_dispatcher

__version__ = "0.1.0"

__all__ = ["emit_event", "register_listener", "get_dispatcher"]
