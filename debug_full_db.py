#!/usr/bin/env python
"""Debug script to see ALL events in the database."""

from divineos.ledger import get_events

events = get_events(limit=10000)
print(f'Total events in database: {len(events)}\n')
print('ALL events (oldest to newest):')
for i, e in enumerate(events):
    payload = e.get('payload', {})
    session_id = payload.get('session_id')
    timestamp = payload.get('timestamp', 'N/A')
    print(f'{i}. Type: {e["event_type"]:<15} Session ID: {session_id} Timestamp: {timestamp}')
