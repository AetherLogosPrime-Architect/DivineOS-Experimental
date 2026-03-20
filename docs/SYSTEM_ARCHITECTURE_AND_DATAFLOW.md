# DivineOS System Architecture and Data Flow

## Overview

DivineOS is a comprehensive system for managing agent work with clarity enforcement, learning capabilities, and memory management. This document describes the complete system architecture, all layers, and how data flows through the system.

## System Layers

### Layer 1: Agent Interface Layer

**Purpose**: Where agents call tools and make decisions

**Components**:
- Agent execution engine
- Tool invocation interface
- Decision-making logic

**Responsibilities**:
- Execute agent instructions
- Call tools with parameters
- Receive tool results
- Make decisions based on outcomes

**Example Flow**:
```
Agent: "I need to read the file"
  ↓
Tool Call: readFile("path/to/file.txt")
  ↓
Tool Result: "file contents..."
  ↓
Agent: "Now I'll analyze this..."
```

### Layer 2: Clarity Enforcement Layer

**Purpose**: Checks if tool calls are explained in context

**Components**:
- Clarity enforcer
- Violation detector
- Semantic analyzer
- Confidence scorer

**Responsibilities**:
- Check if tool calls are explained
- Detect violations
- Analyze semantic relationships
- Score confidence levels

**Enforcement Modes**:
- **BLOCKING**: Raise exception, prevent execution
- **LOGGING**: Log violation, allow execution
- **PERMISSIVE**: Allow execution, no logging

**Example Flow**:
```
Tool Call: readFile("path/to/file.txt")
Context: "I need to read the file"
  ↓
Clarity Check: Is "readFile" explained in context?
  ↓
Semantic Analysis: "read the file" matches "readFile"
  ↓
Result: NO_VIOLATION (confidence: 0.95)
  ↓
Tool Execution: Allowed
```

### Layer 3: Learning & Memory Management Layer

**Purpose**: Tracks patterns, manages context, monitors tokens

**Components**:
- Memory monitor
- Learning cycle
- Pattern store
- Decision store
- Learning audit store
- Pattern recommender

**Responsibilities**:
- Track token usage
- Trigger compression at thresholds
- Capture work patterns
- Generate recommendations
- Manage context lifecycle

**Example Flow**:
```
Tool Execution Completes
  ↓
Token Usage: 120,000 / 200,000 (60%)
  ↓
Memory Monitor: Check status
  ↓
Status: OK (below 75% threshold)
  ↓
Learning Capture: Record pattern
  ↓
Pattern Store: Update confidence
```

### Layer 4: Contradiction Detection & Resolution Layer

**Purpose**: Detects conflicts, establishes "current truth"

**Components**:
- Contradiction detector
- Resolution engine
- Query interface
- Supersession tracker

**Responsibilities**:
- Detect contradictions
- Apply resolution strategy
- Track supersession chains
- Return current facts

**Example Flow**:
```
New Fact: "17 × 23 = 392"
Existing Fact: "17 × 23 = 391"
  ↓
Contradiction Detector: Detect contradiction
  ↓
Resolution Engine: Apply "newest wins" strategy
  ↓
Result: 392 supersedes 391
  ↓
Query Interface: Return 392 as current truth
```

### Layer 5: Ledger & Event Storage Layer

**Purpose**: Immutable audit trail, fact storage, verification

**Components**:
- Event ledger
- Fact store
- Event verifier
- SHA256 verification

**Responsibilities**:
- Store all events immutably
- Verify event integrity
- Query events by session/type
- Maintain audit trail

**Example Flow**:
```
Event: Tool call completed
  ↓
Ledger: Store event with SHA256 hash
  ↓
Verification: Verify hash integrity
  ↓
Query: Retrieve events for session
```

## Complete System Data Flow

