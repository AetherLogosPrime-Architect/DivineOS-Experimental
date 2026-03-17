#!/usr/bin/env python
"""Debug script to check all sessions."""

from divineos.ledger import get_events
import json

# Get all events
all_events = get_events(limit=10000)

# Group by session_id
sessions = {}
for e in all_events:
    sid = e.get('payload', {}).get('session_id')
    if sid:
        if sid not in sessions:
            sessions[sid] = []
        sessions[sid].append(e)

print(f'Total sessions: {len(sessions)}')
for sid, events in sorted(sessions.items(), key=lambda x: len(x[1]), reverse=True):
    print(f'\nSession {sid}: {len(events)} events')
    event_types = {}
    for e in events:
        et = e.get('event_type')
        event_types[et] = event_types.get(et, 0) + 1
    print(f'  Types: {event_types}')
    
    # Show USER_INPUT events
    user_inputs = [e for e in events if e.get('event_type') == 'USER_INPUT']
    if user_inputs:
        print(f'  USER_INPUT events:')
        for e in user_inputs:
            content = e.get('payload', {}).get('content', '')[:50]
            print(f'    - {content}')
