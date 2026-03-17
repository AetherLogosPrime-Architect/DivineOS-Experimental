import sqlite3, json
conn = sqlite3.connect('data/event_ledger.db')
cursor = conn.cursor()

# Get the most recent session_id
cursor.execute('SELECT DISTINCT payload FROM system_events WHERE event_type = "USER_INPUT" ORDER BY timestamp DESC LIMIT 1')
row = cursor.fetchone()
if row:
    payload = json.loads(row[0])
    session_id = payload.get('session_id')
    print(f"Most recent USER_INPUT session_id: {session_id}")
    
    # Count events with this session_id using json_extract
    cursor.execute('SELECT COUNT(*) FROM system_events WHERE json_extract(payload, "$.session_id") = ?', (session_id,))
    count = cursor.fetchone()[0]
    print(f"Events with this session_id (json_extract): {count}")
    
    # List them
    cursor.execute('SELECT event_type FROM system_events WHERE json_extract(payload, "$.session_id") = ? ORDER BY timestamp DESC', (session_id,))
    events = cursor.fetchall()
    for e in events:
        print(f"  - {e[0]}")

conn.close()
