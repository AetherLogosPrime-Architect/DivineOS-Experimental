from divineos.core.ledger import init_db
from divineos.core.consolidation import store_knowledge_smart, search_knowledge, _extract_key_terms, _compute_overlap

# Initialize database
init_db()

# Store first entry
print("=== Storing first entry ===")
kid1 = store_knowledge_smart(
    "MISTAKE", "Always read files before editing them in the codebase"
)
print(f"kid1: {kid1}")

# Now try to store second entry (should find fuzzy duplicate)
print("\n=== Storing second entry ===")
content2 = "Read files before editing them in the codebase always"
key_terms = _extract_key_terms(content2)
print(f"Key terms: {key_terms}")

# Try search manually
print("\n=== Manual search ===")
similar = search_knowledge(key_terms, limit=5)
print(f"Search results: {len(similar)}")
for entry in similar:
    print(f"  - {entry['knowledge_id']}: {entry['content'][:50]}...")
    overlap = _compute_overlap(content2, entry["content"])
    print(f"    Overlap: {overlap}")
    if overlap > 0.6:
        print(f"    -> Would match!")

# Now store the second entry
print("\n=== Storing second entry ===")
kid2 = store_knowledge_smart("MISTAKE", content2)
print(f"kid2: {kid2}")
print(f"kid1 == kid2: {kid1 == kid2}")
