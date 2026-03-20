# DivineOS System Troubleshooting Guide

## Overview

This guide provides solutions for common issues encountered when using DivineOS. It covers diagnosis, root causes, and resolution steps.

## Clarity Enforcement Issues

### Issue 1: Clarity Violations Not Detected

**Symptoms**:
- Tool calls without explanation are not flagged as violations
- Enforcer allows all tool calls regardless of context

**Diagnosis**:
```python
# Check enforcer initialization
from divineos.clarity_enforcement.enforcer import ClarityEnforcer

enforcer = ClarityEnforcer()
print(f"Enforcer initialized: {enforcer is not None}")
print(f"Enforcement mode: {enforcer.config.enforcement_mode}")
```

**Root Causes**:
1. Enforcer not initialized
2. Enforcement mode is PERMISSIVE
3. Violation threshold too high
4. Semantic analyzer disabled

**Solutions**:

1. **Verify enforcer initialization**:
```python
from divineos.clarity_enforcement.enforcer import ClarityEnforcer
from divineos.clarity_enforcement.config import ClarityConfig

config = ClarityConfig(
    enforcement_mode="BLOCKING",
    violation_threshold=0.5,
    semantic_analysis_enabled=True
)
enforcer = ClarityEnforcer(config=config)
assert enforcer is not None
```

2. **Check enforcement mode**:
```python
# BLOCKING: Raise exception on violation
# LOGGING: Log violation, allow execution
# PERMISSIVE: Allow all, no logging

if enforcer.config.enforcement_mode == "PERMISSIVE":
    print("Warning: Enforcement mode is PERMISSIVE")
    # Change to BLOCKING or LOGGING
```

3. **Verify violation threshold**:
```python
# Threshold too high means fewer violations detected
if enforcer.config.violation_threshold > 0.7:
    print("Warning: Violation threshold is high")
    # Lower threshold to detect more violations
```

4. **Enable semantic analysis**:
```python
if not enforcer.config.semantic_analysis_enabled:
    print("Warning: Semantic analysis disabled")
    # Enable for better detection
```

### Issue 2: False Positive Violations

**Symptoms**:
- Tool calls with clear explanation are flagged as violations
- Legitimate tool calls are blocked

**Diagnosis**:
```python
# Check violation details
try:
    enforcer.enforce(
        tool_name="readFile",
        tool_input={"path": "file.txt"},
        context="I need to read the file",
        session_id="session-123"
    )
except ClarityViolation as e:
    print(f"Violation: {e}")
    print(f"Confidence: {e.confidence}")
```

**Root Causes**:
1. Semantic analyzer not recognizing explanation
2. Violation threshold too low
3. Context not provided correctly
4. Tool name not recognized

**Solutions**:

1. **Improve context**:
```python
# Bad context
context = "I need to do something"

# Good context
context = "I need to read the file to understand the structure"

enforcer.enforce(
    tool_name="readFile",
    tool_input={"path": "file.txt"},
    context=context,
    session_id="session-123"
)
```

2. **Lower violation threshold**:
```python
config = ClarityConfig(
    violation_threshold=0.3  # Lower threshold
)
enforcer = ClarityEnforcer(config=config)
```

3. **Check semantic analyzer**:
```python
from divineos.clarity_enforcement.semantic_analyzer import SemanticAnalyzer

analyzer = SemanticAnalyzer()
match = analyzer.analyze_relationship("readFile", "I need to read the file")
print(f"Semantic match: {match}")
```

### Issue 3: Enforcement Mode Not Working

**Symptoms**:
- BLOCKING mode doesn't raise exceptions
- LOGGING mode doesn't log violations
- PERMISSIVE mode blocks some calls

**Diagnosis**:
```python
# Check enforcement mode
print(f"Enforcement mode: {enforcer.config.enforcement_mode}")

# Test each mode
for mode in ["BLOCKING", "LOGGING", "PERMISSIVE"]:
    config = ClarityConfig(enforcement_mode=mode)
    enforcer = ClarityEnforcer(config=config)
    
    try:
        enforcer.enforce(
            tool_name="readFile",
            tool_input={"path": "file.txt"},
            context="",  # No context - will violate
            session_id="session-123"
        )
        print(f"{mode}: No exception raised")
    except Exception as e:
        print(f"{mode}: Exception raised - {e}")
```

**Root Causes**:
1. Configuration not applied
2. Enforcer not reinitialized after config change
3. Wrong enforcement mode specified

