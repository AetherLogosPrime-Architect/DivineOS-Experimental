#!/usr/bin/env python3
"""Show Grok recent events with full details."""

from divineos.core.ledger import init_db, _get_connection
from divineos.core.consolidation import init_knowledge_table
import sqlite3
import json

# Initialize
init_db()
init_knowledge_table()

conn = _get_connection()
conn.row_factory = sqlite3.Row

# Get last 5 events with full payload
cursor = conn.execute('''
    SELECT event_id, event_type, timestamp, actor, payload, content_hash
    FROM system_events 
    ORDER BY timestamp DESC 
    LIMIT 5
''')
events = [dict(row) for row in cursor.fetchall()]

print('=== RECENT EVENTS (Last 5) ===\n')
for i, evt in enumerate(events, 1):
    print(f'{i}. Event ID: {evt["event_id"]}')
    print(f'   Type: {evt["event_type"]}')
    print(f'   Actor: {evt["actor"]}')
    print(f'   Timestamp: {evt["timestamp"]}')
    print(f'   Hash: {evt["content_hash"][:16]}...')
    try:
        payload = json.loads(evt['payload'])
        print('   Payload:')
        for key, val in payload.items():
            if isinstance(val, str) and len(val) > 60:
                print(f'     {key}: {val[:60]}...')
            else:
                print(f'     {key}: {val}')
    except:
        print(f'   Payload: {evt["payload"][:100]}...')
    print()

conn.close()
