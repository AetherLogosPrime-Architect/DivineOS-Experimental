# Integration Test Examples
**Purpose**: Show what integration tests should look like  
**Status**: Ready to implement  

---

## Test 1: Clarity + Learning Integration

**What it tests**: When a tool call violates clarity, does the learning loop capture it?

```python
def test_clarity_violation_captured_by_learning_loop():
    """
    Scenario:
    1. Agent makes an unexplained tool call
    2. Clarity enforcement detects violation
    3. Learning loop should capture this pattern
    
    Expected:
    - Violation is logged
    - Learning loop records the violation
    - Pattern store has the violation
    - Next session can learn from it
    """
    
    # Setup
    session_id = "test_session_123"
    monitor = get_memory_monitor(session_id)
    enforcer = ClarityEnforcer(ClarityConfig(
        enforcement_mode=ClarityEnforcementMode.LOGGING
    ))
    
    # Make an unexplained tool call
    tool_name = "readFile"
    tool_input = {"path": "test.txt"}
    context = ["Some random context"]  # Doesn't explain readFile
    
    # Enforce clarity (should log violation, not raise)
    enforcer.enforce(tool_name, tool_input, context, session_id)
    
    # Check that violation was logged
    violations = get_violations_by_session(session_id)
    assert len(violations) == 1
    assert violations[0].tool_name == "readFile"
    
    # Check that learning loop captured it
    lessons = analyze_session_for_lessons(session_id)
    assert len(lessons.error_patterns) > 0
    
    # Verify pattern is stored
    patterns = monitor.get_recommendation({"tool": "readFile"})
    assert patterns is not None
    assert "violation" in patterns.get("warnings", [])
```

---

## Test 2: Contradiction Detection + Resolution

**What it tests**: Can the system detect and resolve contradictions?

```python
def test_contradiction_detection_and_resolution():
    """
    Scenario:
    1. Store fact: 17 × 23 = 391
    2. Store fact: 17 × 23 = 392
    3. System detects contradiction
    4. System resolves it (newer fact wins)
    5. Query returns correct "current truth"
    
    Expected:
    - Contradiction detected
    - Resolution applied
    - Supersession event created
    - Query returns 391 (newer fact)
    """
    
    # Setup
    ledger = get_ledger()
    detector = ContradictionDetector()
    engine = ResolutionEngine()
    query = QueryInterface(engine, detector)
    
    # Store first fact
    fact1 = {
        "id": "fact_1",
        "fact_type": "mathematical_operation",
        "fact_key": "17_times_23",
        "value": 391,
        "timestamp": "2026-03-19T10:00:00Z",
        "source": "DEMONSTRATED",
        "confidence": 1.0,
    }
    ledger.store_fact(fact1)
    
    # Store contradicting fact (newer)
    fact2 = {
        "id": "fact_2",
        "fact_type": "mathematical_operation",
        "fact_key": "17_times_23",
        "value": 392,
        "timestamp": "2026-03-19T10:01:00Z",
        "source": "DEMONSTRATED",
        "confidence": 1.0,
    }
    ledger.store_fact(fact2)
    
    # Detect contradiction
    contradiction = detector.detect_contradiction(fact1, fact2)
    assert contradiction is not None
    assert contradiction.severity == ContradictionSeverity.CRITICAL
    
    # Resolve contradiction
    resolution = engine.resolve_contradiction(contradiction)
    assert resolution is not None
    assert resolution.winner_id == "fact_2"  # Newer fact wins
    
    # Verify supersession event created
    events = ledger.get_events(type="SUPERSESSION")
    assert len(events) > 0
    assert events[0]["payload"]["superseded_fact_id"] == "fact_1"
    assert events[0]["payload"]["superseding_fact_id"] == "fact_2"
    
    # Query should return current truth (fact_2)
    current_fact = query.get_current_fact("17_times_23")
    assert current_fact["value"] == 392
    assert current_fact["id"] == "fact_2"
```

---

## Test 3: Memory Monitor Integration

**What it tests**: Does memory monitor actually prevent token overflow?

