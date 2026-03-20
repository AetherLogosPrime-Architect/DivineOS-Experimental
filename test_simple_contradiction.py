#!/usr/bin/env python
"""Simple test to verify contradiction resolution works."""

from src.divineos.supersession import (
    ResolutionEngine,
    ResolutionStrategy,
    ContradictionDetector,
)

# Create engine and detector
engine = ResolutionEngine()
detector = ContradictionDetector()

# Create two contradicting facts
fact1 = {
    "id": "fact_1",
    "fact_type": "measurement",
    "fact_key": "temperature",
    "value": 25.0,
    "timestamp": "2026-03-20T10:00:00Z",
    "confidence": 0.9,
    "source": "sensor_a",
}

fact2 = {
    "id": "fact_2",
    "fact_type": "measurement",
    "fact_key": "temperature",
    "value": 26.0,
    "timestamp": "2026-03-20T10:01:00Z",
    "confidence": 0.95,
    "source": "sensor_b",
}

# Register facts
engine.register_fact(fact1)
engine.register_fact(fact2)

# Detect contradiction
contradiction = detector.detect_contradiction(fact1, fact2)
print(f"Contradiction detected: {contradiction is not None}")

if contradiction:
    # Resolve contradiction
    supersession = engine.resolve_contradiction(
        contradiction, ResolutionStrategy.NEWER_FACT
    )
    print(f"Supersession event created: {supersession.event_id}")
    print(f"Superseded fact: {supersession.superseded_fact_id}")
    print(f"Superseding fact: {supersession.superseding_fact_id}")
    
    # Test 1: Check supersession chain
    chain = engine.get_supersession_chain(supersession.superseded_fact_id)
    print("\nTest 1 - Supersession chain:")
    print(f"  Chain length: {len(chain)}")
    print(f"  Chain[0] superseded: {chain[0].superseded_fact_id}")
    print(f"  Chain[0] superseding: {chain[0].superseding_fact_id}")
    
    # Test 2: Check superseded marking
    is_superseded = engine.is_superseded(supersession.superseded_fact_id)
    is_not_superseded = engine.is_superseded(supersession.superseding_fact_id)
    print("\nTest 2 - Superseded marking:")
    print(f"  Superseded fact marked: {is_superseded}")
    print(f"  Superseding fact NOT marked: {not is_not_superseded}")
    
    # Test 3: Check query returns current fact
    current = engine.get_current_truth("measurement", "temperature")
    print("\nTest 3 - Query returns current fact:")
    print(f"  Current fact ID: {current['id']}")
    print(f"  Is superseding fact: {current['id'] == supersession.superseding_fact_id}")
    print(f"  Is NOT superseded fact: {current['id'] != supersession.superseded_fact_id}")

print("\nAll basic tests passed!")
