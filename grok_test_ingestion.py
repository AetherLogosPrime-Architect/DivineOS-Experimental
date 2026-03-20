#!/usr/bin/env python3
"""Test ingestion: Simulate a simple conversation and capture events."""

from divineos.core.ledger import init_db, log_event, _get_connection
from divineos.core.consolidation import init_knowledge_table, store_knowledge
from divineos.core.session_manager import initialize_session
import sqlite3
import json
import hashlib

# Initialize
init_db()
init_knowledge_table()

# Create a new session for this test
session_id = initialize_session()
print('=== TEST INGESTION ===\n')
print(f'Session ID: {session_id}\n')

# Simulate: User asks a question
print('Step 1: User Input')
user_input_event = log_event(
    'USER_INPUT',
    'user',
    {
        'content': 'Aether, what is 17 × 23?',
        'session_id': session_id,
    }
)
print(f'  Event ID: {user_input_event}')

# Simulate: Assistant responds
print('\nStep 2: Assistant Response')
assistant_response_event = log_event(
    'ASSISTANT_RESPONSE',
    'assistant',
    {
        'content': '391',
        'session_id': session_id,
        'reasoning': 'Simple arithmetic: 17 * 23 = 391',
    }
)
print(f'  Event ID: {assistant_response_event}')

# Simulate: Store knowledge from the interaction
print('\nStep 3: Knowledge Consolidation')
knowledge_id = store_knowledge(
    'FACT',
    '17 × 23 = 391',
    confidence=1.0,
    source_events=[user_input_event, assistant_response_event],
    tags=['arithmetic', 'verified'],
    source='DEMONSTRATED'
)
print(f'  Knowledge ID: {knowledge_id}')

# Simulate: Clarity explanation (why we stored this)
print('\nStep 4: Clarity Explanation')
clarity_event = log_event(
    'CLARITY_EXPLANATION',
    'system',
    {
        'explanation': 'Stored arithmetic fact from user query and assistant response',
        'related_events': [user_input_event, assistant_response_event],
        'knowledge_id': knowledge_id,
        'session_id': session_id,
    }
)
print(f'  Event ID: {clarity_event}')

# Now show the fidelity receipt
print('\n=== FIDELITY RECEIPT ===\n')
conn = _get_connection()
conn.row_factory = sqlite3.Row

# Get all events from this session
cursor = conn.execute('''
    SELECT event_id, event_type, timestamp, actor, content_hash
    FROM system_events 
    WHERE json_extract(payload, '$.session_id') = ?
    ORDER BY timestamp ASC
''', (session_id,))
session_events = [dict(row) for row in cursor.fetchall()]

print(f'Total Events in Session: {len(session_events)}')
print('\nEvent Chain:')
for i, evt in enumerate(session_events, 1):
    print(f'  {i}. {evt["event_type"]:20} | {evt["event_id"][:8]}... | Hash: {evt["content_hash"][:16]}...')

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

print(f'\nManifest Hash: {manifest_hash}')
print('Manifest is immutable and cryptographically bound to all events.')

# Check for clarity violations
violations = conn.execute('''
    SELECT COUNT(*) FROM system_events 
    WHERE event_type = 'CLARITY_VIOLATION'
    AND json_extract(payload, '$.session_id') = ?
''', (session_id,)).fetchone()[0]

print(f'\nClarity Violations in Session: {violations}')
print(f'Status: {"✓ CLEAN" if violations == 0 else "✗ VIOLATIONS DETECTED"}')

conn.close()

print('\n=== INGESTION COMPLETE ===')