### Tool Call Processing Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. AGENT INTERFACE LAYER                                    │
│    Agent decides to call tool                               │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. CLARITY ENFORCEMENT LAYER                                │
│    Check if tool call is explained in context               │
│    - Explicit mention check                                 │
│    - Semantic analysis                                      │
│    - Confidence scoring                                     │
└────────────────────┬────────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
    VIOLATION              NO VIOLATION
         │                       │
         ↓                       ↓
    ┌─────────────┐      ┌──────────────┐
    │ Enforcement │      │ Continue     │
    │ Mode Check  │      │ Execution    │
    └─────────────┘      └──────────────┘
         │                       │
    ┌────┴────┬────┬────┐       │
    │          │    │    │       │
 BLOCKING  LOGGING PERM  │       │
    │          │    │    │       │
    ↓          ↓    ↓    ↓       ↓
  RAISE      LOG  ALLOW  ALLOW  ALLOW
  ERROR      &    &      &      &
  STOP       ALLOW ALLOW ALLOW ALLOW
             │    │    │       │
             └────┴────┴───────┘
                   │
                   ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. TOOL EXECUTION                                           │
│    Execute the tool call                                    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. LEARNING & MEMORY MANAGEMENT LAYER                       │
│    - Update token usage                                     │
│    - Check compression threshold (75%)                      │
│    - Capture work pattern                                   │
│    - Update pattern confidence                              │
└────────────────────┬────────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
    COMPRESSION            NO COMPRESSION
    NEEDED                 NEEDED
         │                       │
         ↓                       ↓
    ┌─────────────┐      ┌──────────────┐
    │ Summarize   │      │ Continue     │
    │ Context     │      │ Session      │
    └─────────────┘      └──────────────┘
         │                       │
         ↓                       │
    ┌─────────────┐              │
    │ Compress to │              │
    │ Ledger      │              │
    └─────────────┘              │
         │                       │
         └───────────┬───────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. LEDGER & EVENT STORAGE LAYER                             │
│    - Store tool call event                                  │
│    - Store result event                                     │
│    - Store violation event (if any)                         │
│    - Verify SHA256 integrity                                │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. CONTRADICTION DETECTION & RESOLUTION LAYER               │
│    - Check if result contradicts existing facts             │
│    - Resolve contradictions                                 │
│    - Create SUPERSESSION events                             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ 7. RETURN TO AGENT                                          │
│    Tool result ready for agent to use                       │
└─────────────────────────────────────────────────────────────┘
```

### Session Lifecycle Flow

```
┌─────────────────────────────────────────────────────────────┐
│ SESSION START                                               │
│ - Create session ID                                         │
│ - Load previous context from ledger                         │
│ - Initialize memory monitor                                 │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ WORK EXECUTION LOOP                                         │
│ - Agent makes decisions                                     │
│ - Calls tools                                               │
│ - Clarity enforcement checks each call                      │
│ - Learning captures patterns                                │
│ - Memory monitor tracks tokens                              │
│ - Contradictions detected and resolved                      │
│ - All events stored in ledger                               │
└────────────────────┬────────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
    MORE WORK              SESSION END
         │                       │
         ↓                       ↓
    ┌─────────────┐      ┌──────────────┐
    │ Continue    │      │ Save final   │
    │ Loop        │      │ checkpoint   │
    └─────────────┘      └──────────────┘
         │                       │
         └───────────┬───────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ LEARNING CYCLE EXECUTION                                    │
