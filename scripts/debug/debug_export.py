#!/usr/bin/env python
"""Debug script to check why export_current_session_to_jsonl is failing."""

from divineos.ledger import get_events, _get_connection
import json

# Get all events
all_events = get_events(limit=10000)
print(f'Total events in ledger: {len(all_events)}')

# Get most recent non-SESSION_END event
conn = _get_connection()
cursor = conn.execute(
    "SELECT payload FROM system_events WHERE event_type != 'SESSION_END' ORDER BY timestamp DESC LIMIT 1"
)
row = cursor.fetchone()
if row:
    payload = json.loads(row[0])
    session_id = payload.get('session_id')
    print(f'Most recent session_id: {session_id}')
    
    # Filter events by this session_id
    session_events = [e for e in all_events if e.get('payload', {}).get('session_id') == session_id]
    print(f'Events for this session: {len(session_events)}')
    
    # Show all session_ids in ledger
    all_session_ids = set()
    for e in all_events:
        sid = e.get('payload', {}).get('session_id')
        if sid:
            all_session_ids.add(sid)
    print(f'Unique session_ids in ledger: {len(all_session_ids)}')
    print(f'Session IDs: {list(all_session_ids)[:10]}')
    
    # Show event types
    event_types = {}
    for e in all_events:
        et = e.get('event_type')
        event_types[et] = event_types.get(et, 0) + 1
    print(f'Event types: {event_types}')
else:
    print('No events found')
conn.close()
