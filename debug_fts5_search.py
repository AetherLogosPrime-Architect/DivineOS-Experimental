import sqlite3
from pathlib import Path

db_path = Path('src/data/event_ledger.db')
conn = sqlite3.connect(str(db_path))

# Check what's in knowledge_fts
print("=== Knowledge FTS content ===")
rows = conn.execute("SELECT rowid, content FROM knowledge_fts").fetchall()
for row in rows:
    print(f"rowid={row[0]}, content={row[1][:50]}...")

# Try the search query
print("\n=== Search query ===")
query = "read files editing codebase always"
print(f"Query: {query}")

try:
    rows = conn.execute(
        """SELECT k.knowledge_id, k.content
           FROM knowledge_fts fts
           JOIN knowledge k ON k.rowid = fts.rowid
           WHERE knowledge_fts MATCH ?
             AND k.superseded_by IS NULL
           ORDER BY bm25(knowledge_fts, 10.0, 5.0, 1.0)
           LIMIT 5""",
        (query,)
    ).fetchall()
    print(f"Results: {len(rows)}")
    for row in rows:
        print(f"  - {row[0]}: {row[1][:50]}...")
except Exception as e:
    print(f"Error: {e}")

conn.close()
