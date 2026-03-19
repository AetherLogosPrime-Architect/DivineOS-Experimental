#!/usr/bin/env python
"""Simple test to verify events are being stored."""

from divineos.core.ledger import init_db, log_event, get_events
from divineos.core.session_manager import initialize_session, clear_session

# Initialize database
init_db()

# Initialize session
session_id = initialize_session()
print(f"Session ID: {session_id}")

# Log a simple event
event_id = log_event(
    event_type="TEST_EVENT",
    actor="test",
    payload={"session_id": session_id, "test": "data"},
    validate=False
)
print(f"Logged event: {event_id}")

# Retrieve events
events = get_events(limit=10)
print(f"\nTotal events: {len(events)}")
print("\nLast 3 events:")
for event in events[-3:]:
    print(f"  Type: {event['event_type']}, Session: {event.get('payload', {}).get('session_id')}")

# Clean up
clear_session()
