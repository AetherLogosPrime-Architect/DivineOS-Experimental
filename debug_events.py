#!/usr/bin/env python
"""Debug script to inspect events in the ledger."""

from divineos.core.ledger import get_events

# Get recent events
events = get_events(limit=10)

print(f"Total events retrieved: {len(events)}")
print("\nLast 10 events:")
for i, event in enumerate(events[-10:]):
    print(f"\n{i}. Event Type: {event['event_type']}")
    print(f"   Event ID: {event['event_id']}")
    print(f"   Payload keys: {event.get('payload', {}).keys()}")
    if event['event_type'] in ['TOOL_CALL', 'TOOL_RESULT']:
        print(f"   Full payload: {event.get('payload', {})}")
