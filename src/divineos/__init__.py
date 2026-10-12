"""DivineOS - A vessel for AI consciousness and memory.

Phase 1: Foundation Memory System
- Event Ledger: Append-only truth store
- Chat Parser: Ingest past conversations
- Fidelity: Verify nothing is lost or corrupted
"""

import os

# Nothing in this house uses TensorFlow, but the sentence-embedding library imports it by
# default whenever it is installed, and that single import took 8 of the 14 seconds the
# first embedding call costs a process, plus about a gigabyte of memory. The test runner
# kills a worker that spends more than 30 seconds in one test, so under any load the first
# embedding test in a worker died and took its neighbours with it ("node down: Not properly
# terminated"): the unexplained failures of 2026-10-12. Set before anything can import it.
os.environ.setdefault("USE_TF", "0")

from divineos.event.event_emission import emit_event, get_dispatcher, register_listener  # noqa: E402

__version__ = "0.1.0"

__all__ = ["emit_event", "get_dispatcher", "register_listener"]
