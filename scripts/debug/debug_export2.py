#!/usr/bin/env python
"""Debug script to check event types in the ledger."""

from divineos.ledger import get_events, _get_connection
import json

# Get all events
all_events = get_events(limit=10000)

# Get most recent non-SESSION_END event
conn = _get_connection()
cursor = conn.execute(
    "SELECT payload FROM system_events WHERE event_type != 'SESSION_END' ORDER BY timestamp DESC LIMIT 1"
)
row = cursor.fetchone()
if row:
    payload = json.loads(row[0])
    session_id = payload.get('session_id')
    
    # Filter events by this session_id
    session_events = [e for e in all_events if e.get('payload', {}).get('session_id') == session_id]
    print(f'Events for session {session_id}:')
    for e in session_events:
        print(f"  Type: {e.get('event_type')}, Content: {e.get('payload', {}).get('content', '')[:50]}")
conn.close()
