#!/usr/bin/env python
"""Debug script to understand why analyze-now is failing."""

from pathlib import Path
import json
from divineos.ledger import get_events, get_verified_events, _get_connection
from divineos.event_capture import get_session_tracker

# Try to get session_id using the same logic as the fixed export function
current_session_id = None

# Try to read from persistent file first
session_file = Path.home() / ".divineos" / "current_session.txt"
print(f"Session file: {session_file}")
print(f"File exists: {session_file.exists()}")

if session_file.exists():
    try:
        current_session_id = session_file.read_text().strip()
        print(f"Read session_id from file: {current_session_id}")
    except Exception as e:
        print(f"Failed to read session_id file: {e}")
        current_session_id = None

# If file doesn't exist or is empty, query database
if not current_session_id:
    print("No session_id from file, querying database...")
    conn = _get_connection()
    try:
        cursor = conn.execute(
            "SELECT payload FROM system_events WHERE event_type != 'SESSION_END' ORDER BY timestamp DESC LIMIT 1"
        )
        row = cursor.fetchone()
        if row:
            payload = json.loads(row[0])
            current_session_id = payload.get("session_id")
            print(f"Got session_id from database: {current_session_id}")
        else:
            print("No non-SESSION_END events found in database")
    finally:
        conn.close()

# Fallback to session tracker
if not current_session_id:
    current_session_id = get_session_tracker().get_current_session_id()
    print(f"Using session tracker session_id: {current_session_id}")

print(f"\nFinal session_id: {current_session_id}")

# Now try to get verified events
print(f"\nGetting verified events for session_id: {current_session_id}")
verified_events, corrupted_events = get_verified_events(
    limit=100,
    skip_corrupted=True,
    session_id=current_session_id
)

print(f"Verified events: {len(verified_events)}")
print(f"Corrupted events: {len(corrupted_events)}")

if verified_events:
    print("\nVerified events:")
    for e in verified_events:
        print(f"  - {e['event_type']}: {e['event_id']}")
else:
    print("\nNo verified events found!")
    
    # Debug: get all events and see what's there
    print("\nDebug: All events in database:")
    all_events = get_events(limit=100)
    print(f"Total events: {len(all_events)}")
    for e in all_events[-5:]:
        print(f"  - {e['event_type']}: session_id={e.get('payload', {}).get('session_id')}")