**Solutions**:

1. **Reinitialize enforcer after config change**:
```python
config = ClarityConfig(enforcement_mode="BLOCKING")
enforcer = ClarityEnforcer(config=config)  # Reinitialize
```

2. **Verify mode is applied**:
```python
assert enforcer.config.enforcement_mode == "BLOCKING"
```

3. **Test each mode separately**:
```python
# Test BLOCKING
config = ClarityConfig(enforcement_mode="BLOCKING")
enforcer = ClarityEnforcer(config=config)
try:
    enforcer.enforce(...)
except ClarityViolation:
    print("BLOCKING mode works")

# Test LOGGING
config = ClarityConfig(enforcement_mode="LOGGING")
enforcer = ClarityEnforcer(config=config)
enforcer.enforce(...)  # Should not raise
print("LOGGING mode works")

# Test PERMISSIVE
config = ClarityConfig(enforcement_mode="PERMISSIVE")
enforcer = ClarityEnforcer(config=config)
enforcer.enforce(...)  # Should not raise
print("PERMISSIVE mode works")
```

## Memory Monitor Issues

### Issue 4: Token Usage Not Tracked

**Symptoms**:
- Token usage always shows 0
- Compression never triggers
- Status always shows "OK"

**Diagnosis**:
```python
from divineos.agent_integration.memory_monitor import AgentMemoryMonitor

monitor = AgentMemoryMonitor(session_id="session-123")

# Check token tracking
status = monitor.check_token_usage(current_tokens=100000)
print(f"Current tokens: {status['current_tokens']}")
print(f"Usage percent: {status['usage_percent']}")
print(f"Action: {status['action']}")
```

**Root Causes**:
1. Monitor not initialized
2. Token usage not being updated
3. Thresholds not configured correctly
4. Database not accessible

**Solutions**:

1. **Verify monitor initialization**:
```python
from divineos.agent_integration.memory_monitor import AgentMemoryMonitor

monitor = AgentMemoryMonitor(session_id="session-123")
assert monitor is not None
assert monitor.session_id == "session-123"
```

2. **Update token usage**:
```python
# Call check_token_usage with actual token count
status = monitor.check_token_usage(current_tokens=120000)
print(f"Status: {status}")
```

3. **Verify thresholds**:
```python
# Default thresholds
# Warning: 65% (130,000 of 200,000)
# Compression: 75% (150,000 of 200,000)

# Check if thresholds are correct
if status["usage_percent"] >= 75:
    print("Should trigger compression")
```

4. **Check database access**:
```python
from pathlib import Path

db_path = Path.home() / ".divineos" / "divineos.db"
if not db_path.exists():
    print(f"Database not found: {db_path}")
    # Create database
    db_path.parent.mkdir(parents=True, exist_ok=True)
```

### Issue 5: Compression Not Triggering

**Symptoms**:
- Token usage reaches 75% but compression doesn't trigger
- Status shows "OK" even at high token usage
- Context not being compressed

**Diagnosis**:
```python
# Check compression threshold
status = monitor.check_token_usage(current_tokens=150000)
print(f"Usage percent: {status['usage_percent']}")
print(f"Action: {status['action']}")

if status["action"] != "COMPRESS_NOW":
    print("Compression not triggered")
```

**Root Causes**:
1. Threshold not reached
2. Compression threshold misconfigured
3. Monitor not checking token usage
4. Compression disabled

**Solutions**:

1. **Verify threshold calculation**:
```python
# 75% of 200,000 = 150,000
# If current_tokens >= 150,000, should trigger

current_tokens = 150000
budget = 200000
usage_percent = (current_tokens / budget) * 100

print(f"Usage: {usage_percent}%")
if usage_percent >= 75:
    print("Should trigger compression")
```

2. **Check compression threshold configuration**:
```python
monitor = AgentMemoryMonitor(
    session_id="session-123",
    token_budget=200000,
    compression_threshold=0.75  # 75%
)
```

3. **Manually trigger compression**:
```python
# If automatic compression not working, compress manually
monitor.compress(summary="Manual compression")
```

### Issue 6: Context Not Loading

**Symptoms**:
- Previous context not available at session start
- load_session_context() returns empty
- No previous work history

**Diagnosis**:
```python
# Check loaded context
context = monitor.load_session_context()
print(f"Session ID: {context.get('session_id')}")
print(f"Previous work: {len(context.get('previous_work', []))}")
print(f"Recent context: {len(context.get('recent_context', []))}")
```

