from divineos.core.ledger import init_db
from divineos.agent_integration.decision_store import DecisionStore
import uuid

# Initialize database
init_db()
print("Database initialized")

# Create a store
store = DecisionStore()
print("DecisionStore created")

# Try to store a decision
session_id = str(uuid.uuid4())
pattern_id = str(uuid.uuid4())

decision_id = store.store_decision(
    session_id=session_id,
    task="Test task",
    chosen_pattern=pattern_id,
    pattern_confidence=0.85,
    alternatives_considered=[],
    counterfactual={"chosen_cost": 100.0, "alternative_costs": [150.0]},
)

print(f"Decision stored: {decision_id}")