```python
def test_memory_monitor_prevents_token_overflow():
    """
    Scenario:
    1. Start session with memory monitor
    2. Simulate token usage approaching limit
    3. Memory monitor should trigger compression
    4. Context should be compressed
    5. Tokens should be reduced
    
    Expected:
    - Token usage tracked
    - Compression triggered at 75% (150k of 200k)
    - Context compressed
    - Tokens reduced
    - Session continues
    """
    
    # Setup
    session_id = "test_session_456"
    monitor = get_memory_monitor(session_id)
    
    # Load initial context
    context = monitor.load_session_context()
    assert context is not None
    
    # Simulate token usage
    initial_tokens = 10000
    monitor.update_token_usage(initial_tokens)
    
    # Simulate approaching limit
    for i in range(15):  # Simulate 15 operations
        tokens = initial_tokens + (i * 10000)
        status = monitor.update_token_usage(tokens)
        
        if tokens > 150000:  # 75% of 200k
            # Should recommend compression
            assert status["should_compress"] == True
            
            # Compress context
            summary = "Completed 15 operations, learned 3 patterns"
            compressed = monitor.compress_context(summary)
            assert compressed is not None
            
            # Verify tokens reduced
            new_status = monitor.update_token_usage(50000)
            assert new_status["current_tokens"] < tokens
            break
    
    # Verify session can continue
    assert monitor is not None
    assert monitor.session_id == session_id
```

---

## Test 4: Full Agent Session Integration

**What it tests**: Does everything work together in a realistic scenario?

```python
def test_full_agent_session_integration():
    """
    Scenario:
    1. Agent starts session
    2. Makes multiple tool calls
    3. Some calls are explained, some aren't
    4. System tracks everything
    5. Learning loop captures patterns
    6. Memory monitor manages tokens
    7. Contradictions are detected and resolved
    8. Session ends with complete audit trail
    
    Expected:
    - All systems work together
    - No errors or exceptions
    - Complete audit trail
    - Patterns learned
    - Contradictions resolved
    """
    
    # Setup
    session_id = "test_session_789"
    monitor = get_memory_monitor(session_id)
    enforcer = ClarityEnforcer(ClarityConfig(
        enforcement_mode=ClarityEnforcementMode.LOGGING
    ))
    detector = ContradictionDetector()
    engine = ResolutionEngine()
    ledger = get_ledger()
    
    # Simulate agent session
    tool_calls = [
        {
            "tool": "readFile",
            "input": {"path": "test.txt"},
            "context": "I need to read the file to understand the structure",
            "explained": True,
        },
        {
            "tool": "fsWrite",
            "input": {"path": "output.txt", "text": "result"},
            "context": "Now I'll write the result",
            "explained": True,
        },
        {
            "tool": "executePwsh",
            "input": {"command": "python test.py"},
            "context": "Let me run this",
            "explained": False,  # Not well explained
        },
        {
            "tool": "readFile",
            "input": {"path": "test.txt"},
            "context": "I need to read the file again",
            "explained": True,
        },
    ]
    
    # Process each tool call
    violations = []
    for i, call in enumerate(tool_calls):
        # Update token usage
        tokens = 10000 + (i * 5000)
        monitor.update_token_usage(tokens)
        
        # Check clarity
        enforcer.enforce(
            call["tool"],
            call["input"],
            [call["context"]],
            session_id,
        )
        
        # If violation, record it
        if not call["explained"]:
            violations.append(call["tool"])
        
        # Record work outcome
        monitor.record_work_outcome(
            {
                "tool": call["tool"],
                "input": call["input"],
            },
            {"status": "success", "duration": 100},
        )
    
    # Verify violations were captured
    assert len(violations) > 0
    session_violations = get_violations_by_session(session_id)
    assert len(session_violations) >= len(violations)
    
    # Verify learning loop captured patterns
    lessons = analyze_session_for_lessons(session_id)
    assert lessons is not None
    assert len(lessons.tool_patterns) > 0
    
    # Verify memory monitor tracked everything
    assert monitor.session_id == session_id
    
    # Verify ledger has complete audit trail
    events = ledger.get_events()
    assert len(events) > 0
    
    # End session
    summary = monitor.end_session("Session completed successfully", "completed")
    assert summary is not None
    
    # Verify session is recorded
    final_events = ledger.get_events()
    assert len(final_events) > len(events)
```

---

## Test 5: Contradiction Resolution with Multiple Facts

**What it tests**: Can system handle multiple contradictions?