**Root Causes**:
1. Session ID incorrect
2. No previous work for this session
3. Database not accessible
4. Context not saved in previous session

**Solutions**:

1. **Verify session ID**:
```python
# Use correct session ID
monitor = AgentMemoryMonitor(session_id="correct-session-id")
context = monitor.load_session_context()
```

2. **Check if previous work exists**:
```python
# Query ledger for previous work
from divineos.core.ledger import Ledger

ledger = Ledger()
events = ledger.query_events_for_session("session-123")
print(f"Events found: {len(events)}")

if len(events) == 0:
    print("No previous work for this session")
```

3. **Verify database access**:
```python
from pathlib import Path

db_path = Path.home() / ".divineos" / "divineos.db"
if not db_path.exists():
    print(f"Database not found: {db_path}")
    # Create database and run previous session
```

## Contradiction Resolution Issues

### Issue 7: Contradictions Not Detected

**Symptoms**:
- Contradicting facts stored without detection
- No SUPERSESSION events created
- Query returns wrong fact

**Diagnosis**:
```python
from divineos.supersession.contradiction_detector import ContradictionDetector

detector = ContradictionDetector()

# Check if contradiction detected
fact1 = {"type": "math", "key": "17x23", "value": "391"}
fact2 = {"type": "math", "key": "17x23", "value": "392"}

contradiction = detector.detect_contradiction(fact1, fact2)
print(f"Contradiction detected: {contradiction is not None}")
```

**Root Causes**:
1. Detector not initialized
2. Facts don't have same type and key
3. Detector disabled
4. Database not accessible

**Solutions**:

1. **Verify detector initialization**:
```python
from divineos.supersession.contradiction_detector import ContradictionDetector

detector = ContradictionDetector()
assert detector is not None
```

2. **Check fact structure**:
```python
# Facts must have same type and key to contradict
fact1 = {
    "type": "math_result",      # Same type
    "key": "17_times_23",       # Same key
    "value": "391",             # Different value
    "timestamp": datetime.now(datetime.UTC),
    "source": "DEMONSTRATED",
    "confidence": 1.0
}

fact2 = {
    "type": "math_result",      # Same type
    "key": "17_times_23",       # Same key
    "value": "392",             # Different value
    "timestamp": datetime.now(datetime.UTC),
    "source": "DEMONSTRATED",
    "confidence": 1.0
}

contradiction = detector.detect_contradiction(fact1, fact2)
assert contradiction is not None
```

3. **Verify facts are stored**:
```python
from divineos.core.ledger import Ledger

ledger = Ledger()
ledger.store_fact(fact1)
ledger.store_fact(fact2)

# Query facts
facts = ledger.query_facts_by_key("17_times_23")
print(f"Facts found: {len(facts)}")
```

### Issue 8: Contradictions Not Resolved

**Symptoms**:
- Contradictions detected but not resolved
- No SUPERSESSION events created
- Query returns old fact instead of new

**Diagnosis**:
```python
from divineos.supersession.resolution_engine import ResolutionEngine

engine = ResolutionEngine()

# Check if contradiction resolved
contradiction = {
    "fact1_id": "fact1",
    "fact2_id": "fact2",
    "fact_type": "math_result",
    "fact_key": "17_times_23"
}

resolution = engine.resolve_contradiction(contradiction)
print(f"Resolution: {resolution}")
```

**Root Causes**:
1. Engine not initialized
2. Resolution strategy not configured
3. Engine disabled
4. Database not accessible

**Solutions**:

1. **Verify engine initialization**:
```python
from divineos.supersession.resolution_engine import ResolutionEngine

engine = ResolutionEngine()
assert engine is not None
```

2. **Check resolution strategy**:
```python
# Default strategy: newest_timestamp_wins
# Verify strategy is applied

resolution = engine.resolve_contradiction(contradiction)
print(f"Strategy: {resolution['strategy']}")
assert resolution['strategy'] == "newest_timestamp_wins"
```

3. **Verify SUPERSESSION event created**:
```python
from divineos.core.ledger import Ledger

ledger = Ledger()
events = ledger.query_events_by_type("SUPERSESSION")
print(f"SUPERSESSION events: {len(events)}")
```

### Issue 9: Query Returns Wrong Fact

