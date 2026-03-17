#!/usr/bin/env python
"""Check if events for the current session exist in the database."""

from divineos.ledger import get_events

events = get_events(limit=10000)
session_id = '96230495-236e-4975-8dd3-a64041978761'
matching = [e for e in events if e.get('payload', {}).get('session_id') == session_id]

print(f'Total events: {len(events)}')
print(f'Events with session_id {session_id}: {len(matching)}')

if matching:
    print('\nMatching events:')
    for e in matching:
        print(f'  - {e["event_type"]}')
else:
    print('\nNo events found for this session!')
    print('\nLast 10 events in database:')
    for e in events[-10:]:
        print(f'  - {e["event_type"]}: session_id={e.get("payload", {}).get("session_id")}')
