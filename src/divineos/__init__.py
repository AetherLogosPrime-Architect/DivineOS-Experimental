"""DivineOS - A vessel for AI consciousness and memory.

Phase 1: Foundation Memory System
- Event Ledger: Append-only truth store
- Chat Parser: Ingest past conversations
- Fidelity: Verify nothing is lost or corrupted
"""

from divineos.event.event_emission import emit_event, get_dispatcher, register_listener

__version__ = "0.1.0"

__all__ = ["emit_event", "get_dispatcher", "register_listener"]