**Symptoms**:
- Query returns superseded fact instead of current
- Supersession chain not followed
- Old fact still returned after resolution

**Diagnosis**:
```python
from divineos.supersession.query_interface import QueryInterface

query = QueryInterface()

# Check what query returns
current_fact = query.get_current_fact("17_times_23")
print(f"Current fact value: {current_fact.value}")

# Check supersession chain
chain = query.get_supersession_chain("17_times_23")
print(f"Supersession chain: {chain}")
```

**Root Causes**:
1. Query interface not following supersession chain
2. Supersession events not stored
3. Query cache not updated
4. Database not accessible

**Solutions**:

1. **Verify supersession chain**:
```python
chain = query.get_supersession_chain("17_times_23")
print(f"Chain length: {len(chain)}")
print(f"Chain: {[f.value for f in chain]}")

# Should show: [391 → 392]
```

2. **Check supersession events**:
```python
from divineos.core.ledger import Ledger

ledger = Ledger()
events = ledger.query_events_by_type("SUPERSESSION")

for event in events:
    print(f"Superseded: {event.payload['superseded_fact_id']}")
    print(f"Superseding: {event.payload['superseding_fact_id']}")
```

3. **Refresh query cache**:
```python
# Reinitialize query interface to refresh cache
from divineos.supersession.query_interface import QueryInterface

query = QueryInterface()
current_fact = query.get_current_fact("17_times_23")
print(f"Current fact: {current_fact.value}")
```

## Learning Loop Issues

### Issue 10: Patterns Not Recommended

**Symptoms**:
- Pattern recommender returns no recommendations
- Humility audit shows no patterns
- Learning cycle not running

**Diagnosis**:
```python
from divineos.agent_integration.pattern_recommender import PatternRecommender

recommender = PatternRecommender()

# Check humility audit
audit = recommender.load_humility_audit()
print(f"Low confidence patterns: {len(audit['low_confidence_patterns'])}")
print(f"Untested patterns: {len(audit['untested_patterns'])}")

# Get recommendation
context = {"phase": "bugfix"}
recommendation = recommender.generate_recommendation(context)
print(f"Recommendation: {recommendation}")
```

**Root Causes**:
1. No patterns in pattern store
2. All patterns below confidence threshold
3. Preconditions don't match context
4. Learning cycle not run

**Solutions**:

1. **Verify patterns exist**:
```python
from divineos.agent_integration.pattern_store import PatternStore

store = PatternStore()
patterns = store.get_all_patterns()
print(f"Patterns: {len(patterns)}")

if len(patterns) == 0:
    print("No patterns - run learning cycle first")
```

2. **Check pattern confidence**:
```python
# Patterns below 0.65 confidence not recommended
for pattern in patterns:
    print(f"{pattern.name}: {pattern.confidence}")
    if pattern.confidence < 0.65:
        print(f"  Below threshold - not recommended")
```

3. **Verify preconditions match**:
```python
# Check if preconditions match context
context = {"phase": "bugfix"}
for pattern in patterns:
    match = all(
        context.get(k) == v
        for k, v in pattern.preconditions.items()
    )
    print(f"{pattern.name}: preconditions match = {match}")
```

4. **Run learning cycle**:
```python
from divineos.agent_integration.learning_cycle import LearningCycle

cycle = LearningCycle()
cycle.run()  # Run learning cycle to generate patterns
```

### Issue 11: Confidence Not Updating

**Symptoms**:
- Pattern confidence stays same after work
- Successes not increasing confidence
- Failures not decreasing confidence

**Diagnosis**:
```python
# Check pattern confidence before and after work
pattern_before = store.get_pattern("pattern-id")
print(f"Confidence before: {pattern_before.confidence}")

# Do work and record outcome
monitor.record_work_outcome(
    task="Task",
    pattern_id="pattern-id",
    success=True,
    violations_introduced=0,
    token_efficiency=0.95,
    rework_needed=False
)

# Check confidence after
pattern_after = store.get_pattern("pattern-id")
print(f"Confidence after: {pattern_after.confidence}")
```

**Root Causes**:
1. Work outcome not recorded
2. Learning cycle not run
3. Pattern not found
4. Confidence update disabled

**Solutions**:

1. **Record work outcome**:
```python
monitor.record_work_outcome(
    task="Task name",
    pattern_id="pattern-id",
    success=True,
    violations_introduced=0,
    token_efficiency=0.95,
    rework_needed=False
)
```

