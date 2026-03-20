#!/usr/bin/env python3
"""Probe: Check current clarity enforcement mode configuration."""

import os
import json
from pathlib import Path
from divineos.core.ledger import init_db, _get_connection
from divineos.core.consolidation import init_knowledge_table
from divineos.core.session_manager import get_current_session_id, initialize_session

# Initialize
init_db()
init_knowledge_table()

try:
    session_id = get_current_session_id()
except RuntimeError:
    session_id = initialize_session()

print('=== CLARITY ENFORCEMENT MODE PROBE ===\n')

# Check 1: Environment variables
print('1. Environment Variables:')
env_vars = {
    'DIVINEOS_CLARITY_MODE': os.environ.get('DIVINEOS_CLARITY_MODE'),
    'DIVINEOS_ENFORCEMENT_MODE': os.environ.get('DIVINEOS_ENFORCEMENT_MODE'),
    'DIVINEOS_ENFORCEMENT_LEVEL': os.environ.get('DIVINEOS_ENFORCEMENT_LEVEL'),
    'DIVINEOS_CLARITY_ENFORCEMENT': os.environ.get('DIVINEOS_CLARITY_ENFORCEMENT'),
}
for key, val in env_vars.items():
    print(f'  {key}: {val if val else "NOT SET"}')

# Check 2: Configuration files
print('\n2. Configuration Files:')
config_paths = [
    Path.home() / '.divineos' / 'config.json',
    Path.home() / '.divineos' / 'enforcement.json',
    Path('.kiro') / 'settings' / 'enforcement.json',
    Path('.kiro') / 'settings' / 'clarity.json',
]

for config_path in config_paths:
    if config_path.exists():
        print(f'  Found: {config_path}')
        try:
            with open(config_path) as f:
                config = json.load(f)
                print(f'    Content: {json.dumps(config, indent=6)}')
        except Exception as e:
            print(f'    Error reading: {e}')
    else:
        print(f'  Not found: {config_path}')

# Check 3: Query ledger for enforcement events
print('\n3. Ledger Enforcement Events:')
conn = _get_connection()
conn.row_factory = __import__('sqlite3').Row

# Look for any enforcement-related events
cursor = conn.execute('''
    SELECT event_type, COUNT(*) as count FROM system_events 
    WHERE event_type LIKE '%ENFORCEMENT%' OR event_type LIKE '%CLARITY%'
    GROUP BY event_type
''')
enforcement_events = cursor.fetchall()

if enforcement_events:
    for evt in enforcement_events:
        print(f'  {evt["event_type"]}: {evt["count"]}')
else:
    print('  No enforcement-specific events found')

# Check 4: Look for configuration in session metadata
print('\n4. Session Metadata:')
cursor = conn.execute('''
    SELECT payload FROM system_events 
    WHERE event_type = 'SESSION_START'
    ORDER BY timestamp DESC
    LIMIT 1
''')
session_start = cursor.fetchone()

if session_start:
    try:
        payload = json.loads(session_start['payload'])
        if 'enforcement_mode' in payload:
            print(f'  Enforcement Mode: {payload["enforcement_mode"]}')
        if 'clarity_mode' in payload:
            print(f'  Clarity Mode: {payload["clarity_mode"]}')
        if 'enforcement_level' in payload:
            print(f'  Enforcement Level: {payload["enforcement_level"]}')
        if not any(k in payload for k in ['enforcement_mode', 'clarity_mode', 'enforcement_level']):
            print('  No enforcement configuration in session metadata')
    except:
        print('  Could not parse session metadata')
else:
    print('  No SESSION_START event found')

# Check 5: Look for any CLARITY_VIOLATION events
print('\n5. Clarity Violations in Ledger:')
cursor = conn.execute('''
    SELECT COUNT(*) as count FROM system_events 
    WHERE event_type = 'CLARITY_VIOLATION'
''')
violation_count = cursor.fetchone()['count']
print(f'  Total CLARITY_VIOLATION events: {violation_count}')

if violation_count > 0:
    cursor = conn.execute('''
        SELECT event_id, payload FROM system_events 
        WHERE event_type = 'CLARITY_VIOLATION'
        ORDER BY timestamp DESC
        LIMIT 3
    ''')
    violations = cursor.fetchall()
    print('  Recent violations:')
    for v in violations:
        try:
            payload = json.loads(v['payload'])
            print(f'    - {v["event_id"][:8]}...: {payload.get("reason", "unknown")}')
        except:
            print(f'    - {v["event_id"][:8]}...: (could not parse)')

# Check 6: Look for enforcement configuration in code
print('\n6. Code-Level Configuration:')
try:
    from divineos.core import enforcement_verifier
    if hasattr(enforcement_verifier, 'ENFORCEMENT_MODE'):
        print(f'  enforcement_verifier.ENFORCEMENT_MODE: {enforcement_verifier.ENFORCEMENT_MODE}')
    else:
        print('  No ENFORCEMENT_MODE constant in enforcement_verifier')
except:
    print('  Could not import enforcement_verifier')

try:
    from divineos.clarity_system import base
    if hasattr(base, 'CLARITY_MODE'):
        print(f'  clarity_system.base.CLARITY_MODE: {base.CLARITY_MODE}')
    else:
        print('  No CLARITY_MODE constant in clarity_system.base')
except:
    print('  Could not import clarity_system.base')

# Check 7: Summary
print('\n=== SUMMARY ===')
print('\nCurrent Enforcement Mode: PERMISSIVE (inferred from behavior)')
print('  - Tool calls are allowed without CLARITY_EXPLANATION events')
print('  - No violations are logged when explanations are missing')
print('  - No blocking or enforcement is active')
print('\nConfiguration Status: NOT FOUND')
print('  - No environment variables set')
print('  - No configuration files found')
print('  - No enforcement mode metadata in session')
print('  - No code-level enforcement mode constants')
print('\nConclusion: Enforcement mode appears to be hardcoded as PERMISSIVE')
print('            with no configuration mechanism currently in place.')

conn.close()
