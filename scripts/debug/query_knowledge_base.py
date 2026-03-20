#!/usr/bin/env python3
"""Query the knowledge base for 17 × 23 facts."""

from divineos.core.ledger import init_db, _get_connection
from divineos.core.consolidation import init_knowledge_table
from divineos.core.session_manager import get_current_session_id, initialize_session
import sqlite3

# Initialize
init_db()
init_knowledge_table()

try:
    session_id = get_current_session_id()
except RuntimeError:
    session_id = initialize_session()

print("=== KNOWLEDGE BASE QUERY: 17 × 23 ===\n")

conn = _get_connection()
conn.row_factory = sqlite3.Row

# Query for all FACT entries about 17 × 23
cursor = conn.execute('''
    SELECT knowledge_id, content, confidence, created_at, superseded_by, 
           contradiction_count, corroboration_count
    FROM knowledge 
    WHERE knowledge_type = 'FACT' 
    AND (content LIKE '%17%23%' OR content LIKE '%17 × 23%' OR content LIKE '%17 x 23%')
    ORDER BY created_at ASC
''')

facts = cursor.fetchall()

if not facts:
    print("No facts found about 17 × 23 in the knowledge base.")
else:
    print(f"Found {len(facts)} fact(s) about 17 × 23:\n")
    
    active_facts = []
    superseded_facts = []
    
    for fact in facts:
        status = "SUPERSEDED" if fact['superseded_by'] else "ACTIVE"
        if status == "ACTIVE":
            active_facts.append(fact)
        else:
            superseded_facts.append(fact)
        
        print(f"Knowledge ID: {fact['knowledge_id']}")
        print(f"  Content: {fact['content']}")
        print(f"  Confidence: {fact['confidence']}")
        print(f"  Status: {status}")
        print(f"  Created: {fact['created_at']}")
        if fact['superseded_by']:
            print(f"  Superseded By: {fact['superseded_by']}")
        print(f"  Contradiction Count: {fact['contradiction_count']}")
        print(f"  Corroboration Count: {fact['corroboration_count']}")
        print()
    
    print("=== SUMMARY ===\n")
    print(f"Active Facts: {len(active_facts)}")
    for fact in active_facts:
        print(f"  - {fact['content']} (ID: {fact['knowledge_id'][:8]}..., Confidence: {fact['confidence']})")
    
    if superseded_facts:
        print(f"\nSuperseded Facts: {len(superseded_facts)}")
        for fact in superseded_facts:
            print(f"  - {fact['content']} (ID: {fact['knowledge_id'][:8]}..., Superseded by: {fact['superseded_by'][:8]}...)")
    
    if len(active_facts) > 1:
        print(f"\n⚠️  CONFLICT DETECTED: {len(active_facts)} conflicting active facts exist")
        print("The system currently returns multiple conflicting values without automatic resolution.")
    elif len(active_facts) == 1:
        print(f"\n✓ Single authoritative fact: {active_facts[0]['content']}")

conn.close()
