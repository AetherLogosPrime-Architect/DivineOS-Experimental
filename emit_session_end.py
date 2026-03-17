#!/usr/bin/env python
"""Emit SESSION_END event for the current session."""

import sys
sys.path.insert(0, 'src')

from divineos.event_emission import emit_session_end

print("Emitting SESSION_END event...")
try:
    event_id = emit_session_end()
    print(f"✓ SESSION_END event emitted: {event_id}")
except Exception as e:
    print(f"✗ Failed to emit SESSION_END: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