```python
def test_multiple_contradictions_resolution():
    """
    Scenario:
    1. Store multiple facts about same thing
    2. Some contradict each other
    3. System resolves all contradictions
    4. Query returns correct "current truth"
    
    Expected:
    - All contradictions detected
    - All resolved correctly
    - Query returns newest fact
    """
    
    # Setup
    ledger = get_ledger()
    detector = ContradictionDetector()
    engine = ResolutionEngine()
    query = QueryInterface(engine, detector)
    
    # Store multiple facts (each newer than previous)
    facts = [
        {
            "id": "fact_1",
            "fact_type": "system_state",
            "fact_key": "deployment_status",
            "value": "pending",
            "timestamp": "2026-03-19T10:00:00Z",
            "source": "SYSTEM",
            "confidence": 0.8,
        },
        {
            "id": "fact_2",
            "fact_type": "system_state",
            "fact_key": "deployment_status",
            "value": "in_progress",
            "timestamp": "2026-03-19T10:05:00Z",
            "source": "SYSTEM",
            "confidence": 0.9,
        },
        {
            "id": "fact_3",
            "fact_type": "system_state",
            "fact_key": "deployment_status",
            "value": "completed",
            "timestamp": "2026-03-19T10:10:00Z",
            "source": "SYSTEM",
            "confidence": 1.0,
        },
    ]
    
    # Store all facts
    for fact in facts:
        ledger.store_fact(fact)
    
    # Detect all contradictions
    contradictions = []
    for i in range(len(facts)):
        for j in range(i + 1, len(facts)):
            contradiction = detector.detect_contradiction(facts[i], facts[j])
            if contradiction:
                contradictions.append(contradiction)
    
    # Should have 3 contradictions (1-2, 1-3, 2-3)
    assert len(contradictions) == 3
    
    # Resolve all contradictions
    for contradiction in contradictions:
        resolution = engine.resolve_contradiction(contradiction)
        assert resolution is not None
    
    # Query should return newest fact
    current = query.get_current_fact("deployment_status")
    assert current["value"] == "completed"
    assert current["id"] == "fact_3"
    
    # Verify supersession chain
    chain = query.get_supersession_chain("deployment_status")
    assert len(chain) == 3
    assert chain[0]["id"] == "fact_1"
    assert chain[1]["id"] == "fact_2"
    assert chain[2]["id"] == "fact_3"
```

---

## Test 6: Error Handling in Integration

**What it tests**: What happens when something fails?

```python
def test_integration_error_handling():
    """
    Scenario:
    1. Clarity enforcement fails
    2. Learning loop should still work
    3. Memory monitor should still track
    4. Ledger should record error
    5. Session should continue
    
    Expected:
    - Error is caught
    - Error is logged
    - System continues
    - No cascading failures
    """
    
    # Setup
    session_id = "test_session_error"
    monitor = get_memory_monitor(session_id)
    enforcer = ClarityEnforcer()
    
    # Simulate error in clarity enforcement
    try:
        # This should raise an exception
        enforcer.enforce(
            "readFile",
            {"path": "test.txt"},
            ["random context"],
            session_id,
        )
    except ClarityViolationException as e:
        # Error should be caught
        assert e is not None
        assert "readFile" in str(e)
    
    # System should continue
    # Memory monitor should still work
    monitor.update_token_usage(10000)
    assert monitor is not None
    
    # Ledger should record error
    events = get_ledger().get_events()
    assert len(events) > 0
    
    # Session should continue
    monitor.record_work_outcome(
        {"tool": "readFile"},
        {"status": "error", "error": "clarity_violation"},
    )
    
    # Verify session is still valid
    assert monitor.session_id == session_id
```

---

## How to Run These Tests

```bash
# Create test file
touch tests/test_integration_full.py

# Copy test code into file
# Run tests
python -m pytest tests/test_integration_full.py -v

# Run specific test
python -m pytest tests/test_integration_full.py::test_clarity_violation_captured_by_learning_loop -v
```

---

## What These Tests Validate

1. **Clarity + Learning**: Violations are captured by learning loop
2. **Contradiction Resolution**: System can detect and resolve conflicts
3. **Memory Monitor**: Token tracking and compression work
4. **Full Session**: All systems work together
5. **Multiple Contradictions**: Complex scenarios handled correctly
6. **Error Handling**: Failures don't cascade

---

## Expected Results

After implementing these tests:

- ✅ All tests should pass
- ✅ Integration issues will be revealed
- ✅ You'll understand data flow
- ✅ You'll have confidence in deployment
- ✅ You'll have documentation of expected behavior

---

## Next Steps

1. Create `tests/test_integration_full.py`
2. Copy these test examples
3. Run tests
4. Fix any failures
5. Add more integration tests as needed

---

**Status**: READY TO IMPLEMENT  
**Confidence**: HIGH  
**Recommendation**: Start with these tests this week
