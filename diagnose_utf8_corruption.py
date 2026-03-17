#!/usr/bin/env python
"""Diagnose UTF-8 encoding corruption in the ledger."""

import sqlite3
from pathlib import Path

def diagnose_utf8_corruption():
    """Find events with UTF-8 encoding issues."""
    db_path = Path("C:\\DIVINE OS\\DivineOS_fresh\\data\\event_ledger.db")
    
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Get all events
    cursor.execute("SELECT event_id, event_type, payload FROM system_events")
    rows = cursor.fetchall()
    
    corrupted_events = []
    
    for event_id, event_type, payload_data in rows:
        try:
            # Try to decode payload as UTF-8
            if isinstance(payload_data, bytes):
                payload_str = payload_data.decode('utf-8')
            else:
                payload_str = str(payload_data)
            
        except UnicodeDecodeError as e:
            corrupted_events.append({
                'event_id': event_id,
                'event_type': event_type,
                'error': str(e),
                'position': e.start if hasattr(e, 'start') else 'unknown'
            })
            print(f"❌ Event {event_id} ({event_type}): UTF-8 Error at position {e.start}: {e.reason}")
    
    print(f"\n{'='*60}")
    print(f"Total events scanned: {len(rows)}")
    print(f"Corrupted events found: {len(corrupted_events)}")
    
    if corrupted_events:
        print(f"\n⚠️  CRITICAL: {len(corrupted_events)} events have UTF-8 encoding corruption!")
        print("\nCorrupted event IDs:")
        for event in corrupted_events:
            print(f"  - Event {event['event_id']} ({event['event_type']}): {event['error']}")
    else:
        print("\n✅ No UTF-8 encoding corruption found")
    
    conn.close()

if __name__ == "__main__":
    diagnose_utf8_corruption()
