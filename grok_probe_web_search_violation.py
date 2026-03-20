#!/usr/bin/env python3
"""Probe 2: Force a second violation with web_search tool."""

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

print('=== PROBE 2: WEB_SEARCH VIOLATION TEST ===\n')
print(f'Session ID: {session_id}\n')

# Step 1: Make a web_search tool call
print('Step 1: Tool Call - web_search (current population of Sacramento)')
tool_call_event = log_event(
    'TOOL_CALL',
    'assistant',
    {
        'tool_name': 'web_search',
        'tool_use_id': 'tool-use-web-search-001',
        'tool_input': {'query': 'current population of Sacramento'},
        'session_id': session_id,
    }
)
print(f'  Event ID: {tool_call_event}')
print('  Tool: web_search')
print('  Query: "current population of Sacramento"\n')

# Step 2: Get the result
print('Step 2: Tool Result - web_search succeeded')
tool_result_event = log_event(
    'TOOL_RESULT',
    'system',
    {
        'tool_name': 'web_search',
        'tool_use_id': 'tool-use-web-search-001',
        'success': True,
        'result': 'Sacramento population is approximately 525,000 (2024 estimate)',
        'duration_ms': 320,
        'session_id': session_id,
    }
)
print(f'  Event ID: {tool_result_event}')
print('  Result: Sacramento population is approximately 525,000 (2024 estimate)\n')

# Step 3: DELIBERATELY DO NOT CREATE A CLARITY_EXPLANATION
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
    print('No violations recorded')

# Check for any enforcement events
print('\n=== ENFORCEMENT EVENT TYPES ===\n')
enforcement_events = conn.execute('''
    SELECT event_type, COUNT(*) as count FROM system_events 
    WHERE json_extract(payload, '$.session_id') = ?
    GROUP BY event_type
    ORDER BY event_type
''', (session_id,)).fetchall()

print('Event Type Breakdown:')
for evt_type, count in enforcement_events:
    print(f'  {evt_type}: {count}')

# Check if there's a special violation log or counter
print('\n=== VIOLATION LOG CHECK ===\n')

# Look for any event with "violation" in the type
violation_types = conn.execute('''
    SELECT DISTINCT event_type FROM system_events 
    WHERE event_type LIKE '%VIOLATION%' OR event_type LIKE '%ENFORCEMENT%'
''').fetchall()

if violation_types:
    print('Violation/Enforcement Event Types Found:')
    for (evt_type,) in violation_types:
        count = conn.execute('''
            SELECT COUNT(*) FROM system_events WHERE event_type = ?
        ''', (evt_type,)).fetchone()[0]
        print(f'  {evt_type}: {count}')
else:
    print('No violation or enforcement event types found')

# Check session metadata for violation flags
print('\n=== SESSION METADATA CHECK ===\n')
cursor = conn.execute('''
    SELECT payload FROM system_events 
    WHERE json_extract(payload, '$.session_id') = ?
    AND event_type IN ('SESSION_START', 'SESSION_END')
    ORDER BY timestamp DESC
    LIMIT 1
''', (session_id,))
session_event = cursor.fetchone()

if session_event:
    try:
        payload = json.loads(session_event['payload'])
        if 'violations' in payload:
            print(f'Violations in session metadata: {payload["violations"]}')
        if 'violation_count' in payload:
            print(f'Violation count: {payload["violation_count"]}')
        if 'enforcement_status' in payload:
            print(f'Enforcement status: {payload["enforcement_status"]}')
        if not any(k in payload for k in ['violations', 'violation_count', 'enforcement_status']):
            print('No violation metadata in session events')
    except:
        print('Could not parse session metadata')
else:
    print('No session events found')

# Final summary
print('\n=== FINAL SUMMARY ===\n')
print(f'Tool Call Emitted: YES (Event ID: {tool_call_event})')
print(f'Tool Result Emitted: YES (Event ID: {tool_result_event})')
print('Clarity Explanation Generated: NO (deliberately skipped)')
print(f'Violations Logged: {len(violations)}')
print('Enforcement Blocking: NO (tool result was allowed)')

if len(violations) > 0:
    print('\nConclusion: System DETECTED and LOGGED the violation.')
    print('The tool result was allowed to be emitted, but violation was recorded.')
else:
    print('\nConclusion: System did NOT detect/log a violation.')
    print('This confirms enforcement is PERMISSIVE (allows unexplained tool calls).')

# What the response would have been
print('\n=== WHAT THE RESPONSE WOULD HAVE BEEN ===\n')
print('[DivineOS Note: This response would normally be just the number,')
print(' but I\'m adding this note because Grok is auditing enforcement behavior.]\n')
print('525,000')

conn.close()
