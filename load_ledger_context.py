#!/usr/bin/env python
"""Load and analyze ledger context."""

import sys
sys.path.insert(0, 'src')

from divineos.agent_integration.memory_monitor import get_memory_monitor

monitor = get_memory_monitor('foundation-ledger-architecture-fix')
context = monitor.load_session_context()

print("=== LEDGER CONTEXT ===")
print(f"Session ID: {monitor.session_id}")
print(f"Current tokens: {monitor.current_tokens}")
print(f"Previous work items loaded: {len(context) if context else 0}")

if context:
    print("\nRecent work:")
    items = list(context.items()) if hasattr(context, 'items') else context
    for i, item in enumerate(items[:5]):
        print(f"  {i+1}. {item}")
