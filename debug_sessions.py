import sqlite3, json
conn = sqlite3.connect('data/event_ledger.db')
cursor = conn.cursor()
cursor.execute('SELECT event_type, payload FROM system_events ORDER BY timestamp DESC LIMIT 10')
rows = cursor.fetchall()
print("Recent events and their session_ids:")
for r in rows:
    payload = json.loads(r[1])
    session_id = payload.get('session_id', 'MISSING')
    print(f"{r[0]:15} | {session_id}")
conn.close()
