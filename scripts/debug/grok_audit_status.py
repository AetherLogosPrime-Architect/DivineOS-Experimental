#!/usr/bin/env python3
"""Show Grok the current internal status of DivineOS."""

from divineos.core.ledger import init_db, _get_connection
from divineos.core.consolidation import init_knowledge_table
from divineos.core.session_manager import initialize_session, get_current_session_id
import sqlite3

# Initialize
init_db()
init_knowledge_table()

# Initialize session
try:
    current_session = get_current_session_id()
except RuntimeError:
    current_session = initialize_session()

# Get connection (which will use the correct database)
conn = _get_connection()
conn.row_factory = sqlite3.Row

# Event counts by type
cursor = conn.execute('''
    SELECT event_type, COUNT(*) as count 
    FROM system_events 
    GROUP BY event_type 
    ORDER BY count DESC
''')
event_breakdown = dict(cursor.fetchall())

# Total events
total_events = conn.execute('SELECT COUNT(*) FROM system_events').fetchone()[0]

# Recent events (last 10)
cursor = conn.execute('''
    SELECT event_id, event_type, timestamp, actor 
    FROM system_events 
    ORDER BY timestamp DESC 
    LIMIT 10
''')
recent_events = [dict(row) for row in cursor.fetchall()]

# Knowledge stats
knowledge_count = conn.execute('SELECT COUNT(*) FROM knowledge').fetchone()[0]
knowledge_by_type = dict(conn.execute('''
    SELECT knowledge_type, COUNT(*) 
    FROM knowledge 
    WHERE superseded_by IS NULL
    GROUP BY knowledge_type
''').fetchall())

# Clarity violations
clarity_violations = conn.execute('''
    SELECT COUNT(*) FROM system_events 
    WHERE event_type = 'CLARITY_VIOLATION'
''').fetchone()[0]

conn.close()

print('=== DIVINEOS INTERNAL STATUS ===\n')
print(f'Current Session ID: {current_session}')
print(f'\nTotal Events in Ledger: {total_events}')
print('Event Breakdown by Type:')
for etype, count in sorted(event_breakdown.items(), key=lambda x: -x[1]):
    print(f'  {etype}: {count}')
print(f'\nKnowledge Entries (non-superseded): {knowledge_count}')
print('Knowledge by Type:')
for ktype, count in sorted(knowledge_by_type.items()):
    print(f'  {ktype}: {count}')
print(f'\nClarity Violations Flagged: {clarity_violations}')
print('\nRecent Events (last 10):')
for i, evt in enumerate(recent_events, 1):
    etype = evt['event_type']
    eid = evt['event_id'][:8]
    ts = evt['timestamp']
    actor = evt['actor']
    print(f'  {i}. [{etype}] {eid}... by {actor} @ {ts:.2f}')