│ - Load work history from ledger                             │
│ - Extract patterns from work outcomes                       │
│ - Update pattern confidence scores                          │
│ - Detect pattern invalidation                               │
│ - Generate humility audit                                   │
│ - Store results to ledger                                   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ SESSION COMPLETE                                            │
│ - All work saved to ledger                                  │
│ - Patterns updated                                          │
│ - Ready for next session                                    │
└─────────────────────────────────────────────────────────────┘
```

### Contradiction Resolution Flow

```
┌─────────────────────────────────────────────────────────────┐
│ NEW FACT STORED                                             │
│ Type: "math_result"                                         │
│ Key: "17_times_23"                                          │
│ Value: "392"                                                │
│ Timestamp: 2026-03-19T21:00:00                              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ CONTRADICTION DETECTOR                                      │
│ Query: Find facts with same type and key                    │
│ Result: Found existing fact with value "391"                │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ CONTRADICTION IDENTIFIED                                    │
│ - Fact 1: 17×23 = 391 (timestamp: 2026-03-19T20:00:00)     │
│ - Fact 2: 17×23 = 392 (timestamp: 2026-03-19T21:00:00)     │
│ - Severity: CRITICAL (math result contradiction)            │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ RESOLUTION ENGINE                                           │
│ Strategy: "newest_timestamp_wins"                           │
│ Winner: Fact 2 (392) - newer timestamp                      │
│ Loser: Fact 1 (391) - older timestamp                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ MARK FACT AS SUPERSEDED                                     │
│ Fact 1: superseded_by = Fact 2 ID                           │
│ Fact 2: supersedes = Fact 1 ID                              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ CREATE SUPERSESSION EVENT                                   │
│ Type: "SUPERSESSION"                                        │
│ Superseded Fact ID: Fact 1 ID                               │
│ Superseding Fact ID: Fact 2 ID                              │
│ Reason: "newer_timestamp"                                   │
│ Timestamp: 2026-03-19T21:00:01                              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ STORE TO LEDGER                                             │
│ - Store SUPERSESSION event                                  │
│ - Verify SHA256 integrity                                   │
│ - Update query index                                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ QUERY INTERFACE UPDATED                                     │
│ Query: get_current_fact("17_times_23")                      │
│ Result: Returns Fact 2 (392), not Fact 1 (391)              │
│ Supersession Chain: [Fact 1 → Fact 2]                       │
└─────────────────────────────────────────────────────────────┘
```

## Component Interactions

### Clarity Enforcement + Learning Loop

```
Tool Call Without Explanation
  ↓
Clarity Enforcer: VIOLATION
  ↓
Learning Loop: Capture violation pattern
  ↓
Pattern Store: Record violation
  ↓
Next Session: Pattern recommender suggests explanation
```

### Memory Monitor + Learning Cycle

```
Session End
  ↓
Memory Monitor: Save checkpoint
  ↓
Learning Cycle: Load work history
  ↓
Extract Patterns: Analyze outcomes
  ↓
Update Confidence: Increase/decrease based on success
  ↓
Generate Humility Audit: Identify low-confidence patterns
```

### Contradiction Resolution + Ledger

```
New Fact Stored
  ↓
Contradiction Detector: Check for conflicts
  ↓
Resolution Engine: Apply strategy
  ↓
Create SUPERSESSION Event
  ↓
Ledger: Store event with verification
  ↓
Query Interface: Return current truth
```

## Data Models

### Event Model
```python
@dataclass
class Event:
    id: str                    # Unique event ID
    type: str                  # Event type (TOOL_CALL, VIOLATION, SUPERSESSION, etc.)
    session_id: str            # Session this event belongs to
    timestamp: datetime        # When event occurred
    payload: dict              # Event-specific data
    hash: str                  # SHA256 hash for verification
    previous_hash: str         # Hash of previous event (chain)
```

### Fact Model
```python
@dataclass
class Fact:
    id: str                    # Unique fact ID
    fact_type: str             # Type of fact (e.g., "math_result")
    fact_key: str              # Key for this fact (e.g., "17_times_23")
    value: Any                 # The fact value (e.g., "392")
    timestamp: datetime        # When fact was established
    source: str                # Source (DEMONSTRATED, INFERRED, LEARNED)
    confidence: float          # Confidence level (0.0 to 1.0)
    superseded_by: Optional[str] = None  # ID of superseding fact
