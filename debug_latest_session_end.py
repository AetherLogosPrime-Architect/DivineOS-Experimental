#!/usr/bin/env python
"""Debug script to see the latest SESSION_END event and its counts."""

from divineos.ledger import get_events

events = get_events(limit=10000)
print(f'Total events in database: {len(events)}\n')

# Find the most recent SESSION_END
for e in reversed(events):
    if e['event_type'] == 'SESSION_END':
        print(f'Most recent SESSION_END:')
        print(f'  Event ID: {e["event_id"]}')
        print(f'  Timestamp: {e["timestamp"]}')
        payload = e.get('payload', {})
        print(f'  Session ID: {payload.get("session_id")}')
        print(f'  Message Count: {payload.get("message_count")}')
        print(f'  Tool Call Count: {payload.get("tool_call_count")}')
        print(f'  Tool Result Count: {payload.get("tool_result_count")}')
        
        # Now check how many events actually have this session_id
        session_id = payload.get('session_id')
        session_events = [e for e in events if e.get('payload', {}).get('session_id') == session_id]
        print(f'\n  Events with this session_id: {len(session_events)}')
        for evt in session_events:
            print(f'    - {evt["event_type"]}')
        break
