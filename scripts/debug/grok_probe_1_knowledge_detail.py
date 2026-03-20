#!/usr/bin/env python3
"""Probe 1: Show detailed knowledge entry."""

from divineos.core.ledger import init_db, _get_connection
from divineos.core.consolidation import init_knowledge_table
import sqlite3
import json

# Initialize
init_db()
init_knowledge_table()

conn = _get_connection()
conn.row_factory = sqlite3.Row

# Get the specific knowledge entry
knowledge_id = '3034df54-b9ef-4076-a870-9003bebef953'
cursor = conn.execute('''
    SELECT * FROM knowledge WHERE knowledge_id = ?
''', (knowledge_id,))
entry = cursor.fetchone()

if entry:
    entry_dict = dict(entry)
    print('=== KNOWLEDGE ENTRY DETAIL ===\n')
    print(f'Knowledge ID: {entry_dict["knowledge_id"]}')
    print(f'Type: {entry_dict["knowledge_type"]}')
    print(f'Content: {entry_dict["content"]}')
    print(f'Confidence: {entry_dict["confidence"]}')
    print(f'Source: {entry_dict["source"]}')
    print(f'Maturity: {entry_dict["maturity"]}')
    print(f'\nTags: {json.loads(entry_dict["tags"])}')
    print(f'Source Events: {json.loads(entry_dict["source_events"])}')
    print(f'\nSuperseded By: {entry_dict["superseded_by"]}')
    print(f'Access Count: {entry_dict["access_count"]}')
    print(f'\nCreated At: {entry_dict["created_at"]}')
    print(f'Updated At: {entry_dict["updated_at"]}')
    print(f'Content Hash: {entry_dict["content_hash"]}')
    print(f'\nCorroboration Count: {entry_dict["corroboration_count"]}')
    print(f'Contradiction Count: {entry_dict["contradiction_count"]}')
else:
    print(f'Knowledge entry {knowledge_id} not found')

conn.close()
