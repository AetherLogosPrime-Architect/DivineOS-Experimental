from divineos.agent_integration.memory_monitor import load_context
context = load_context('foundation-ledger-architecture-fix')
print('=== LEDGER ANALYSIS ===')
print('Session: foundation-ledger-architecture-fix')
print('Previous work items:', context.get('previous_work', 0))
print('Recent context items:', len(context.get('recent_context', [])))
print()
print('Key insight: The system has been running pattern learning and archiving')
print('The pytest hanging issue is a NEW problem introduced by the commit')
