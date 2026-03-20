#!/usr/bin/env python
"""Direct test runner - bypasses pytest to avoid hanging issues."""

import sys
from pathlib import Path

# Initialize database first
from divineos.core.ledger import init_db
init_db()
print("[OK] Database initialized")

# Now run a simple test
from divineos.agent_integration.decision_store import DecisionStore
import uuid

print("\n=== Testing DecisionStore ===")
store = DecisionStore()
session_id = str(uuid.uuid4())
pattern_id = str(uuid.uuid4())

try:
    decision_id = store.store_decision(
        session_id=session_id,
        task="Test task",
        chosen_pattern=pattern_id,
        pattern_confidence=0.85,
        alternatives_considered=[],
        counterfactual={
            "chosen_cost": 100.0,
            "alternative_costs": [150.0],
            "default_cost": 120.0,
            "counterfactual_type": "estimated",
        },
    )
    print(f"[OK] Decision stored: {decision_id}")
except Exception as e:
    print(f"[FAIL] Failed to store decision: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n=== All tests passed ===")
