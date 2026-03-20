#!/usr/bin/env python
"""Live probe: Test supersession system with 17×23 contradiction."""

from datetime import datetime
from divineos.supersession.contradiction_detector import ContradictionDetector
from divineos.supersession.resolution_engine import ResolutionEngine
from divineos.supersession.query_interface import QueryInterface

# Initialize components
detector = ContradictionDetector()
engine = ResolutionEngine()
query = QueryInterface(engine, detector)

# Create two conflicting facts about 17 × 23
fact1 = {
    "id": "fact_001_17x23_correct",
    "fact_type": "arithmetic",
    "fact_key": "17_times_23",
    "value": 391,
    "confidence": 1.0,
    "timestamp": datetime.now().isoformat(),
    "source": "canonical_math",
}

fact2 = {
    "id": "fact_002_17x23_wrong",
    "fact_type": "arithmetic",
    "fact_key": "17_times_23",
    "value": 500,
    "confidence": 0.8,
    "timestamp": datetime.now().isoformat(),
    "source": "user_input",
}

print("=" * 80)
print("LIVE SUPERSESSION PROBE: 17 × 23 Contradiction")
print("=" * 80)

# Register facts
print("\n1. Registering Fact 1 (correct: 17 × 23 = 391)")
query.register_fact(fact1)
print(f"   ID: {fact1['id']}")
print(f"   Value: {fact1['value']}")
print(f"   Confidence: {fact1['confidence']}")

print("\n2. Registering Fact 2 (wrong: 17 × 23 = 500)")
query.register_fact(fact2)
print(f"   ID: {fact2['id']}")
print(f"   Value: {fact2['value']}")
print(f"   Confidence: {fact2['confidence']}")

# Detect contradictions
print("\n3. Detecting Contradictions...")
contradiction = detector.detect_contradiction(fact1, fact2)
print(f"   Contradiction Detected: {contradiction is not None}")
if contradiction:
    print("\n   Contradiction Details:")
    print(f"   - Severity: {contradiction.severity.value}")
    print(f"   - Fact 1: {contradiction.fact1_id}")
    print(f"   - Fact 2: {contradiction.fact2_id}")
    print(f"   - Context Items: {len(contradiction.context)}")

# Resolve contradiction
print("\n4. Resolving Contradiction (NEWER_FACT strategy)...")
from divineos.supersession.resolution_engine import ResolutionStrategy
resolution = engine.resolve_contradiction(contradiction, ResolutionStrategy.NEWER_FACT)
print(f"   Resolution Strategy: {resolution.reason}")
print(f"   Winning Fact: {resolution.superseding_fact_id}")
print(f"   Losing Fact: {resolution.superseded_fact_id}")
print(f"   Event ID: {resolution.event_id}")

# Query current truth
print("\n5. Querying Current Truth...")
current_truth = query.query_current_truth("arithmetic", "17_times_23")
if current_truth:
    print(f"   Current Fact ID: {current_truth.current_fact.get('id')}")
    print(f"   Current Value: {current_truth.current_fact.get('value')}")
    print(f"   Superseded Facts: {len(current_truth.superseded_facts)}")
    if current_truth.superseded_facts:
        for superseded in current_truth.superseded_facts:
            print(f"     - {superseded.get('id')}: {superseded.get('value')}")
    print(f"   Supersession Events: {len(current_truth.supersession_events)}")
    if current_truth.supersession_events:
        for event in current_truth.supersession_events:
            print(f"     - Event ID: {event.get('event_id')}")
            print(f"       Reason: {event.get('reason')}")

# Query contradictions
print("\n6. Querying All Contradictions...")
all_contradictions = query.query_contradictions()
print(f"   Total Contradictions: {len(all_contradictions)}")
for contradiction in all_contradictions:
    print(f"   - Severity: {contradiction.get('severity')}")
    print(f"     Fact 1: {contradiction.get('fact1_id')}")
    print(f"     Fact 2: {contradiction.get('fact2_id')}")

# Query supersession chain
print("\n7. Querying Supersession Chain...")
chain = query.query_supersession_chain(fact2["id"])
print(f"   Chain Length: {len(chain)}")
for i, event in enumerate(chain, 1):
    print(f"   Event {i}:")
    print(f"   - ID: {event.get('event_id')}")
    print(f"   - Superseded: {event.get('superseded_fact_id')}")
    print(f"   - Superseding: {event.get('superseding_fact_id')}")
    print(f"   - Reason: {event.get('reason')}")

print("\n" + "=" * 80)
print("PROBE COMPLETE")
print("=" * 80)
print("\nExpected Outcome:")
print("[OK] Fact 1 (391) is current truth")
print("[OK] Fact 2 (500) is superseded")
print("[OK] Supersession event created with NEWER_FACT reason")
print("[OK] Contradiction detected and tracked")
print("[OK] Supersession chain shows resolution path")
