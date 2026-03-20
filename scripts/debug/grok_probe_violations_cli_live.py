#!/usr/bin/env python
"""Live probe: Test violations CLI commands."""

from divineos.violations_cli.violations_command import ViolationsCommand
from divineos.clarity_enforcement.violation_detector import ClarityViolation, ViolationSeverity
from divineos.core.session_manager import get_or_create_session_id

# Get or create current session
session_id = get_or_create_session_id()

# Get CLI command instance
cmd = ViolationsCommand()

print("=" * 80)
print("LIVE VIOLATIONS CLI PROBE")
print("=" * 80)

# Create some test violations
print("\n1. Creating test violations...")
violations = [
    ClarityViolation(
        tool_name="code_execution",
        tool_input={"expr": "13 ** 5"},
        severity=ViolationSeverity.HIGH,
        context=["Unexplained tool call"],
        session_id=session_id,
    ),
    ClarityViolation(
        tool_name="deleteFile",
        tool_input={"path": "important.txt"},
        severity=ViolationSeverity.HIGH,
        context=["Destructive operation without explanation"],
        session_id=session_id,
    ),
    ClarityViolation(
        tool_name="readFile",
        tool_input={"path": "config.json"},
        severity=ViolationSeverity.LOW,
        context=["Reading configuration"],
        session_id=session_id,
    ),
]

print(f"   Created {len(violations)} test violations")
for i, v in enumerate(violations, 1):
    print(f"   {i}. {v.tool_name} ({v.severity.value})")

# Test query_recent_violations
print("\n2. Testing query_recent_violations(limit=5)...")
try:
    recent = cmd.query_recent_violations(limit=5)
    print(f"   Found {len(recent)} recent violations")
    for v in recent[:3]:
        print(f"   - {v.get('tool_name')} ({v.get('severity')})")
except Exception as e:
    print(f"   Error: {e}")

# Test query_violations_by_severity
print("\n3. Testing query_violations_by_severity(HIGH)...")
try:
    high_severity = cmd.query_violations_by_severity("HIGH")
    print(f"   Found {len(high_severity)} HIGH severity violations")
    for v in high_severity[:3]:
        print(f"   - {v.get('tool_name')}")
except Exception as e:
    print(f"   Error: {e}")

# Test query_violations_by_session
print("\n4. Testing query_violations_by_session(current_session)...")
try:
    session_violations = cmd.query_violations_by_session(session_id)
    print(f"   Found {len(session_violations)} violations in current session")
    for v in session_violations[:3]:
        print(f"   - {v.get('tool_name')} ({v.get('severity')})")
except Exception as e:
    print(f"   Error: {e}")

# Test query_contradictions
print("\n5. Testing query_contradictions()...")
try:
    contradictions = cmd.query_contradictions()
    print(f"   Found {len(contradictions)} contradictions")
    if contradictions:
        for c in contradictions[:3]:
            print(f"   - Fact 1: {c.get('fact1_id')}")
            print(f"     Fact 2: {c.get('fact2_id')}")
except Exception as e:
    print(f"   Error: {e}")

print("\n" + "=" * 80)
print("PROBE COMPLETE")
print("=" * 80)
print("\nCLI Commands Available:")
print("- query_recent_violations(limit=5)")
print("- query_violations_by_severity(severity)")
print("- query_violations_by_session(session_id)")
print("- query_contradictions()")
print("\nAll commands return formatted violation data for CLI display")
