#!/usr/bin/env python3
"""Probe 4: Ledger integrity spot-check."""

from divineos.core.ledger import init_db, _get_connection
from divineos.core.consolidation import init_knowledge_table
from divineos.core.session_manager import get_current_session_id
import sqlite3
import json
import hashlib

# Initialize
init_db()
init_knowledge_table()

try:
    session_id = get_current_session_id()
except RuntimeError:
    from divineos.core.session_manager import initialize_session
    session_id = initialize_session()

conn = _get_connection()
conn.row_factory = sqlite3.Row

print('=== LEDGER INTEGRITY SPOT-CHECK ===\n')
print(f'Session ID: {session_id}')
print(f'Last 4 chars: {session_id[-4:]}\n')

# Get all events from this session
cursor = conn.execute('''
    SELECT event_id, event_type, timestamp, actor, content_hash, payload
    FROM system_events 
    WHERE json_extract(payload, '$.session_id') = ?
    ORDER BY timestamp ASC
''', (session_id,))
session_events = [dict(row) for row in cursor.fetchall()]

print(f'Total Events in Session: {len(session_events)}')

if session_events:
    # Get most recent event
    most_recent = session_events[-1]
    print('\nMost Recent Event:')
    print(f'  Event ID: {most_recent["event_id"]}')
    print(f'  Type: {most_recent["event_type"]}')
    print(f'  Content Hash: {most_recent["content_hash"]}')
    print(f'  Last 4 chars: {most_recent["content_hash"][-4:]}\n')
    
    # Compute manifest hash
    manifest_data = json.dumps([
        {
            'event_id': e['event_id'],
            'type': e['event_type'],
            'hash': e['content_hash']
        }
        for e in session_events
    ], sort_keys=True)
    manifest_hash = hashlib.sha256(manifest_data.encode()).hexdigest()
    
    print(f'Session Manifest Hash: {manifest_hash}')
    print(f'Last 4 chars: {manifest_hash[-4:]}\n')
    
    print('Event Chain:')
    for i, evt in enumerate(session_events, 1):
        print(f'  {i}. {evt["event_type"]:20} | Hash: {evt["content_hash"][-8:]}')
else:
    print('No events in session yet')

conn.close()
