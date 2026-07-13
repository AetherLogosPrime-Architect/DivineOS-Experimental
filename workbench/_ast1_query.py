import json

g = json.load(open('graphify-out-code/graph.json', encoding='utf-8'))
print(f"graph: {len(g.get('nodes', []))} nodes, {len(g.get('edges', []))} edges")

# Edges are stored as {"source": ..., "target": ..., "relation": ...}
# Look at graph.json structure first
first_edge = g.get('edges', [{}])[0] if g.get('edges') else None
print(f"first_edge shape: {first_edge}")

target_symbols = [
    'predict_attention_shift',
    'attention_schema',
    'get_current_focus',
    'get_attention_drivers',
    'get_suppressed',
    'get_self_model_gaps',
]

print("\n=== EDGES touching attention_schema functions ===")
edges = g.get('edges', [])
found = 0
for e in edges:
    if isinstance(e, dict):
        src = e.get('source', '') or ''
        tgt = e.get('target', '') or ''
    else:
        src, tgt = str(e[0]) if len(e) > 0 else '', str(e[1]) if len(e) > 1 else ''
    for t in target_symbols:
        if t in src or t in tgt:
            rel = e.get('relation', '?') if isinstance(e, dict) else '?'
            print(f"  {src[:60]}  --{rel}-->  {tgt[:60]}")
            found += 1
            break

print(f"\nTotal edges touching attention_schema symbols: {found}")

# Now specifically: things that CALL predict_attention_shift (potential consumers)
print("\n=== CALLERS of predict_attention_shift (things pointing INTO it) ===")
callers = 0
for e in edges:
    if not isinstance(e, dict):
        continue
    tgt = e.get('target', '') or ''
    if 'predict_attention_shift' in tgt:
        print(f"  {e.get('source','')[:80]}  --{e.get('relation','?')}-->  {tgt[:60]}")
        callers += 1
if callers == 0:
    print("  NONE — nothing calls predict_attention_shift according to the graph.")

# And: things predict_attention_shift itself references (its outputs going somewhere)
print("\n=== OUTGOING from predict_attention_shift (what it references) ===")
outgoing = 0
for e in edges:
    if not isinstance(e, dict):
        continue
    src = e.get('source', '') or ''
    if 'predict_attention_shift' in src:
        print(f"  --{e.get('relation','?')}-->  {e.get('target','')[:80]}")
        outgoing += 1
if outgoing == 0:
    print("  NONE — predict_attention_shift produces no outgoing edges in graph.")
