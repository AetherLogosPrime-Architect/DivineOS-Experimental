from divineos.core.ledger import init_db
from divineos.core.consolidation import _get_connection, _KNOWLEDGE_COLS_K, _row_to_dict, _extract_key_terms

# Initialize database
init_db()

# Simulate what store_knowledge_smart does
conn = _get_connection()

# Insert first entry
kid1 = "test-id-1"
conn.execute(
    "INSERT INTO knowledge (knowledge_id, created_at, updated_at, knowledge_type, content, confidence, source_events, tags, access_count, content_hash, source, maturity, corroboration_count, contradiction_count) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, 0, 0)",
    (
        kid1,
        1.0,
        1.0,
        "MISTAKE",
        "Always read files before editing them in the codebase",
        1.0,
        "[]",
        "[]",
        "hash1",
        "STATED",
        "RAW",
    ),
)

# Try to search BEFORE commit
print("=== Before commit ===")
key_terms = _extract_key_terms("Read files before editing them in the codebase always")
print(f"Key terms: {key_terms}")

try:
    query_str = f"""SELECT {_KNOWLEDGE_COLS_K}
           FROM knowledge_fts fts
           JOIN knowledge k ON k.rowid = fts.rowid
           WHERE knowledge_fts MATCH ?
             AND k.superseded_by IS NULL
           ORDER BY bm25(knowledge_fts, 10.0, 5.0, 1.0)
           LIMIT 5"""
    rows = conn.execute(query_str, (key_terms, 5)).fetchall()
    print(f"Results before commit: {len(rows)}")
except Exception as e:
    print(f"Error before commit: {e}")

# Now commit
print("\n=== After commit ===")
conn.commit()

try:
    rows = conn.execute(query_str, (key_terms, 5)).fetchall()
    print(f"Results after commit: {len(rows)}")
    for row in rows:
        entry = _row_to_dict(row)
        print(f"  - {entry['knowledge_id']}: {entry['content'][:50]}...")
except Exception as e:
    print(f"Error after commit: {e}")

conn.close()
