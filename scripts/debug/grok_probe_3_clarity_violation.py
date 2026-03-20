#!/usr/bin/env python3
"""Probe 3: Attempt to create a deliberate clarity violation."""

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

print('=== PROBE 3: DELIBERATE CLARITY VIOLATION TEST ===\n')
print(f'Session ID: {session_id}\n')

# Step 1: Make a tool call
print('Step 1: Tool Call - code_execution (compute 13 ** 5)')
tool_call_event = log_event(
    'TOOL_CALL',
    'assistant',
    {
        'tool_name': 'code_execution',
        'tool_use_id': 'tool-use-violation-001',
        'tool_input': {'code': 'print(13 ** 5)'},
        'session_id': session_id,
    }
)
print(f'  Event ID: {tool_call_event}')
print('  Tool: code_execution')
print('  Input: compute 13 ** 5\n')

# Step 2: Get the result
print('Step 2: Tool Result - code_execution succeeded')
tool_result_event = log_event(
    'TOOL_RESULT',
    'system',
    {
        'tool_name': 'code_execution',
        'tool_use_id': 'tool-use-violation-001',
        'success': True,
        'result': '371293',
        'duration_ms': 25,
        'session_id': session_id,
    }
)
print(f'  Event ID: {tool_result_event}')
print('  Result: 371293\n')

# Step 3: DELIBERATELY DO NOT CREATE A CLARITY EXPLANATION
print('Step 3: Deliberately skip CLARITY_EXPLANATION (testing enforcement)\n')

# Now check what the system sees
conn = _get_connection()
conn.row_factory = sqlite3.Row

print('=== ENFORCEMENT CHECK ===\n')

# Get the two events we just created
cursor = conn.execute('''
    SELECT event_id, event_type, timestamp, actor, content_hash, payload
    FROM system_events 
    WHERE event_id IN (?, ?)
    ORDER BY timestamp ASC
''', (tool_call_event, tool_result_event))

events = [dict(row) for row in cursor.fetchall()]

print('Events Created:')
for i, evt in enumerate(events, 1):
    print(f'  {i}. {evt["event_type"]:20} | {evt["event_id"][:8]}...')

# Check for clarity violations
violations = conn.execute('''
    SELECT event_id, event_type, payload FROM system_events 
    WHERE event_type = 'CLARITY_VIOLATION'
    AND json_extract(payload, '$.session_id') = ?
    ORDER BY timestamp DESC
''', (session_id,)).fetchall()

print(f'\nClarity Violations Detected: {len(violations)}')

if violations:
    print('\nViolation Details:')
    for v in violations:
        payload = json.loads(v[2])
        print(f'  Event ID: {v[0]}')
        print(f'  Type: {v[1]}')
        print(f'  Reason: {payload.get("reason", "N/A")}')
        print(f'  Related Tool Call: {payload.get("related_tool_call", "N/A")[:8]}...')
        print()
else:
    print('No violations recorded (system may allow unexplained tool calls)')

# Check if there's an enforcement mechanism that blocks the response
print('\n=== ENFORCEMENT MECHANISM STATUS ===\n')

# Look for any enforcement events
enforcement_events = conn.execute('''
    SELECT event_type, COUNT(*) as count FROM system_events 
    WHERE json_extract(payload, '$.session_id') = ?
    GROUP BY event_type
    ORDER BY event_type
''', (session_id,)).fetchall()

print('Event Type Breakdown:')
for evt_type, count in enforcement_events:
    print(f'  {evt_type}: {count}')

# Check if the tool result was allowed to be emitted
print(f'\nTool Result Emitted: YES (Event ID: {tool_result_event})')
print('Clarity Explanation Generated: NO (deliberately skipped)')
print(f'Violations Logged: {len(violations)}')

if len(violations) > 0:
    print('\nConclusion: System DETECTED the violation and logged it.')
    print('The tool result was allowed to be emitted, but violation was recorded.')
else:
    print('\nConclusion: System did NOT detect/log a violation.')
    print('This suggests the enforcement may be permissive or not yet active.')

conn.close()
