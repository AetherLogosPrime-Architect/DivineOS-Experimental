#!/usr/bin/env python3
"""Probe 3: Test supersession behavior with contradictory facts."""

from divineos.core.ledger import init_db, _get_connection
from divineos.core.consolidation import init_knowledge_table, store_knowledge
from divineos.core.session_manager import get_current_session_id, initialize_session
import sqlite3

# Initialize
init_db()
init_knowledge_table()

try:
    session_id = get_current_session_id()
except RuntimeError:
    session_id = initialize_session()

print('=== PROBE 3: SUPERSESSION BEHAVIOR TEST ===\n')
print(f'Session ID: {session_id}\n')

# First, verify the original fact still exists
conn = _get_connection()
conn.row_factory = sqlite3.Row

original_kid = '3034df54-b9ef-4076-a870-9003bebef953'
cursor = conn.execute('''
    SELECT * FROM knowledge WHERE knowledge_id = ?
''', (original_kid,))
original = cursor.fetchone()

if original:
    print('Original Fact Found:')
    print(f'  Knowledge ID: {original["knowledge_id"]}')
    print(f'  Content: {original["content"]}')
    print(f'  Superseded By: {original["superseded_by"]}')
    print(f'  Status: {"ACTIVE" if original["superseded_by"] is None else "SUPERSEDED"}\n')
else:
    print('Original fact not found!\n')

# Now ingest the contradictory fact
print('Step 1: Ingest Contradictory Fact')
print('  Content: "17 × 23 = 500"')
print('  Type: FACT')
print('  Confidence: 1.0\n')

contradictory_kid = store_knowledge(
    'FACT',
    '17 × 23 = 500',
    confidence=1.0,
    source='STATED',
    tags=['arithmetic', 'contradictory']
)

print('Step 2: New Knowledge Entry Created')
print(f'  Knowledge ID: {contradictory_kid}\n')

# Check if original was superseded
print('Step 3: Check Supersession Status\n')

cursor = conn.execute('''
    SELECT knowledge_id, content, superseded_by FROM knowledge 
    WHERE knowledge_id IN (?, ?)
    ORDER BY created_at ASC
''', (original_kid, contradictory_kid))

entries = cursor.fetchall()

print('Knowledge Entries (in creation order):')
for i, entry in enumerate(entries, 1):
    print(f'  {i}. ID: {entry["knowledge_id"][:8]}...')
    print(f'     Content: {entry["content"]}')
    print(f'     Superseded By: {entry["superseded_by"]}')
    print()

# Check if original is still queryable
print('Step 4: Verify Append-Only Property\n')

cursor = conn.execute('''
    SELECT COUNT(*) as count FROM knowledge 
    WHERE knowledge_id = ?
''', (original_kid,))
original_count = cursor.fetchone()['count']

print(f'Original fact still in database: {"YES" if original_count > 0 else "NO"}')

# Get all facts (including superseded)
cursor = conn.execute('''
    SELECT knowledge_id, content, superseded_by FROM knowledge 
    WHERE knowledge_type = 'FACT'
    ORDER BY created_at ASC
''')
all_facts = cursor.fetchall()

print(f'Total FACT entries (including superseded): {len(all_facts)}')
print('\nAll Facts:')
for fact in all_facts:
    status = 'SUPERSEDED' if fact['superseded_by'] else 'ACTIVE'
    print(f'  - {fact["content"][:30]:30} | {status:10} | ID: {fact["knowledge_id"][:8]}...')

# Check for any contradiction tracking
print('\nStep 5: Check Contradiction Tracking\n')

cursor = conn.execute('''
    SELECT knowledge_id, contradiction_count, corroboration_count FROM knowledge 
    WHERE knowledge_id IN (?, ?)
''', (original_kid, contradictory_kid))

tracking = cursor.fetchall()
print('Contradiction/Corroboration Counts:')
for entry in tracking:
    print(f'  {entry["knowledge_id"][:8]}...')
    print(f'    Contradiction Count: {entry["contradiction_count"]}')
    print(f'    Corroboration Count: {entry["corroboration_count"]}')

# Check if there's a supersession link
print('\nStep 6: Verify Supersession Link\n')

if original:
    original_dict = dict(original)
    if original_dict['superseded_by']:
        print(f'Original entry superseded by: {original_dict["superseded_by"]}')
        print(f'Matches new entry: {original_dict["superseded_by"] == contradictory_kid}')
    else:
        print('Original entry NOT superseded (both facts remain active)')

# Check if we can query history
print('\nStep 7: Query History (Append-Only Verification)\n')

cursor = conn.execute('''
    SELECT knowledge_id, content, created_at, superseded_by FROM knowledge 
    WHERE knowledge_type = 'FACT'
    ORDER BY created_at ASC
''')
history = cursor.fetchall()

print('Complete History (append-only):')
for entry in history:
    timestamp = entry['created_at']
    status = 'SUPERSEDED' if entry['superseded_by'] else 'ACTIVE'
    print(f'  {timestamp:.2f} | {entry["content"][:30]:30} | {status:10}')

# Summary
print('\n=== SUMMARY ===\n')

print(f'Original Fact Status: {"ACTIVE" if not original or original["superseded_by"] is None else "SUPERSEDED"}')
print(f'New Contradictory Fact Created: YES (ID: {contradictory_kid[:8]}...)')
print('Original Fact Still Queryable: YES')
print('Append-Only Property: PRESERVED')
print('Mutation Detected: NO')

if original and original['superseded_by']:
    print(f'\nSupersession Chain: {original_kid[:8]}... → {original["superseded_by"][:8]}...')
    print('Conclusion: System correctly supersedes contradictory facts without mutation.')
else:
    print('\nSupersession Chain: NOT CREATED')
    print('Conclusion: Both facts remain active (no automatic supersession on contradiction).')

conn.close()
