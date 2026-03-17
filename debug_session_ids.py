#!/usr/bin/env python
"""Debug script to find all session_ids in the ledger."""

from divineos.ledger import get_events
from pathlib import Path
from collections import Counter

# Get all events (no limit)
print("Retrieving all events from ledger...")
events = get_events(limit=10000)
print(f"Total events retrieved: {len(events)}")

# Extract session_ids
session_ids = []
for event in events:
    payload = event.get("payload", {})
    session_id = payload.get("session_id")
    if session_id:
        session_ids.append(session_id)

# Count occurrences
session_id_counts = Counter(session_ids)
print(f"\nUnique session_ids: {len(session_id_counts)}")
print("\nSession ID distribution:")
for session_id, count in session_id_counts.most_common(10):
    print(f"  {session_id}: {count} events")

# Check persistent session file
session_file = Path.home() / ".divineos" / "current_session.txt"
print(f"\nPersistent session file exists: {session_file.exists()}")
if session_file.exists():
    current_session_id = session_file.read_text().strip()
    print(f"Current session_id from file: {current_session_id}")
    if current_session_id in session_id_counts:
        print(f"  ✓ Found in ledger: {session_id_counts[current_session_id]} events")
    else:
        print(f"  ✗ NOT found in ledger")
else:
    print("No persistent session file")

# Show most recent event
if events:
    most_recent = events[0]
    print(f"\nMost recent event:")
    print(f"  Type: {most_recent.get('event_type')}")
    print(f"  Session ID: {most_recent.get('payload', {}).get('session_id')}")
    print(f"  Timestamp: {most_recent.get('timestamp')}")