2. **Run learning cycle**:
```python
from divineos.agent_integration.learning_cycle import LearningCycle

cycle = LearningCycle()
cycle.run()  # Updates pattern confidence
```

3. **Verify pattern exists**:
```python
pattern = store.get_pattern("pattern-id")
if pattern is None:
    print("Pattern not found")
else:
    print(f"Pattern: {pattern.name}")
    print(f"Confidence: {pattern.confidence}")
```

## Database Issues

### Issue 12: Database Not Accessible

**Symptoms**:
- "Database not found" errors
- "Permission denied" errors
- All operations fail

**Diagnosis**:
```python
from pathlib import Path

db_path = Path.home() / ".divineos" / "divineos.db"
print(f"Database path: {db_path}")
print(f"Exists: {db_path.exists()}")
print(f"Readable: {db_path.is_file() and db_path.stat().st_mode & 0o400}")
print(f"Writable: {db_path.is_file() and db_path.stat().st_mode & 0o200}")
```

**Root Causes**:
1. Database file not created
2. Directory doesn't exist
3. Permission denied
4. Disk full

**Solutions**:

1. **Create database directory**:
```python
from pathlib import Path

db_dir = Path.home() / ".divineos"
db_dir.mkdir(parents=True, exist_ok=True)
print(f"Created: {db_dir}")
```

2. **Check permissions**:
```python
import os
from pathlib import Path

db_path = Path.home() / ".divineos" / "divineos.db"
if db_path.exists():
    # Check read/write permissions
    readable = os.access(db_path, os.R_OK)
    writable = os.access(db_path, os.W_OK)
    print(f"Readable: {readable}, Writable: {writable}")
```

3. **Check disk space**:
```python
import shutil

db_dir = Path.home() / ".divineos"
usage = shutil.disk_usage(db_dir)
print(f"Free space: {usage.free / (1024**3):.2f} GB")
```

## Performance Issues

### Issue 13: Slow Tool Call Processing

**Symptoms**:
- Tool calls take > 100ms
- Clarity check is slow
- System feels sluggish

**Diagnosis**:
```python
import time

start = time.time()
enforcer.enforce(
    tool_name="readFile",
    tool_input={"path": "file.txt"},
    context="I need to read the file",
    session_id="session-123"
)
elapsed = time.time() - start
print(f"Clarity check took: {elapsed*1000:.2f}ms")
```

**Root Causes**:
1. Semantic analyzer slow
2. Database queries slow
3. Too many patterns to check
4. System under load

**Solutions**:

1. **Disable semantic analysis if not needed**:
```python
config = ClarityConfig(
    semantic_analysis_enabled=False  # Faster but less accurate
)
enforcer = ClarityEnforcer(config=config)
```

2. **Optimize database queries**:
```python
# Ensure database indexes exist
from divineos.core.ledger import Ledger

ledger = Ledger()
ledger.create_indexes()  # Create performance indexes
```

3. **Reduce pattern store size**:
```python
# Archive old patterns
store = PatternStore()
store.archive_patterns(confidence_threshold=0.3)
```

## Debugging Tips

### Enable Logging

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Get logger for specific component
logger = logging.getLogger("divineos.clarity_enforcement")
logger.setLevel(logging.DEBUG)
```

### Inspect Component State

```python
# Check enforcer state
print(f"Enforcer config: {enforcer.config.__dict__}")

# Check monitor state
print(f"Monitor session: {monitor.session_id}")
print(f"Monitor budget: {monitor.token_budget}")

# Check detector state
print(f"Detector strategy: {detector.resolution_strategy}")
```

### Query Database Directly

```python
from divineos.core.ledger import Ledger

ledger = Ledger()

# Query all events
events = ledger.query_all_events()
print(f"Total events: {len(events)}")

# Query specific session
session_events = ledger.query_events_for_session("session-123")
print(f"Session events: {len(session_events)}")

# Query by type
violations = ledger.query_events_by_type("VIOLATION")
print(f"Violations: {len(violations)}")
```

## Getting Help

If you can't resolve an issue:

1. **Check logs**: Look in `logs/` directory for error messages
2. **Review documentation**: See [System Architecture](SYSTEM_ARCHITECTURE_AND_DATAFLOW.md)
3. **Run tests**: Execute test suite to verify system health
4. **Check configuration**: Verify all configs are correct
5. **Inspect database**: Query ledger directly to understand state

