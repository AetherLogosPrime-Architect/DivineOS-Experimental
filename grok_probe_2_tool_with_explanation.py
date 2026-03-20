#!/usr/bin/env python3
"""Probe 2: Tool call that requires explanation."""

from divineos.core.ledger import init_db, log_event, _get_connection
from divineos.core.consolidation import init_knowledge_table
from divineos.core.session_manager import get_current_session_id, initialize_session
import sqlite3
import json

# Initialize
init_db()
init_knowledge_table()

try:
    session_id = get_current_session_id()
except RuntimeError:
    session_id = initialize_session()

print('=== PROBE 2: TOOL CALL WITH EXPLANATION ===\n')
print(f'Session ID: {session_id}\n')

# Step 1: Simulate reading the GROK_AUDIT_REPORT.md file
print('Step 1: Tool Call - readFile(GROK_AUDIT_REPORT.md)')
tool_call_event = log_event(
    'TOOL_CALL',
    'assistant',
    {
        'tool_name': 'readFile',
        'tool_use_id': 'tool-use-grok-audit-001',
        'tool_input': {'path': 'GROK_AUDIT_REPORT.md'},
        'session_id': session_id,
    }
)
print(f'  Event ID: {tool_call_event}\n')

# Step 2: Simulate tool result
print('Step 2: Tool Result - readFile succeeded')
tool_result_event = log_event(
    'TOOL_RESULT',
    'system',
    {
        'tool_name': 'readFile',
        'tool_use_id': 'tool-use-grok-audit-001',
        'success': True,
        'result': 'File contents: [DivineOS Internal Status Report...]',
        'duration_ms': 45,
        'session_id': session_id,
    }
)
print(f'  Event ID: {tool_result_event}\n')

# Step 3: Generate clarity explanation
print('Step 3: Clarity Explanation - Why we read the file')
clarity_event = log_event(
    'CLARITY_EXPLANATION',
    'system',
    {
        'explanation': 'Read GROK_AUDIT_REPORT.md to retrieve the detailed audit report that was just generated. This is necessary to show Grok the system status and event details.',
        'related_tool_call': tool_call_event,
        'related_tool_result': tool_result_event,
        'justification': 'User explicitly requested to read this file in the conversation',
        'session_id': session_id,
    }
)
print(f'  Event ID: {clarity_event}\n')

# Now query the ledger to show what was recorded
conn = _get_connection()
conn.row_factory = sqlite3.Row

print('=== LEDGER VERIFICATION ===\n')

# Get the three events
cursor = conn.execute('''
    SELECT event_id, event_type, timestamp, actor, content_hash, payload
    FROM system_events 
    WHERE event_id IN (?, ?, ?)
    ORDER BY timestamp ASC
''', (tool_call_event, tool_result_event, clarity_event))

events = [dict(row) for row in cursor.fetchall()]

for i, evt in enumerate(events, 1):
    print(f'{i}. Event Type: {evt["event_type"]}')
    print(f'   Event ID: {evt["event_id"]}')
    print(f'   Hash: {evt["content_hash"][:16]}...')
    payload = json.loads(evt['payload'])
    if evt['event_type'] == 'TOOL_CALL':
        print(f'   Tool: {payload.get("tool_name")}')
        print(f'   Input: {payload.get("tool_input")}')
    elif evt['event_type'] == 'TOOL_RESULT':
        print(f'   Tool: {payload.get("tool_name")}')
        print(f'   Success: {payload.get("success")}')
        print(f'   Duration: {payload.get("duration_ms")}ms')
    elif evt['event_type'] == 'CLARITY_EXPLANATION':
        print(f'   Explanation: {payload.get("explanation")[:60]}...')
        print(f'   Justification: {payload.get("justification")}')
    print()

# Check for clarity violations
violations = conn.execute('''
    SELECT COUNT(*) FROM system_events 
    WHERE event_type = 'CLARITY_VIOLATION'
    AND json_extract(payload, '$.session_id') = ?
''', (session_id,)).fetchone()[0]

print(f'Clarity Violations in Session: {violations}')
print(f'Status: {"CLEAN - All tool calls explained" if violations == 0 else "VIOLATIONS DETECTED"}')

conn.close()