```

### Pattern Model
```python
@dataclass
class Pattern:
    pattern_id: str            # Unique pattern ID
    pattern_type: str          # "structural" or "tactical"
    name: str                  # Pattern name
    description: str           # Pattern description
    preconditions: dict        # Conditions when pattern applies
    confidence: float          # Confidence level (0.0 to 1.0)
    occurrences: int           # Times observed
    successes: int             # Times succeeded
    success_rate: float        # Success rate (0.0 to 1.0)
```

## Integration Points

### 1. Agent → Clarity Enforcement
- Agent calls tool
- Clarity enforcer checks if explained
- Returns violation or allows execution

### 2. Clarity Enforcement → Learning Loop
- Violation detected
- Learning loop captures pattern
- Pattern store updated

### 3. Tool Execution → Memory Monitor
- Tool completes
- Memory monitor updates token usage
- Checks compression threshold

### 4. Memory Monitor → Learning Cycle
- Session ends
- Learning cycle triggered
- Patterns updated based on outcomes

### 5. New Fact → Contradiction Detector
- Fact stored in ledger
- Contradiction detector checks for conflicts
- Resolution engine applies strategy

### 6. Resolution → Query Interface
- Supersession event created
- Query interface updated
- Current truth established

## Performance Characteristics

### Latency Targets
- Tool call processing: < 100ms
- Clarity check: < 50ms
- Contradiction detection: < 100ms
- Pattern recommendation: < 200ms

### Throughput Targets
- Ledger writes: > 1000 events/sec
- Learning analysis: < 500ms for 100 events
- Memory compression: > 50% reduction

### Storage
- Ledger: Immutable, append-only
- Facts: Indexed by type and key
- Patterns: Indexed by preconditions
- Events: Queryable by session and type

## Error Handling

### Clarity Enforcement Errors
- Violation detected → Log and enforce based on mode
- Enforcement failure → Log error, allow execution

### Contradiction Resolution Errors
- Unresolvable contradiction → Log error, flag for review
- Resolution failure → Rollback, raise exception

### Memory Monitor Errors
- Token budget exceeded → Raise error, suggest compression
- Compression failure → Log error, continue with reduced context

### Learning Cycle Errors
- Pattern extraction failure → Log error, continue with available patterns
- Confidence update failure → Log error, use previous confidence

## Correctness Invariants

### I1: Event Immutability
Once stored in ledger, events cannot be modified or deleted.

### I2: Fact Uniqueness
Only one fact can be "current" for a given type and key.

### I3: Supersession Transitivity
If A supersedes B and B supersedes C, then A supersedes C.

### I4: Pattern Consistency
Same preconditions always return same recommendation (unless confidence changes).

### I5: Token Budget Enforcement
Token usage never exceeds budget without compression.

### I6: Violation Capture
All clarity violations are captured and stored in ledger.

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Agent Interface                          │
│              (Kiro IDE or External Agent)                   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│                  DivineOS System                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Clarity Enforcement Layer                            │  │
│  │ - Enforcer, Detector, Analyzer, Scorer               │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Learning & Memory Management Layer                   │  │
│  │ - Monitor, Cycle, Stores, Recommender                │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Contradiction Detection & Resolution Layer           │  │
│  │ - Detector, Engine, Query Interface                  │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Ledger & Event Storage Layer                         │  │
│  │ - Ledger, Verifier, Query Interface                  │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│                  Persistent Storage                         │
│  - SQLite database (~/.divineos/divineos.db)                │
│  - Event ledger (immutable)                                 │
│  - Fact store (indexed)                                     │
│  - Pattern store (indexed)                                  │
└─────────────────────────────────────────────────────────────┘
```

## Summary

DivineOS is a layered system where:

1. **Clarity Enforcement** ensures tool calls are explained
2. **Learning & Memory** captures patterns and manages context
3. **Contradiction Resolution** establishes "current truth"
4. **Ledger Storage** maintains immutable audit trail

Each layer builds on the previous, creating a comprehensive system for managing agent work with transparency, learning, and correctness.

