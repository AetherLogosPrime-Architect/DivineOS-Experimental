#!/usr/bin/env python
"""Debug script to understand why emit_session_end reports zero events."""

from divineos.ledger import get_events

events = get_events(limit=10000)
print(f'Total events in database: {len(events)}')
print('\nLast 5 events:')
for i, e in enumerate(events[-5:]):
    payload = e.get('payload', {})
    session_id = payload.get('session_id')
    print(f'{i}. Type: {e["event_type"]:<15} Session ID: {session_id}')
    print(f'   Payload keys: {list(payload.keys())}')

# Now test the filtering logic
print('\n\nTesting filtering logic:')
if events:
    # Get the most recent non-SESSION_END event's session_id
    for e in reversed(events):
        if e['event_type'] != 'SESSION_END':
            test_session_id = e.get('payload', {}).get('session_id')
            print(f'Most recent non-SESSION_END session_id: {test_session_id}')
            break
    
    # Try the filtering
    session_events = [e for e in events if e.get('payload', {}).get('session_id') == test_session_id]
    print(f'Events matching this session_id: {len(session_events)}')
    for e in session_events:
        print(f'  - {e["event_type"]}')
