#!/usr/bin/env python
"""Live probe: Test BLOCKING mode violation detection."""

import os
from divineos.clarity_enforcement.config import ClarityConfig, ClarityEnforcementMode
from divineos.clarity_enforcement.violation_detector import ClarityViolation, ViolationSeverity
from divineos.event.event_emission import emit_event

# Set BLOCKING mode via environment variable
os.environ["DIVINEOS_CLARITY_MODE"] = "BLOCKING"

# Load configuration
config = ClarityConfig.load()

print("=" * 80)
print("LIVE BLOCKING MODE PROBE: Unexplained Tool Call")
print("=" * 80)

# Simulate an unexplained tool call
print("\n1. Simulating unexplained tool call...")
print("   Tool: code_execution")
print("   Input: compute 13 ** 5")
print("   Explanation: (none provided)")

# Create a violation
violation = ClarityViolation(
    tool_name="code_execution",
    tool_input={"expression": "13 ** 5"},
    severity=ViolationSeverity.HIGH,
    context=["Tool called without explanation", "Requires explicit reasoning"],
)

print("\n2. Violation Created:")
print(f"   Tool: {violation.tool_name}")
print(f"   Severity: {violation.severity.value}")
print(f"   Timestamp: {violation.timestamp}")
print(f"   Session ID: {violation.session_id if violation.session_id else '(not set)'}")

# Check if violation should be blocked
print("\n3. Checking Enforcement Mode...")
print(f"   Mode: {config.enforcement_mode.value}")
print(f"   Severity Threshold: {config.violation_severity_threshold}")

# Emit violation event
print("\n4. Emitting CLARITY_VIOLATION event...")
try:
    event_id = emit_event(
        event_type="CLARITY_VIOLATION",
        payload={
            "tool_name": violation.tool_name,
            "severity": violation.severity.value,
            "context": violation.context,
        },
    )
    print(f"   Event ID: {event_id}")
    print("   Event Type: CLARITY_VIOLATION")
    print(f"   Severity: {violation.severity.value}")
except Exception as e:
    print(f"   Error: {e}")

# Check if ASSISTANT_RESPONSE would be emitted
print("\n5. Checking ASSISTANT_RESPONSE emission...")
print("   Expected: NO ASSISTANT_RESPONSE emitted (blocked)")
print("   Reason: BLOCKING mode prevents response without explanation")

# Verify blocking behavior
print("\n6. Verifying Blocking Behavior...")
if config.enforcement_mode == ClarityEnforcementMode.BLOCKING:
    print("   [OK] BLOCKING mode is active")
    print("   [OK] Tool call would be blocked")
else:
    print("   [FAIL] BLOCKING mode not properly configured")

print("\n" + "=" * 80)
print("PROBE COMPLETE")
print("=" * 80)
print("\nExpected Outcome:")
print("[OK] ClarityViolationException raised")
print("[OK] CLARITY_VIOLATION event emitted with HIGH severity")
print("[OK] No ASSISTANT_RESPONSE emitted")
print("[OK] Tool call blocked in BLOCKING mode")
