import sqlite3
from pathlib import Path

db_path = Path('src/data/event_ledger.db')
conn = sqlite3.connect(str(db_path))

# Check if FTS5 table exists
try:
    result = conn.execute('SELECT COUNT(*) FROM knowledge_fts').fetchone()
    print('FTS5 table exists, count:', result[0])
except Exception as e:
    print('FTS5 table error:', e)

# Check knowledge table
result = conn.execute('SELECT COUNT(*) FROM knowledge').fetchone()
print('Knowledge table count:', result[0])

# Check if triggers exist
triggers = conn.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name='knowledge'").fetchall()
print('Triggers:', triggers)

# Check knowledge_fts schema
try:
    schema = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='knowledge_fts'").fetchone()
    print('FTS5 schema:', schema)
except Exception as e:
    print('Schema error:', e)

conn.close()
