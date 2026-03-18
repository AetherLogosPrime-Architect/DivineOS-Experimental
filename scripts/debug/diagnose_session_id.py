#!/usr/bin/env python
"""Diagnose session ID mismatch issue."""

import sqlite3
import json
from pathlib import Path

def diagnose_session_id():
    """Check session IDs in ledger vs current session."""
    db_path = Path("C:\\DIVINE OS\\DivineOS_fresh\\data\\event_ledger.db")
    
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Get all unique session IDs from events
    cursor.execute("""
        SELECT DISTINCT json_extract(payload, '$.session_id') as session_id, 
               COUNT(*) as count
        FROM system_events 
        WHERE event_type != 'SESSION_END' 
        GROUP BY session_id
        ORDER BY count DESC
    """)
    sessions = cursor.fetchall()
    
    print("=" * 60)
    print("Session IDs in ledger:")
    print("=" * 60)
    for session_id, count in sessions:
        print(f"  {session_id}: {count} events")
    
    # Get current session ID from file
    session_file = Path.home() / ".divineos" / "current_session.txt"
    print("\n" + "=" * 60)
    print("Current session ID:")
    print("=" * 60)
    
    if session_file.exists():
        current_session = session_file.read_text().strip()
        print(f"  From file: {current_session}")
        
        # Check if this session exists in ledger
        cursor.execute(
            "SELECT COUNT(*) FROM system_events WHERE json_extract(payload, '$.session_id') = ?",
            (current_session,)
        )
        count = cursor.fetchone()[0]
        print(f"  Events with this session ID: {count}")
        
        if count == 0:
            print("\n⚠️  PROBLEM: Current session ID has NO events in ledger!")
    else:
        print(f"  No file at {session_file}")
    
    # Get most recent session ID from database
    cursor.execute("""
        SELECT json_extract(payload, '$.session_id') as session_id
        FROM system_events 
        WHERE event_type != 'SESSION_END'
        ORDER BY timestamp DESC 
        LIMIT 1
    """)
    row = cursor.fetchone()
    if row:
        recent_session = row[0]
        print(f"\n  Most recent session ID: {recent_session}")
    
    conn.close()
    print("\n" + "=" * 60)

if __name__ == "__main__":
    diagnose_session_id()
